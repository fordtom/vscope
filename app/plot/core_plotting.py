import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt

from .styling import DEVICE_COLORS


def build_device_color_mapping(device_ids):
    """Build a mapping of device IDs to colors for consistent coloring."""
    device_colors = {}
    sorted_ids = sorted(device_ids)
    for idx, device_id in enumerate(sorted_ids):
        device_colors[device_id] = DEVICE_COLORS[idx % len(DEVICE_COLORS)]
        print(f"Assigned color {device_colors[device_id]} to device {device_id}")
    return device_colors


def calculate_time_axis(snapshot):
    """Calculate x-axis data based on snapshot timing metadata."""
    has_timing = (
        snapshot.acquisition_time is not None and snapshot.pretrigger_time is not None
    )

    if has_timing:
        # Create time axis centered around 0 (trigger point)
        x_data = np.linspace(
            -snapshot.pretrigger_time,
            snapshot.acquisition_time - snapshot.pretrigger_time,
            snapshot.buffer_length,
        )
        print(f"Using time axis from {x_data[0]:.3f}s to {x_data[-1]:.3f}s")
        return x_data, True
    else:
        # Fallback to sample indices
        x_data = np.arange(snapshot.buffer_length)
        print(f"Using sample index from 0 to {snapshot.buffer_length - 1}")
        return x_data, False


def create_plot_widgets(num_channels, has_timing):
    """Create and configure plot widgets for each channel."""
    plot_widgets = []
    for channel in range(num_channels):
        plot_widget = pg.PlotWidget()
        plot_widget.setBackground("#FFFFFF")

        # Configure axes (only bottom plot shows labels)
        if channel == num_channels - 1:
            plot_widget.setLabel("left", "")
            if has_timing:
                plot_widget.setLabel("bottom", "Time (s)")
            else:
                plot_widget.setLabel("bottom", "")
        else:
            plot_widget.setLabel("left", "")
            plot_widget.setLabel("bottom", "")

        plot_widget.showGrid(x=True, y=True, alpha=0.1)
        plot_widget.setMinimumHeight(100)

        # Link x-axes to first plot for synchronization
        if channel > 0:
            plot_widget.setXLink(plot_widgets[0])

        plot_widgets.append(plot_widget)
        print(f"Created plot widget for channel {channel}")

    return plot_widgets


def add_channel_labels(plot_widgets, channel_labels):
    """Add channel labels to the top right corner of each plot."""
    if not channel_labels:
        print("No channel labels available")
        return

    for channel, plot_widget in enumerate(plot_widgets):
        if channel >= len(channel_labels):
            continue

        channel_label = channel_labels[channel]
        if not channel_label or not channel_label.strip():
            continue

        # Create text item for the channel label
        text_item = pg.TextItem(
            text=channel_label,
            color="#495057",
            anchor=(1, 0),  # Top right anchor
        )

        view_box = plot_widget.getViewBox()
        plot_widget.addItem(text_item)

        # Position in top right corner with padding
        x_range = view_box.viewRange()[0]
        y_range = view_box.viewRange()[1]
        padding_x = (x_range[1] - x_range[0]) * 0.02
        padding_y = (y_range[1] - y_range[0]) * 0.05

        text_item.setPos(x_range[1] - padding_x, y_range[1] - padding_y)
        print(f"Added label '{channel_label}' to channel {channel}")


def apply_window_styling(widget):
    """Apply consistent light theme styling to a plot window."""
    widget.setStyleSheet(
        """
        QWidget {
            background-color: #F8F9FA;
            color: #212529;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QLabel {
            color: #495057;
            background-color: transparent;
            padding: 8px;
        }
    """
    )
