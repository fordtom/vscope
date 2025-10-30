import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

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
        self._legend_registered_devices = set()

        # Set up the UI
        self.init_ui()

        # Track state for labels and plot items
        self._labels_added = False
        self.curves = {}
        self.x_data = None

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
            self._legend_registered_devices.add(device_id)

        # Finalize the legend layout
        self.legend_widget.finalize_layout()

        # Create plot widgets - live view always uses time axis
        self.plot_widgets = create_plot_widgets(self.num_channels, has_timing=True)
        for plot_widget in self.plot_widgets:
            layout.addWidget(plot_widget)

    def setup_live_updates(self):
        """Bind live updates to GUI frame notifications."""
        self.x_data, _ = self.gui.get_frame_buffer_data()
        if self.x_data.size == 0:
            # Fallback to default axis when buffers uninitialized
            self.x_data = np.linspace(-10.0, 0.0, 101)

        for plot_widget in self.plot_widgets:
            view_box = plot_widget.getViewBox()
            view_box.setXRange(float(self.x_data[0]), float(self.x_data[-1]), padding=0)
            view_box.enableAutoRange(x=False, y=True)

        if hasattr(self.gui, "frame_updated"):
            self.gui.frame_updated.connect(self.update_plots)

        self.update_plots(-1)

    def update_plots(self, _write_index: int = -1):
        """Refresh plot curves using the circular buffers."""
        frame_buffers = getattr(self.gui, "frame_buffers", {})
        if not frame_buffers:
            if self.x_data is None:
                self.x_data = np.linspace(-10.0, 0.0, 101)
            blank = np.full_like(self.x_data, np.nan)
            for curve in self.curves.values():
                curve.setData(self.x_data, blank, connect="finite")
            return

        self._sync_device_colors(frame_buffers)
        self._sync_curves(frame_buffers)

        buffer_index = getattr(self.gui, "buffer_index", 0)

        for device_id, buffer in frame_buffers.items():
            for channel in range(min(self.num_channels, buffer.shape[0])):
                curve = self.curves.get((device_id, channel))
                if curve is None:
                    curve = self._create_curve(device_id, channel)
                    if curve is None:
                        continue

                ordered = np.roll(buffer[channel], -buffer_index)
                curve.setData(self.x_data, ordered, connect="finite")

        self._add_channel_labels()

    def _add_channel_labels(self):
        """Add channel labels to the top right corner of each plot."""
        from core import devices

        if self._labels_added:
            return

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

        self._labels_added = True

    def _sync_device_colors(self, frame_buffers):
        device_ids = sorted(frame_buffers.keys())
        if not device_ids:
            return

        if set(device_ids) != set(self.device_colors.keys()):
            self.device_colors = build_device_color_mapping(device_ids)

        for device_id in device_ids:
            if device_id not in self._legend_registered_devices:
                color = self.device_colors[device_id]
                self.legend_widget.add_device_legend(device_id, color)
                self._legend_registered_devices.add(device_id)

    def _create_curve(self, device_id, channel):
        if channel >= len(self.plot_widgets):
            return None

        color = self.device_colors.get(device_id)
        if color is None:
            return None

        pen = pg.mkPen(color=color, width=2, style=Qt.PenStyle.SolidLine)
        plot_widget = self.plot_widgets[channel]
        curve = pg.PlotDataItem(
            self.x_data, np.full_like(self.x_data, np.nan), pen=pen, connect="finite"
        )
        plot_widget.addItem(curve)
        self.curves[(device_id, channel)] = curve
        return curve

    def _sync_curves(self, frame_buffers):
        active_keys = {
            (device_id, channel)
            for device_id, buffer in frame_buffers.items()
            for channel in range(min(self.num_channels, buffer.shape[0]))
        }

        for key, curve in list(self.curves.items()):
            if key not in active_keys:
                _, channel = key
                if channel < len(self.plot_widgets):
                    self.plot_widgets[channel].removeItem(curve)
                del self.curves[key]

        for key in active_keys:
            if key not in self.curves:
                self._create_curve(*key)

    def closeEvent(self, event):
        """Handle window close event by disconnecting live updates."""
        if hasattr(self.gui, "frame_updated"):
            try:
                self.gui.frame_updated.disconnect(self.update_plots)
            except TypeError:
                pass
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
