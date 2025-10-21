import asyncio
from typing import List

from PyQt6.QtWidgets import (
    QApplication,
    QMessageBox,
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt

from core import interface, devices, snapshots
from app import plot
from app.components.styling import COLOR_THEME
from app.gui.settings import get_settings
from app.gui.notify import NotifyDialog


class SnapshotDescriptionDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save Snapshot")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        label = QLabel("Enter a description for this snapshot:")
        layout.addWidget(label)

        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText(
            "e.g., Test configuration 1, 100kHz, 2.5V..."
        )
        layout.addWidget(self.description_input)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.description_input.setFocus()

    def get_description(self) -> str:
        return self.description_input.text().strip()


class VScopeHandlers:
    """Handlers for VScope top-panel controls: refresh/run/save/trigger/timing/state."""

    def __init__(self, window) -> None:
        self.window = window

    # ---- Refresh ----
    def on_refresh_clicked_wrapper(self) -> None:
        # Warn and abort if VID/PID are not configured
        try:
            settings = get_settings()
            vids_conf = str(settings.get("usb_vid", "") or "").strip()
            pids_conf = str(settings.get("usb_pid", "") or "").strip()
            # Require both VID and PID to be present
            if not vids_conf or not pids_conf:
                msg = (
                    "USB VID and PID are required.\n\n"
                    "Open Settings (File → Settings…) and set both a Vendor ID (VID) "
                    "and a Product ID (PID) for your devices."
                )
                NotifyDialog(
                    self.window, title="USB Filters Required", message=msg
                ).exec()
                return
        except Exception:
            # If settings access fails, proceed with best effort
            pass

        asyncio.create_task(self.on_refresh_clicked())

    def on_refresh_clicked_fallback(self) -> None:
        print("Refresh button clicked (fallback mode)")
        # Warn and abort if VID/PID are not configured
        try:
            settings = get_settings()
            vids_conf = str(settings.get("usb_vid", "") or "").strip()
            pids_conf = str(settings.get("usb_pid", "") or "").strip()
            if not vids_conf or not pids_conf:
                msg = (
                    "USB VID and PID are required.\n\n"
                    "Open Settings (File → Settings…) and set both a Vendor ID (VID) "
                    "and a Product ID (PID) for your device."
                )
                NotifyDialog(
                    self.window, title="USB Filters Required", message=msg
                ).exec()
                return
        except Exception:
            pass
        interface.refresh()
        device_count = len(devices.devices)
        self.window.vscope_controls.set_refresh_count_label(device_count)
        self.window.vscope_controls.set_channel_samples_labels(
            devices.channels, devices.buffer_length
        )
        self.window.vscope_controls.set_run_state("run")
        self.window.initialize_frame_buffer()
        print("Frame buffer initialized with NaN values due to refresh")
        print(
            f"Found {device_count} devices with {devices.channels} channels and {devices.buffer_length} samples"
        )

    async def on_refresh_clicked(self) -> None:
        print("Refresh button clicked")
        interface.refresh()
        device_count = len(devices.devices)
        self.window.vscope_controls.set_refresh_count_label(device_count)
        self.window.vscope_controls.set_channel_samples_labels(
            devices.channels, devices.buffer_length
        )

        if device_count > 0:
            try:
                state = await interface.get_state()
                if state is not None:
                    state_mapping = {0: "run", 1: "stop", 2: "acquiring", 3: "error"}
                    state_value = ord(state) if isinstance(state, bytes) else state
                    button_state = state_mapping.get(state_value, "error")
                    self.window.vscope_controls.set_run_state(button_state)
                    print(f"Device state: {state_value} -> {button_state}")
                else:
                    self.window.vscope_controls.set_run_state("error")
                    print("Failed to get device state - state mismatch")

                sample_time, pretrigger_time = await interface.get_timing()
                if sample_time is not None and pretrigger_time is not None:
                    self.window.vscope_controls.set_timing_inputs(
                        sample_time, pretrigger_time
                    )
                    print(
                        f"Timing updated: acquisition={sample_time:.3f}s, pretrigger={pretrigger_time:.3f}s"
                    )
                else:
                    print("Failed to get timing configuration - device mismatch")

                # Buffers
                if hasattr(self.window.rtbuffer_controls, "buffer_inputs"):
                    print("Reading buffer values...")
                    for buffer_index in range(16):
                        try:
                            buffer_value = await interface.get_buff(buffer_index)
                            if buffer_value is not None:
                                self.window.rtbuffer_controls.buffer_inputs[
                                    buffer_index
                                ].setValue(buffer_value)
                            else:
                                print(
                                    f"Buffer {buffer_index + 1}: mismatch between devices"
                                )
                        except Exception as buffer_error:
                            print(
                                f"Error reading buffer {buffer_index + 1}: {buffer_error}"
                            )
                    print("Buffer values updated")

            except Exception as exc:
                self.window.vscope_controls.set_run_state("error")
                print(f"Error getting device state/timing: {exc}")
        else:
            self.window.vscope_controls.set_run_state("run")

        self.window.initialize_frame_buffer()
        print("Frame buffer initialized with NaN values due to refresh")
        self.window.snapshot_handlers.refresh_snapshot_list()
        print(
            f"Found {device_count} devices with {devices.channels} channels and {devices.buffer_length} samples"
        )

    # ---- Run/Trigger/Save ----
    def on_run_clicked(self) -> None:
        current_state = self.window.vscope_controls.get_run_state()
        print(f"Run button clicked - Current state: {current_state}")

        if len(devices.devices) == 0:
            print("No devices connected - cannot change state")
            return

        if current_state in ("error", "acquiring"):
            print(f"State is {current_state} - no action taken")
            return
        elif current_state == "run":
            asyncio.create_task(self.set_device_state_async(1))
            print("Sent set_state(1) - transitioning to stop")
        elif current_state == "stop":
            asyncio.create_task(self.set_device_state_async(0))
            print("Sent set_state(0) - transitioning to run")

    def on_trigger_clicked(self) -> None:
        current_state = self.window.vscope_controls.get_run_state()
        print(f"Trigger button clicked - Current state: {current_state}")

        if len(devices.devices) == 0:
            print("No devices connected - cannot trigger")
            return

        if current_state in ("error", "acquiring"):
            print(f"State is {current_state} - no action taken")
            return
        elif current_state == "run":
            print("View Live button clicked - creating live plot window")
            try:
                live_plot_window = plot.create_live_plot(self.window)
                if not hasattr(self.window, "live_plot_windows"):
                    self.window.live_plot_windows = []
                self.window.live_plot_windows.append(live_plot_window)
                print("Successfully created live plot window")
            except Exception as exc:
                error_msg = f"Failed to create live plot:\n{str(exc)}"
                QMessageBox.critical(self.window, "Live Plot Error", error_msg)
                print(f"Error creating live plot: {exc}")
            return
        elif current_state == "stop":
            asyncio.create_task(self.set_device_state_async(2))
            print("Sent set_state(2) - triggering acquisition")

    def on_save_clicked(self) -> None:
        print("Save button clicked")

        if len(devices.devices) == 0:
            QMessageBox.warning(
                self.window, "No Devices", "No devices connected. Cannot save snapshot."
            )
            return

        dialog = SnapshotDescriptionDialog(self.window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            description = dialog.get_description()
            if not description:
                QMessageBox.warning(
                    self.window,
                    "No Description",
                    "Please enter a description for the snapshot.",
                )
                return

            self.window.vscope_controls.set_save_button_saving(True)

            async def do_save():
                try:
                    await self.save_snapshot_async(description)
                except Exception as exc:
                    print(f"Error saving snapshot: {exc}")
                    QMessageBox.critical(
                        self.window, "Save Error", f"Failed to save snapshot:\n{str(exc)}"
                    )
                finally:
                    self.window.vscope_controls.set_save_button_saving(False)

            asyncio.create_task(do_save())

    async def save_snapshot_async(self, description: str) -> None:
        print(f"Starting snapshot save with description: '{description}'")
        acquisition_time = self.window.vscope_controls.get_acq_time_value()
        pretrigger_time = self.window.vscope_controls.get_pretrigger_value()
        await interface.get_snapshot(description, acquisition_time, pretrigger_time)
        print(f"Snapshot saved successfully: '{description}'")
        self.window.initialize_frame_buffer()
        print("Frame buffer initialized with NaN values after snapshot download")
        self.window.snapshot_handlers.refresh_snapshot_list()

    # ---- Timing/State helpers ----
    async def set_device_state_async(self, state: int) -> None:
        success = await interface.set_state(state)
        if success:
            state_mapping = {0: "run", 1: "stop", 2: "acquiring"}
            expected_state = state_mapping.get(state, "error")
            self.window.vscope_controls.set_run_state(expected_state)
            print(f"Successfully set device state to {state} -> {expected_state}")
        else:
            print(f"Failed to set device state to {state} - setting error state")
            self.window.vscope_controls.set_run_state("error")
            try:
                stop_success = await interface.set_state(0)
                if stop_success:
                    print("Emergency stop successful")
                else:
                    print("Emergency stop also failed")
            except Exception as exc:
                print(f"Error during emergency stop: {exc}")

    def on_acq_time_changed(self, _value: float) -> None:
        print(
            f"Acquisition Time changed: {self.window.vscope_controls.get_acq_time_value()} s"
        )
        self.update_timing()

    def on_pretrigger_time_changed(self, _value: float) -> None:
        print(
            f"Pretrigger Time changed: {self.window.vscope_controls.get_pretrigger_value()} s"
        )
        self.update_timing()

    def update_timing(self) -> None:
        if len(devices.devices) == 0:
            print("No devices connected - cannot update timing")
            return
        if self.window.vscope_controls.get_run_state() != "run":
            print(
                f"Cannot update timing - device state is {self.window.vscope_controls.get_run_state()} (only allowed in 'run' state)"
            )
            return
        acq_time = self.window.vscope_controls.get_acq_time_value()
        pretrigger_time = self.window.vscope_controls.get_pretrigger_value()
        asyncio.create_task(self.update_timing_async(acq_time, pretrigger_time))

    async def update_timing_async(
        self, sample_time: float, pretrigger_time: float
    ) -> None:
        success = await interface.set_timing(sample_time, pretrigger_time)
        if success:
            print(
                f"Successfully updated timing: acquisition={sample_time:.3f}s, pretrigger={pretrigger_time:.3f}s"
            )
            try:
                (
                    actual_sample_time,
                    actual_pretrigger_time,
                ) = await interface.get_timing()
                if (
                    actual_sample_time is not None
                    and actual_pretrigger_time is not None
                ):
                    self.window.vscope_controls.set_timing_inputs(
                        actual_sample_time, actual_pretrigger_time
                    )
                    print(
                        f"Readback values: acquisition={actual_sample_time:.3f}s, pretrigger={actual_pretrigger_time:.3f}s"
                    )
                else:
                    print("Failed to read back timing values - device mismatch")
            except Exception as exc:
                print(f"Error reading back timing values: {exc}")
        else:
            print(
                f"Failed to update timing: acquisition={sample_time:.3f}s, pretrigger={pretrigger_time:.3f}s"
            )
