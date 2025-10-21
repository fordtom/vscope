import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer

from .styling import LegendWidget
from .core_plotting import (
    build_device_color_mapping,
    create_plot_widgets,
    apply_window_styling,
)


class LivePlotWindow(QWidget):
    """
    Live plotting window that shows real-time data from the frame buffer.
    """

    def __init__(self, gui_reference, title="VScope Live View"):
        """
        Initialize the live plot window.

        Args:
            gui_reference: Reference to the main GUI for data access
            title: Window title
        """
        super().__init__()
        self.gui = gui_reference
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 800, 1200)
        self.setMinimumSize(600, 300)

        # Get initial configuration from connected devices
        from core import devices

        self.num_channels = devices.channels if devices.channels is not None else 0
        print(f"LivePlotWindow: Creating live plots for {self.num_channels} channels")
        print(f"LivePlotWindow: Found {len(devices.devices)} connected devices")

        # Check if we have valid configuration
        if self.num_channels == 0 or len(devices.devices) == 0:
            print(
                "LivePlotWindow: No valid device configuration - window may not display data"
            )

        # Build device color mapping
        device_ids = []
        if devices.devices:
            device_ids = [device.identifier for device in devices.devices.values()]
        self.device_colors = build_device_color_mapping(device_ids)

        # Track last update time to avoid unnecessary redraws
        self.last_update_time = 0

        # Set up the UI
        self.init_ui()

        # Set up live data updates
        self.setup_live_updates()

        # Show window as non-blocking
        self.show()

    def init_ui(self):
        """Initialize UI with legend and stacked plots."""
        apply_window_styling(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Add legend
        self.legend_widget = LegendWidget()
        layout.addWidget(self.legend_widget)

        # Set title for live data
        self.legend_widget.set_title("Live Data")

        # Populate legend with device colors
        for device_id, color in self.device_colors.items():
            self.legend_widget.add_device_legend(device_id, color)

        # Finalize the legend layout
        self.legend_widget.finalize_layout()

        # Create plot widgets - live view always uses time axis
        self.plot_widgets = create_plot_widgets(self.num_channels, has_timing=True)
        for plot_widget in self.plot_widgets:
            layout.addWidget(plot_widget)

    def setup_live_updates(self):
        """Set up timer for periodic live data updates."""
        # Update every 100ms (10Hz) - same as frame sampling rate
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_plots)
        self.update_timer.start(100)
        print("LivePlotWindow: Started live update timer (100ms interval)")

    def update_plots(self):
        """Update plots with current frame buffer data."""
        # Get current frame buffer data
        timestamps, data_dict = self.gui.get_frame_buffer_data()

        # Skip update if no data available
        if len(timestamps) == 0 or not data_dict:
            return

        # Skip update if data hasn't changed since last update
        if len(timestamps) > 0 and timestamps[-1] == self.last_update_time:
            return

        # Update last update time
        self.last_update_time = timestamps[-1] if len(timestamps) > 0 else 0

        # Clear existing plots
        for plot_widget in self.plot_widgets:
            plot_widget.clear()

        # Create time axis relative to current time (oscilloscope-style scrolling)
        current_time = timestamps[-1] if len(timestamps) > 0 else 0
        x_data = timestamps - current_time  # Relative time (negative values = past)

        # Plot each device's data with assigned colors
        for device_id, device_data in data_dict.items():
            if device_id not in self.device_colors:
                continue

            color = self.device_colors[device_id]

            # Plot each channel for this device
            for channel in range(min(self.num_channels, device_data.shape[0])):
                y_data = device_data[channel, :]

                # Skip plotting if all data is NaN
                if np.all(np.isnan(y_data)):
                    continue

                pen = pg.mkPen(color=color, width=2, style=Qt.PenStyle.SolidLine)
                self.plot_widgets[channel].plot(x_data, y_data, pen=pen)

        # Auto-range all plots to fit data
        for plot_widget in self.plot_widgets:
            plot_widget.autoRange()

        # Add channel labels
        self._add_channel_labels()

    def _add_channel_labels(self):
        """Add channel labels to the top right corner of each plot."""
        from core import devices

        if not devices.devices:
            return

        first_device = list(devices.devices.values())[0]
        if not hasattr(first_device, "channel_names"):
            return

        channel_names = first_device.channel_names
        if not channel_names:
            return

        for channel, plot_widget in enumerate(self.plot_widgets):
            if channel >= len(channel_names):
                continue

            channel_label = channel_names[channel]
            if not channel_label or not channel_label.strip():
                continue

            # Create text item for the channel label
            text_item = pg.TextItem(text=channel_label, color="#495057", anchor=(1, 0))

            view_box = plot_widget.getViewBox()
            plot_widget.addItem(text_item)

            # Position in top right corner with padding
            x_range = view_box.viewRange()[0]
            y_range = view_box.viewRange()[1]
            padding_x = (x_range[1] - x_range[0]) * 0.02
            padding_y = (y_range[1] - y_range[0]) * 0.05

            text_item.setPos(x_range[1] - padding_x, y_range[1] - padding_y)

    def closeEvent(self, event):
        """Handle window close event by stopping the update timer."""
        if hasattr(self, "update_timer"):
            self.update_timer.stop()
            print("LivePlotWindow: Stopped live update timer")
        event.accept()


def create_live_plot(gui_reference):
    """
    Create a live plot window for real-time data display.

    Args:
        gui_reference: Reference to the main GUI for data access

    Returns:
        LivePlotWindow: The created live plot window
    """
    return LivePlotWindow(gui_reference)
