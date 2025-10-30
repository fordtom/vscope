import serial, asyncio, struct, re
from concurrent.futures import ThreadPoolExecutor
import serial.tools.list_ports as ls
from typing import Dict, Optional

# Serial configuration constants
DEFAULT_BAUD_RATE = 115200
DEFAULT_DATA_BITS = 8
DEFAULT_STOP_BITS = 1.0
DEFAULT_PARITY = "N"
VALID_DATA_BITS = (5, 6, 7, 8)
VALID_STOP_BITS = (1.0, 1.5, 2.0)
VALID_PARITY_CODES = ("N", "E", "O", "M", "S")

# Device communication constants
HANDSHAKE_COMMAND = b"h00000000"
HANDSHAKE_RESPONSE_SIZE = 14
LABEL_REQUEST_PREFIX = b"l0000"
LABEL_RESPONSE_SIZE = 41
DEFAULT_TIMEOUT = 0.02
SNAPSHOT_TIMEOUT = 10
MAX_RETRY_ATTEMPTS = 3
BYTES_PER_SAMPLE = 4


def _normalize_serial_settings(settings: dict) -> tuple:
    """Return a normalized tuple of serial settings for change detection.

    Tuple format: (baud, data_bits, stop_bits, parity_code)
    """
    try:
        baud = int(settings.get("serial_baud", DEFAULT_BAUD_RATE))
    except Exception:
        baud = DEFAULT_BAUD_RATE
    try:
        data_bits = int(settings.get("serial_data_bits", DEFAULT_DATA_BITS))
        if data_bits not in VALID_DATA_BITS:
            data_bits = DEFAULT_DATA_BITS
    except Exception:
        data_bits = DEFAULT_DATA_BITS
    try:
        stop_bits = float(settings.get("serial_stop_bits", DEFAULT_STOP_BITS))
        if stop_bits not in VALID_STOP_BITS:
            stop_bits = DEFAULT_STOP_BITS
    except Exception:
        stop_bits = DEFAULT_STOP_BITS
    try:
        parity_code = str(settings.get("serial_parity", DEFAULT_PARITY)).upper()
        if parity_code not in VALID_PARITY_CODES:
            parity_code = DEFAULT_PARITY
    except Exception:
        parity_code = DEFAULT_PARITY
    return (baud, data_bits, stop_bits, parity_code)


def _serial_params_from_normalized(norm: tuple) -> dict:
    """Map normalized tuple to pyserial Serial constructor kwargs."""
    baud, data_bits, stop_bits, parity_code = norm
    bytesize_map = {
        5: serial.FIVEBITS,
        6: serial.SIXBITS,
        7: serial.SEVENBITS,
        8: serial.EIGHTBITS,
    }
    stopbits_map = {
        1.0: serial.STOPBITS_ONE,
        1.5: serial.STOPBITS_ONE_POINT_FIVE,
        2.0: serial.STOPBITS_TWO,
    }
    parity_map = {
        "N": serial.PARITY_NONE,
        "E": serial.PARITY_EVEN,
        "O": serial.PARITY_ODD,
        "M": serial.PARITY_MARK,
        "S": serial.PARITY_SPACE,
    }
    return {
        "baudrate": baud,
        "bytesize": bytesize_map.get(data_bits, serial.EIGHTBITS),
        "stopbits": stopbits_map.get(stop_bits, serial.STOPBITS_ONE),
        "parity": parity_map.get(parity_code, serial.PARITY_NONE),
        "xonxoff": False,
        "rtscts": False,
    }


