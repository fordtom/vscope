import sys
import asyncio
import time
from typing import Tuple, Dict

import numpy as np
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QMenuBar,
    QMenu,
)
from PyQt6.QtGui import QAction

from core import interface, devices, snapshots
from app.components.styling import apply_light_mode, get_stylesheet
from app.components.vscope_controls import VScopeControls
from app.components.rtbuffer_controls import RTBufferControls
from app.components.snapshot_list import SnapshotList
from app.callbacks.vscope_handlers import VScopeHandlers
from app.callbacks.rtbuffer_handlers import RTBufferHandlers
from app.callbacks.snapshot_handlers import SnapshotHandlers

from .settings import SettingsDialog, load_settings, get_settings  # re-export accessor

# Live buffer configuration: 10 seconds at 100ms sample time = 101 values (from -10 to 0 inclusive)
LIVE_BUFFER_SIZE = 101
LIVE_SAMPLE_TIME = 0.1  # 100ms


class ProperScopeGUI(QWidget):
    """Coordinator for the VScope application.

    Wires UI components and callback handlers, manages periodic sampling,
    and exposes lightweight helpers for frame buffer data used by plotting.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VScope Control Panel")
        self.setGeometry(100, 100, 800, 600)

        # Live-frame state - fixed-size FIFO buffers (101 values per channel, one per device)
        self.latest_frame_data = None
        self.frame_buffers: Dict[str, np.ndarray] = {}  # device_id -> [channels, 101] array
        self.buffer_index = 0  # Circular buffer index (0-100)

        # Build UI and handlers
        self.init_ui()
        self.vscope_handlers = VScopeHandlers(self)
        self.rtbuffer_handlers = RTBufferHandlers(self)
        self.snapshot_handlers = SnapshotHandlers(self)
        self.wire_signals()

        # Start timers for periodic sampling
        self.setup_periodic_sampling()

        # Load cached snapshots with retention from settings and refresh list
        try:
            settings = get_settings()
            retention_days = int(settings.get("cache_gc_days", 31))
            snapshots.load_from_cache(retention_days=retention_days)
        except Exception as exc:
            print(f"Warning: failed to load cached snapshots: {exc}")
        self.snapshot_handlers.refresh_snapshot_list()

        # Initialize trigger button to blank/disabled before first refresh
        self.vscope_controls.set_run_state("error")

    def init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Menu bar (File -> Settings)
        menu_bar = QMenuBar(self)
        file_menu = QMenu("&File", self)
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        file_menu.addAction(settings_action)
        menu_bar.addMenu(file_menu)
        layout.setMenuBar(menu_bar)

        # Top panel: VScope controls
        self.vscope_controls = VScopeControls(self)
        layout.addWidget(self.vscope_controls)
        # Middle panel: RT buffer controls
        self.rtbuffer_controls = RTBufferControls(self)
        layout.addWidget(self.rtbuffer_controls)
        # Bottom panel: snapshot list
        self.snapshot_panel = SnapshotList(self)
        layout.addWidget(self.snapshot_panel)

    def show_settings_dialog(self) -> None:
        dlg = SettingsDialog(self)
        if dlg.exec():
            # Optionally react to changed settings; for now, no-op
            pass

    def wire_signals(self) -> None:
        # Top panel
        self.vscope_controls.refresh_button.clicked.connect(
            self.vscope_handlers.on_refresh_clicked_wrapper
        )
        self.vscope_controls.run_button.clicked.connect(
            self.vscope_handlers.on_run_clicked
        )
        self.vscope_controls.save_button.clicked.connect(
            self.vscope_handlers.on_save_clicked
        )
        self.vscope_controls.trigger_button.clicked.connect(
            self.vscope_handlers.on_trigger_clicked
        )
        self.vscope_controls.acq_time_input.editingFinished.connect(
            lambda: self.vscope_handlers.on_acq_time_changed(
                self.vscope_controls.get_acq_time_value()
            )
        )
        self.vscope_controls.pretrigger_input.editingFinished.connect(
            lambda: self.vscope_handlers.on_pretrigger_time_changed(
                self.vscope_controls.get_pretrigger_value()
            )
        )

        # Middle panel (16 numeric inputs)
        for idx, input_widget in enumerate(self.rtbuffer_controls.buffer_inputs):
            input_widget.editingFinished.connect(
                (
                    lambda idx=idx, w=input_widget: self.rtbuffer_handlers.on_buffer_changed(
                        idx, w.value()
                    )
                )
            )

        # Bottom panel (snapshot list)
        lst = self.snapshot_panel.snapshot_list
        lst.itemClicked.connect(self.snapshot_handlers.on_snapshot_selected)
        lst.itemDoubleClicked.connect(self.snapshot_handlers.on_snapshot_double_clicked)
        lst.customContextMenuRequested.connect(
            self.snapshot_handlers.show_snapshot_context_menu
        )

    def setup_periodic_sampling(self) -> None:
        """Schedule async tasks to start once event loop is running."""
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(
            0,
            lambda: asyncio.create_task(self.sample_state_loop())
            and asyncio.create_task(self.sample_frame_loop())
            and print("Periodic sampling started: state=50ms, frame=100ms"),
        )

    async def sample_state_loop(self) -> None:
        """Periodic state sampler (20Hz) - runs in Qt event loop"""
        while True:
            if len(devices.devices) > 0:
                try:
                    state = await interface.get_state()
                    if state is not None:
                        state_mapping = {
                            0: "run",
                            1: "stop",
                            2: "acquiring",
                            3: "error",
                        }
                        state_value = ord(state) if isinstance(state, bytes) else state
                        button_state = state_mapping.get(state_value, "error")
                        if self.vscope_controls.get_run_state() != button_state:
                            self.vscope_controls.set_run_state(button_state)
                except Exception as exc:
                    print(f"Error sampling state: {exc}")
                    if self.vscope_controls.get_run_state() != "error":
                        self.vscope_controls.set_run_state("error")
            await asyncio.sleep(0.05)  # 20Hz = 50ms

    async def sample_frame_loop(self) -> None:
        """Periodic frame sampler (10Hz) - runs in Qt event loop"""
        while True:
            if len(devices.devices) > 0:
                try:
                    frame_data = await interface.get_frame()
                    if frame_data:
                        self.latest_frame_data = frame_data
                        # Initialize buffers if needed
                        if not self.frame_buffers:
                            self._initialize_frame_buffers()
                        # Reinitialize if device count changed
                        elif len(self.frame_buffers) != len(devices.devices):
                            self._initialize_frame_buffers()
                        # Add new frame to circular buffer
                        for device_id, channel_values in frame_data.items():
                            if device_id not in self.frame_buffers:
                                self._initialize_frame_buffers()
                            if device_id in self.frame_buffers:
                                frame_array = np.array(channel_values).reshape(-1, 1)
                                self.frame_buffers[device_id][:, self.buffer_index] = frame_array[:, 0]
                        self.buffer_index = (self.buffer_index + 1) % LIVE_BUFFER_SIZE
                except Exception:
                    # Silently ignore frame sampling errors
                    pass
            await asyncio.sleep(LIVE_SAMPLE_TIME)  # 10Hz = 100ms

    def _initialize_frame_buffers(self) -> None:
        """Initialize or reinitialize frame buffers with NaN values."""
        if len(devices.devices) == 0 or devices.channels is None:
            print(
                "No devices or channel configuration available - frame buffers left empty"
            )
            self.frame_buffers = {}
            return

        self.frame_buffers = {}
        for device in devices.devices.values():
            self.frame_buffers[device.identifier] = np.full(
                (devices.channels, LIVE_BUFFER_SIZE), np.nan
            )
        self.buffer_index = 0

    def initialize_frame_buffer(self) -> None:
        """Clear frame buffers by setting all values to NaN."""
        if len(devices.devices) == 0 or devices.channels is None:
            print(
                "No devices or channel configuration available - frame buffers left empty"
            )
            self.frame_buffers = {}
            self.buffer_index = 0
            return

        # Initialize buffers if they don't exist
        if not self.frame_buffers:
            self._initialize_frame_buffers()
            return

        # Set all values to NaN instead of clearing
        for device_id in list(self.frame_buffers.keys()):
            # Remove devices that no longer exist
            if device_id not in [d.identifier for d in devices.devices.values()]:
                del self.frame_buffers[device_id]
            else:
                self.frame_buffers[device_id][:] = np.nan
        
        # Add any new devices
        for device in devices.devices.values():
            if device.identifier not in self.frame_buffers:
                self.frame_buffers[device.identifier] = np.full(
                    (devices.channels, LIVE_BUFFER_SIZE), np.nan
                )
        
        self.buffer_index = 0
        print(
            f"Frame buffers cleared (set to NaN) - {LIVE_BUFFER_SIZE} values per channel"
        )

    def get_frame_buffer_data(self) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Get frame buffer data with fixed x-axis from -10 to 0 seconds."""
        if not self.frame_buffers:
            # Return empty arrays with correct shape
            x_data = np.linspace(-10.0, 0.0, LIVE_BUFFER_SIZE)
            return (x_data, {})
        
        # Create fixed x-axis from -10 to 0 seconds (inclusive)
        x_data = np.linspace(-10.0, 0.0, LIVE_BUFFER_SIZE)
        
        # Reorder buffers to show chronological order (oldest to newest)
        data_dict: Dict[str, np.ndarray] = {}
        for device_id, buffer in self.frame_buffers.items():
            # Roll buffer so oldest data is first (starting from buffer_index)
            reordered = np.roll(buffer, -self.buffer_index, axis=1)
            data_dict[device_id] = reordered
        
        return (x_data, data_dict)


def main() -> None:
    # Ensure settings are loaded at launch
    load_settings()

    import pyqtgraph as pg
    from qasync import QEventLoop

    app = pg.mkQApp()
    apply_light_mode(app)
    app.setStyleSheet(get_stylesheet())

    # Integrate qasync event loop
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = ProperScopeGUI()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
