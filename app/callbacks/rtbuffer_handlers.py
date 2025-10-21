import asyncio

from core import interface, devices


class RTBufferHandlers:
    """Handlers for reading/writing real-time buffer values."""

    def __init__(self, window) -> None:
        self.window = window

    def on_buffer_changed(self, buffer_index: int, value: float) -> None:
        print(f"Buffer {buffer_index + 1} changed: {value}")
        self.update_buffer(buffer_index, value)

    def update_buffer(self, buffer_index: int, value: float) -> None:
        if len(devices.devices) == 0:
            print(f"No devices connected - cannot update buffer {buffer_index + 1}")
            return
        asyncio.create_task(self.update_buffer_async(buffer_index, value))

    async def update_buffer_async(self, buffer_index: int, value: float) -> None:
        success = await interface.set_buff(buffer_index, value)
        if success:
            print(f"Successfully updated buffer {buffer_index + 1} to {value:.3f}")
            try:
                actual_value = await interface.get_buff(buffer_index)
                if actual_value is not None:
                    self.window.rtbuffer_controls.buffer_inputs[buffer_index].setValue(
                        actual_value
                    )
                    print(f"Buffer {buffer_index + 1} readback: {actual_value:.3f}")
                else:
                    print(
                        f"Failed to read back buffer {buffer_index + 1} - device mismatch"
                    )
            except Exception as exc:
                print(f"Error reading back buffer {buffer_index + 1}: {exc}")
        else:
            print(f"Failed to update buffer {buffer_index + 1} to {value:.3f}")