class Device:
    def __init__(self, path, serial_kwargs: dict | None = None) -> None:
        self.comport = path
        if serial_kwargs is None:
            serial_kwargs = _serial_params_from_normalized(
                (
                    DEFAULT_BAUD_RATE,
                    DEFAULT_DATA_BITS,
                    DEFAULT_STOP_BITS,
                    DEFAULT_PARITY,
                )
            )
        self.port = serial.Serial(path, **serial_kwargs)
        self.port.flush()

        self.configure()

    def configure(self):
        self.port.timeout = DEFAULT_TIMEOUT

        self.port.write(HANDSHAKE_COMMAND)
        temp = self.port.read(size=HANDSHAKE_RESPONSE_SIZE)

        self.channels, self.buffer_length, raw_name = struct.unpack("<HH10s", temp)
        try:
            decoded = raw_name.decode("utf-8", "ignore").rstrip("\x00").strip()
        except Exception:
            decoded = ""
        self.identifier = decoded or self.comport

        self.channel_names = [self.label(i) for i in range(self.channels)]
        self.response: Optional[bytes] = None

    def __del__(self) -> None:
        if hasattr(self, "port") and self.port.is_open:
            self.port.close()

    def msg(self, message: bytes, return_size: Optional[int] = None) -> None:
        try:
            if return_size is None:
                return_size = self.channels * self.buffer_length * BYTES_PER_SAMPLE
                self.port.timeout = SNAPSHOT_TIMEOUT
            else:
                self.port.timeout = DEFAULT_TIMEOUT

            tries_remaining = MAX_RETRY_ATTEMPTS
            while tries_remaining > 0:
                try:
                    self.port.write(message)
                    self.response = self.port.read(size=return_size)

                    if len(self.response) == return_size:
                        break

                except:
                    tries_remaining -= 1
                    self.port.flush()

            if tries_remaining == 0:
                self.response = None

        except:
            self.response = None

    def label(self, channel: int) -> str:
        try:
            self.port.write(LABEL_REQUEST_PREFIX + struct.pack("<I", channel))
            data = self.port.read(size=LABEL_RESPONSE_SIZE)
            return data.decode("utf-8", "ignore").rstrip("\x00").strip()

        except:
            return ""


