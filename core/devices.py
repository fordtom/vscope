import serial, asyncio, struct, re
from concurrent.futures import ThreadPoolExecutor
import serial.tools.list_ports as ls
from typing import Dict, Optional

devices: Dict[str, "Device"] = {}
channels = 0
buffer_length = 0
_executor = ThreadPoolExecutor()
_msg_lock = asyncio.Lock()


_last_serial_settings: tuple | None = None


def _normalize_serial_settings(settings: dict) -> tuple:
    """Return a normalized tuple of serial settings for change detection.

    Tuple format: (baud, data_bits, stop_bits, parity_code)
    """
    try:
        baud = int(settings.get("serial_baud", 115200))
    except Exception:
        baud = 115200
    try:
        data_bits = int(settings.get("serial_data_bits", 8))
        if data_bits not in (5, 6, 7, 8):
            data_bits = 8
    except Exception:
        data_bits = 8
    try:
        stop_bits = float(settings.get("serial_stop_bits", 1.0))
        if stop_bits not in (1.0, 1.5, 2.0):
            stop_bits = 1.0
    except Exception:
        stop_bits = 1.0
    try:
        parity_code = str(settings.get("serial_parity", "N")).upper()
        if parity_code not in ("N", "E", "O", "M", "S"):
            parity_code = "N"
    except Exception:
        parity_code = "N"
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
        # No flow control for now (can be added later)
        "xonxoff": False,
        "rtscts": False,
    }


class Device:
    def __init__(self, path, serial_kwargs: dict | None = None) -> None:
        self.comport = path
        if serial_kwargs is None:
            # Fallback to defaults if not provided
            serial_kwargs = _serial_params_from_normalized((115200, 8, 1.0, "N"))
        self.port = serial.Serial(path, **serial_kwargs)
        self.port.flush()

        self.configure()

    def configure(self):
        self.port.timeout = 0.02

        # Handshake: request config; device responds with: [u16 n_ch][u16 buf_len][10-byte name]
        self.port.write(b"h00000000")
        temp = self.port.read(size=14)

        # Unpack as two 16-bit little-endian unsigned integers and a 10-byte identifier
        self.channels, self.buffer_length, raw_name = struct.unpack("<HH10s", temp)
        try:
            decoded = raw_name.decode("utf-8", "ignore").rstrip("\x00").strip()
        except Exception:
            decoded = ""
        # Use provided identifier, otherwise fall back to the serial port name
        self.identifier = decoded or self.comport

        self.channel_names = [self.label(i) for i in range(self.channels)]
        self.response: Optional[bytes] = None

    def __del__(self) -> None:
        if hasattr(self, "port") and self.port.is_open:
            self.port.close()

    def msg(self, message: bytes, return_size: Optional[int] = None) -> None:
        try:
            if return_size is None:
                return_size = self.channels * self.buffer_length * 4
                self.port.timeout = 10
            else:
                self.port.timeout = 0.02

            tries_remaining = 3
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
            self.port.write(b"l0000" + struct.pack("<I", channel))
            data = self.port.read(size=41)
            return data.decode("utf-8", "ignore").rstrip("\x00").strip()

        except:
            return ""


