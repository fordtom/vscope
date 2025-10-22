import sys
import asyncio
import time
from collections import deque
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


class ProperScopeGUI(QWidget):
    """Coordinator for the VScope application.

    Wires UI components and callback handlers, manages periodic sampling,
    and exposes lightweight helpers for frame buffer data used by plotting.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("VScope Control Panel")
        self.setGeometry(100, 100, 800, 600)

        # Live-frame state
        self.latest_frame_data = None
        self.frame_buffer: deque = deque(maxlen=100)  # ~10 seconds at 10Hz

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
                        processed_frame_data: Dict[str, np.ndarray] = {}
                        for device_id, channel_values in frame_data.items():
                            processed_frame_data[device_id] = np.array(
                                channel_values
                            ).reshape(-1, 1)
                        timestamp = time.time()
                        self.frame_buffer.append((timestamp, processed_frame_data))
                except Exception:
                    # Silently ignore frame sampling errors
                    pass
            await asyncio.sleep(0.1)  # 10Hz = 100ms

    def initialize_frame_buffer(self) -> None:
        """Pre-populate frame buffer with NaNs for smooth scrolling plots."""
        self.frame_buffer.clear()
        if len(devices.devices) == 0 or devices.channels is None:
            print(
                "No devices or channel configuration available - frame buffer left empty"
            )
            return

        current_time = time.time()
        buffer_duration = self.frame_buffer.maxlen * 0.1  # 10Hz sampling
        for i in range(self.frame_buffer.maxlen):
            timestamp = current_time - buffer_duration + (i * 0.1)
            nan_frame_data: Dict[str, np.ndarray] = {}
            for device in devices.devices.values():
                nan_frame_data[device.identifier] = np.full(
                    (devices.channels, 1), np.nan
                )
            self.frame_buffer.append((timestamp, nan_frame_data))

        print(
            f"Frame buffer initialized with {self.frame_buffer.maxlen} NaN entries for smooth scrolling"
        )
        device_identifiers = [device.identifier for device in devices.devices.values()]
        if len(device_identifiers) > 0:
            print(f"Using device identifiers: {device_identifiers}")
        else:
            print("No device identifiers found during initialization")

    def get_frame_buffer_data(self) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        if not self.frame_buffer:
            return (np.array([]), {})
        timestamps = np.array([entry[0] for entry in self.frame_buffer])
        data_dict: Dict[str, np.ndarray] = {}
        for device_id in self.frame_buffer[0][1].keys():
            device_frames = [
                frame_data[device_id] for _, frame_data in self.frame_buffer
            ]
            data_dict[device_id] = np.concatenate(device_frames, axis=1)
        return (timestamps, data_dict)


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