class DeviceManager:
    def __init__(self):
        self.devices: Dict[str, Device] = {}
        self.channels = 0
        self.buffer_length = 0
        self._executor = ThreadPoolExecutor()
        self._msg_lock = asyncio.Lock()
        self._last_serial_settings: tuple | None = None

    def refresh_devices(self) -> None:
        try:
            from app.gui.settings import get_settings

            settings = get_settings()
        except Exception:
            settings = {}

        current_serial_norm = _normalize_serial_settings(settings)
        serial_kwargs = _serial_params_from_normalized(current_serial_norm)

        if (
            self._last_serial_settings is not None
            and current_serial_norm != self._last_serial_settings
        ):
            try:
                for dev in list(self.devices.values()):
                    try:
                        if getattr(dev, "port", None) is not None and dev.port.is_open:
                            dev.port.close()
                    except Exception:
                        pass
            finally:
                self.devices = {}
        self._last_serial_settings = current_serial_norm

        def _split_values(value: str) -> list[str]:
            if not value:
                return []
            parts = re.split(r"[\s,;]+", value)
            return [p for p in (part.strip() for part in parts) if p]

        def _parse_int(text: str) -> int:
            t = text.strip().lower()
            try:
                return int(t, 16) if t.startswith("0x") else int(t, 10)
            except Exception:
                raise

        vids_conf = str(settings.get("usb_vid", "") or "").strip()
        pids_conf = str(settings.get("usb_pid", "") or "").strip()
        regex_conf = str(settings.get("usb_name_regex", "") or "").strip()

        try:
            vids_list = [_parse_int(v) for v in _split_values(vids_conf)]
            pids_list = [_parse_int(p) for p in _split_values(pids_conf)]
        except Exception:
            vids_list, pids_list = [], []

        both_vid_and_pid_provided = len(vids_list) > 0 and len(pids_list) > 0

        name_regex = None
        if regex_conf:
            try:
                name_regex = re.compile(regex_conf, re.IGNORECASE)
            except re.error:
                name_regex = None

        def is_target_device(port) -> bool:
            port_vid = getattr(port, "vid", None)
            port_pid = getattr(port, "pid", None)
            description = getattr(port, "description", "") or ""

            if not both_vid_and_pid_provided:
                vid_pid_ok = False
            else:
                if len(vids_list) == len(pids_list):
                    pairs = set(zip(vids_list, pids_list))
                else:
                    pairs = {(v, p) for v in vids_list for p in pids_list}
                vid_pid_ok = (port_vid, port_pid) in pairs

            if name_regex is not None:
                try:
                    name_ok = bool(name_regex.search(description))
                except Exception:
                    name_ok = False
            else:
                name_ok = True

            return bool(vid_pid_ok and name_ok)

        def add_device(COM) -> None:
            if COM not in [device.comport for device in self.devices.values()]:
                new_device = Device(COM, serial_kwargs)
                if new_device.identifier not in self.devices:
                    self.devices[new_device.identifier] = new_device
            else:
                for device in self.devices.values():
                    if COM in device.comport:
                        device.configure()
                        break

        def remove_device(identifier) -> None:
            if identifier in self.devices:
                del self.devices[identifier]

        ports = [
            (p.serial_number, p.device) for p in ls.comports() if is_target_device(p)
        ]
        [add_device(com) for _, com in ports]

        current_com_ports = [com for _, com in ports]
        removed = [
            identifier
            for identifier, device in self.devices.items()
            if device.comport not in current_com_ports
        ]
        [remove_device(identifier) for identifier in removed]

        device_list = list(self.devices.values())
        devices_match = all(
            device.channels == device_list[0].channels
            and device.buffer_length == device_list[0].buffer_length
            and device.channel_names == device_list[0].channel_names
            for device in device_list
        )

        if not devices_match:
            first_device = device_list[0]
            mismatched = [
                f"{identifier}: {dev.channels}ch/{dev.buffer_length}buf"
                for identifier, dev in self.devices.items()
                if (
                    dev.channels != first_device.channels
                    or dev.buffer_length != first_device.buffer_length
                    or dev.channel_names != first_device.channel_names
                )
            ]
            raise ValueError(
                f"Device configuration mismatch. Expected {first_device.channels}ch/{first_device.buffer_length}buf with matching channel labels, but found: {', '.join(mismatched)}"
            )

        if len(ports) != len(self.devices):
            raise RuntimeError(
                f"Device initialization failed. Found {len(ports)} ports but only {len(self.devices)} devices initialized successfully"
            )

        if device_list:
            self.channels = device_list[0].channels
            self.buffer_length = device_list[0].buffer_length

    async def send_message(
        self,
        message: bytes,
        return_size: Optional[int] = None,
        *,
        acquire_timeout: float | None = None,
    ) -> None:
        acquire_coro = self._msg_lock.acquire()
        if acquire_timeout is None:
            await acquire_coro
        else:
            try:
                await asyncio.wait_for(acquire_coro, acquire_timeout)
            except asyncio.TimeoutError as exc:
                raise TimeoutError("Serial interface busy") from exc

        try:
            loop = asyncio.get_running_loop()
            tasks = [
                loop.run_in_executor(
                    self._executor, self.devices[identifier].msg, message, return_size
                )
                for identifier in self.devices
            ]
            await asyncio.gather(*tasks)

            failed_identifiers = [
                identifier
                for identifier, device in self.devices.items()
                if device.response is None
            ]
            for identifier in failed_identifiers:
                del self.devices[identifier]

            if failed_identifiers:
                raise RuntimeError(
                    f"Communication failed with devices: {', '.join(failed_identifiers)}"
                )
        finally:
            if self._msg_lock.locked():
                self._msg_lock.release()


# Global singleton instance for backward compatibility
_device_manager = DeviceManager()
devices = _device_manager.devices
channels = _device_manager.channels
buffer_length = _device_manager.buffer_length


def refresh_devices() -> None:
    global devices, channels, buffer_length
    _device_manager.refresh_devices()
    devices = _device_manager.devices
    channels = _device_manager.channels
    buffer_length = _device_manager.buffer_length


async def send_message(
    message: bytes,
    return_size: Optional[int] = None,
    *,
    acquire_timeout: float | None = None,
) -> None:
    await _device_manager.send_message(
        message, return_size, acquire_timeout=acquire_timeout
    )