def refresh_devices() -> None:
    global devices, channels, buffer_length

    # Load USB identification overrides from settings at refresh time
    try:
        from app.gui.settings import get_settings

        settings = get_settings()
    except Exception:
        settings = {}

    # Determine serial configuration at refresh time
    global _last_serial_settings
    current_serial_norm = _normalize_serial_settings(settings)
    serial_kwargs = _serial_params_from_normalized(current_serial_norm)

    # If serial settings changed, close all devices and clear map so we reopen cleanly
    if (
        _last_serial_settings is not None
        and current_serial_norm != _last_serial_settings
    ):
        try:
            for dev in list(devices.values()):
                try:
                    if getattr(dev, "port", None) is not None and dev.port.is_open:
                        dev.port.close()
                except Exception:
                    pass
        finally:
            devices = {}
    _last_serial_settings = current_serial_norm

    def _split_values(value: str) -> list[str]:
        if not value:
            return []
        # Split on commas and/or whitespace, ignore empties
        parts = re.split(r"[\s,;]+", value)
        return [p for p in (part.strip() for part in parts) if p]

    def _parse_int(text: str) -> int:
        t = text.strip().lower()
        try:
            return int(t, 16) if t.startswith("0x") else int(t, 10)
        except Exception:
            # If parsing fails, raise to surface configuration issues
            raise

    vids_conf = str(settings.get("usb_vid", "") or "").strip()
    pids_conf = str(settings.get("usb_pid", "") or "").strip()
    regex_conf = str(settings.get("usb_name_regex", "") or "").strip()

    try:
        vids_list = [_parse_int(v) for v in _split_values(vids_conf)]
        pids_list = [_parse_int(p) for p in _split_values(pids_conf)]
    except Exception:
        # On invalid VID/PID entries, disable VID/PID filtering (treated as unset)
        vids_list, pids_list = [], []

    # Require both VID and PID to be provided to enable matching
    both_vid_and_pid_provided = len(vids_list) > 0 and len(pids_list) > 0

    name_regex = None
    if regex_conf:
        try:
            name_regex = re.compile(regex_conf, re.IGNORECASE)
        except re.error:
            name_regex = None

    # Finding ports based on vendor ID, product ID, and optional name filter
    def is_target_device(port) -> bool:
        port_vid = getattr(port, "vid", None)
        port_pid = getattr(port, "pid", None)
        description = getattr(port, "description", "") or ""

        # Determine VID/PID match
        if not both_vid_and_pid_provided:
            # If either VID or PID is missing, do not match any devices
            vid_pid_ok = False
        else:
            if len(vids_list) == len(pids_list):
                pairs = set(zip(vids_list, pids_list))
            else:
                # If lengths differ, allow cross-product to support multi-pairs
                pairs = {(v, p) for v in vids_list for p in pids_list}
            vid_pid_ok = (port_vid, port_pid) in pairs

        # Determine name/description match
        if name_regex is not None:
            try:
                name_ok = bool(name_regex.search(description))
            except Exception:
                name_ok = False
        else:
            # No regex configured: do not filter by name
            name_ok = True

        return bool(vid_pid_ok and name_ok)

    def add_device(COM) -> None:
        global devices
        if COM not in [device.comport for device in devices.values()]:
            new_device = Device(COM, serial_kwargs)
            if new_device.identifier not in devices:
                devices[new_device.identifier] = new_device
        else:
            for device in devices.values():
                if COM in device.comport:
                    device.configure()
                    break

    def remove_device(identifier) -> None:
        global devices
        if identifier in devices:
            del devices[identifier]

    ports = [(p.serial_number, p.device) for p in ls.comports() if is_target_device(p)]
    [add_device(com) for _, com in ports]

    # Remove devices whose COM ports are no longer available
    current_com_ports = [com for _, com in ports]
    removed = [
        identifier
        for identifier, device in devices.items()
        if device.comport not in current_com_ports
    ]
    [remove_device(identifier) for identifier in removed]

    # Check that all devices have matching channels, buffer_length, and channel_names
    device_list = list(devices.values())
    devices_match = all(
        device.channels == device_list[0].channels
        and device.buffer_length == device_list[0].buffer_length
        and device.channel_names == device_list[0].channel_names
        for device in device_list
    )

    if not devices_match:
        # Collect mismatched device info for the error message
        first_device = device_list[0]
        mismatched = [
            f"{identifier}: {dev.channels}ch/{dev.buffer_length}buf"
            for identifier, dev in devices.items()
            if (
                dev.channels != first_device.channels
                or dev.buffer_length != first_device.buffer_length
                or dev.channel_names != first_device.channel_names
            )
        ]
        raise ValueError(
            f"Device configuration mismatch. Expected {first_device.channels}ch/{first_device.buffer_length}buf with matching channel labels, but found: {', '.join(mismatched)}"
        )

    if len(ports) != len(devices):
        raise RuntimeError(
            f"Device initialization failed. Found {len(ports)} ports but only {len(devices)} devices initialized successfully"
        )

    if device_list:
        channels = device_list[0].channels
        buffer_length = device_list[0].buffer_length


async def send_message(message: bytes, return_size: Optional[int] = None) -> None:
    global devices
    async with _msg_lock:
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(
                _executor, devices[identifier].msg, message, return_size
            )
            for identifier in devices
        ]
        await asyncio.gather(*tasks)

        failed_identifiers = [
            identifier
            for identifier, device in devices.items()
            if device.response is None
        ]
        for identifier in failed_identifiers:
            del devices[identifier]

        if failed_identifiers:
            raise RuntimeError(
                f"Communication failed with devices: {', '.join(failed_identifiers)}"
            )
