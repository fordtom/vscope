import struct
import numpy as np
from . import devices, snapshots

# Default configuration constants
DEFAULT_ONBOARD_POLLING_RATE = 50_000.0
TIMING_REQUEST_SIZE = 8
SINGLE_BYTE_RESPONSE = 1
FLOAT_SIZE = 4
SUCCESS_RESPONSE = b"\x00"
FLOAT_COMPARISON_EPSILON = 1e-6


def refresh():
    devices.refresh_devices()


async def get_timing():
    """
    Timing config message returns the vscope configuration:
    - bytes 0-3: divider value (sampled every nth sample based on a 50khz frequency)
    - bytes 4-7: pretrigger value (number of samples before the trigger)
    """
    data = b"t00000000"
    await devices.send_message(data, TIMING_REQUEST_SIZE)

    # Extract divider/pretrigger from all devices and check consistency
    configs = [
        struct.unpack("<II", device.response)
        for device in devices.devices.values()
        if device.response is not None
    ]

    if not configs or not all(config == configs[0] for config in configs):
        return (None, None)

    # Calculate times using the consistent values and configured sample rate
    divider, pretrigger = configs[0]
    try:
        from app.gui.settings import get_settings

        settings = get_settings()
        onboard_polling_rate = float(
            settings.get("onboard_polling_rate", DEFAULT_ONBOARD_POLLING_RATE)
        )
        if onboard_polling_rate <= 0:
            onboard_polling_rate = DEFAULT_ONBOARD_POLLING_RATE
    except Exception:
        onboard_polling_rate = DEFAULT_ONBOARD_POLLING_RATE

    sample_time = divider * devices.buffer_length / onboard_polling_rate
    pretrigger_time = pretrigger * divider / onboard_polling_rate

    return (sample_time, pretrigger_time)


async def set_timing(sample_time_seconds: float, pretrigger_time_seconds: float):
    """
    Sets both divider and pretrigger values from real time values.

    Args:
        sample_time_seconds: Total sample time in seconds
        pretrigger_time_seconds: Pre-trigger time in seconds

    Returns:
        True if successful, False if invalid parameters or communication failed
    """
    # Calculate integer values from real times using configured sample rate
    try:
        from app.gui.settings import get_settings

        settings = get_settings()
        onboard_polling_rate = float(
            settings.get("onboard_polling_rate", DEFAULT_ONBOARD_POLLING_RATE)
        )
        if onboard_polling_rate <= 0:
            onboard_polling_rate = DEFAULT_ONBOARD_POLLING_RATE
    except Exception:
        onboard_polling_rate = DEFAULT_ONBOARD_POLLING_RATE

    divider = max(
        1, round(sample_time_seconds * onboard_polling_rate / devices.buffer_length)
    )
    pretrigger = min(
        devices.buffer_length,
        round(pretrigger_time_seconds * onboard_polling_rate / divider),
    )

    timing_message = b"T" + struct.pack("<II", divider, pretrigger)
    await devices.send_message(timing_message, SINGLE_BYTE_RESPONSE)

    for device in devices.devices.values():
        if device.response != SUCCESS_RESPONSE:
            return False

    return True


async def get_state():
    """
    Gets the state of the devices.

    Returns:
        State if all devices match, None if no devices or mismatch
    """
    data = b"s00000000"
    await devices.send_message(data, SINGLE_BYTE_RESPONSE)
    states = [device.response for device in devices.devices.values()]
    if not states or not all(state == states[0] for state in states):
        return None
    return states[0]


async def set_state(state: int):
    """
    Sets the state of the devices.

    Args:
        state: State to set (0, 1, or 2)
    """
    data = b"S0000000" + bytes([state])
    await devices.send_message(data, SINGLE_BYTE_RESPONSE)

    for device in devices.devices.values():
        if device.response != SUCCESS_RESPONSE:
            return False
    return True


async def get_buff(buffer: int):
    """
    Read buffer value from devices.

    Args:
        buffer: Buffer index to read

    Returns:
        Float value if all devices match, None if no devices or mismatch
    """
    data = b"b0000" + struct.pack("<I", buffer)
    await devices.send_message(data, FLOAT_SIZE)

    values = [
        struct.unpack("<f", device.response)[0]
        for device in devices.devices.values()
        if device.response is not None
    ]
    if not values or not all(
        abs(value - values[0]) < FLOAT_COMPARISON_EPSILON for value in values
    ):
        return None

    return values[0]


async def set_buff(number: int, value: float) -> bool:
    """
    Used to write buffer values - the buffer values are fp32 values sent as 32-bit data.

    Args:
        number: Buffer index/address
        value: Float32 value to write

    Returns:
        True if successful, False if communication failed
    """
    buffer_message = b"B" + struct.pack("<If", number, value)
    await devices.send_message(buffer_message, SINGLE_BYTE_RESPONSE)

    for device in devices.devices.values():
        if device.response != SUCCESS_RESPONSE:
            return False

    return True


async def get_frame(lock_timeout: float | None = None):
    """
    Gets a single frame of data from devices.

    Returns:
        Dictionary of device identifiers to numpy arrays of frame data
    """
    data = b"f00000000"
    await devices.send_message(
        data, (FLOAT_SIZE * devices.channels), acquire_timeout=lock_timeout
    )
    return {
        device.identifier: struct.unpack(
            f"<{len(device.response) // FLOAT_SIZE}f", device.response
        )
        for device in devices.devices.values()
        if device.response is not None
    }


async def get_snapshot(
    description: str, acquisition_time: float, pretrigger_time: float
) -> None:
    """
    Creates a snapshot with timing metadata.

    Args:
        description: Description of the snapshot
        acquisition_time: Total acquisition time in seconds
        pretrigger_time: Pre-trigger time in seconds
    """
    uid = snapshots.new(
        description,
        devices.channels,
        devices.buffer_length,
        acquisition_time,
        pretrigger_time,
        list(devices.devices.values())[0].channel_names,
    )

    data = b"d00000000"
    await devices.send_message(data, None)

    for device in devices.devices.values():
        if device.response is not None:
            float_data = struct.unpack(
                f"<{len(device.response) // FLOAT_SIZE}f", device.response
            )
            reshaped = (
                np.array(float_data)
                .reshape(devices.buffer_length, devices.channels)
                .transpose()
            )
            snapshots.storage[uid].set_data(device.identifier, reshaped)

    # Persist snapshot to cache after data has been populated
    snapshots.storage[uid].cache()
