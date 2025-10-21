import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

from .styling import LegendWidget, LINE_STYLES, LINE_STYLE_NAMES
from .core_plotting import (
    build_device_color_mapping,
    calculate_time_axis,
    create_plot_widgets,
    add_channel_labels,
    apply_window_styling,
)


class PlotWindow(QWidget):
    """
    Simple plotting window for a single VScope snapshot.
    Focus: Just get the data showing in stacked plots.
    """

    def __init__(self, snapshot, title="VScope Plot"):
        """
        Initialize the plot window for a single snapshot.

        Args:
            snapshot: Snapshot object containing the data
            title: Window title
        """
        super().__init__()
        self.snapshot = snapshot
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 800, 1200)
        self.setMinimumSize(600, 300)

        self.num_channels = snapshot.channels
        print(f"PlotWindow: Creating plots for {self.num_channels} channels")
        data = snapshot.get_data()
        print(f"PlotWindow: Snapshot has {len(data)} devices")
        for device_id, device_data in data.items():
            print(f"PlotWindow: Device {device_id} data shape: {device_data.shape}")

        # Check timing metadata
        self.has_timing = (
            snapshot.acquisition_time is not None
            and snapshot.pretrigger_time is not None
        )
        if self.has_timing:
            print(
                f"PlotWindow: Using timing metadata - acquisition: {snapshot.acquisition_time:.3f}s, pretrigger: {snapshot.pretrigger_time:.3f}s"
            )

        # Build device color mapping
        device_ids = list(snapshot.get_data().keys())
        self.device_colors = build_device_color_mapping(device_ids)

        # Set up the UI
        self.init_ui()

        # Generate the plots
        self.create_plots()

        # Show window as non-blocking
        self.show()

    def init_ui(self):
        """Initialize a simple UI with legend and stacked plots."""
        apply_window_styling(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Add legend
        self.legend_widget = LegendWidget()
        layout.addWidget(self.legend_widget)

        # Set title for single snapshot
        self.legend_widget.set_title(self.windowTitle())

        # Populate legend with device colors
        for device_id, color in self.device_colors.items():
            self.legend_widget.add_device_legend(device_id, color)

        # Finalize the legend layout
        self.legend_widget.finalize_layout()

        # Create plot widgets
        self.plot_widgets = create_plot_widgets(self.num_channels, self.has_timing)
        for plot_widget in self.plot_widgets:
            layout.addWidget(plot_widget)

    def create_plots(self):
        """Create plots with device-specific colors and improved visibility."""
        print(f"PlotWindow: Starting to plot data...")

        # Clear any existing plots
        for plot_widget in self.plot_widgets:
            plot_widget.clear()

        # Calculate x-axis data
        x_data, _ = calculate_time_axis(self.snapshot)

        # Plot each device's data with assigned colors
        for device_id, device_data in self.snapshot.get_data().items():
            print(f"PlotWindow: Plotting device {device_id}")
            color = self.device_colors[device_id]

            # Plot each channel for this device
            for channel in range(self.num_channels):
                y_data = device_data[channel, :]
                print(
                    f"PlotWindow: Channel {channel} - y_data range: [{np.min(y_data):.3f}, {np.max(y_data):.3f}]"
                )

                # Plot with device-specific color and solid line style
                pen = pg.mkPen(color=color, width=2, style=Qt.PenStyle.SolidLine)
                self.plot_widgets[channel].plot(x_data, y_data, pen=pen)
                print(f"PlotWindow: Added plot to channel {channel} with color {color}")

        # Auto-range all plots to fit data
        for channel, plot_widget in enumerate(self.plot_widgets):
            plot_widget.autoRange()
            print(f"PlotWindow: Auto-ranged channel {channel}")

        # Add channel labels
        if hasattr(self.snapshot, "channel_labels"):
            add_channel_labels(self.plot_widgets, self.snapshot.channel_labels)

        print(f"PlotWindow: Finished plotting")


def plot_single_snapshot(snapshot):
    """
    Create a plot window for a single snapshot.

    Args:
        snapshot: Snapshot object containing the data

    Returns:
        PlotWindow: The created plot window
    """
    title = snapshot.description
    return PlotWindow(snapshot, title)


class ComparisonPlotWindow(QWidget):
    """
    Plotting window for comparing multiple VScope snapshots.
    Each snapshot gets a different line style, devices get consistent colors.
    """

    def __init__(self, snapshots, title="VScope Comparison"):
        """
        Initialize the comparison plot window for multiple snapshots.

        Args:
            snapshots: Dictionary of {uid: snapshot} pairs to compare
            title: Window title
        """
        super().__init__()
        self.snapshots = snapshots
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 800, 1200)
        self.setMinimumSize(600, 300)

        # Use channels from first snapshot (assuming all have same channel count)
        first_snapshot = next(iter(snapshots.values()))
        self.num_channels = first_snapshot.channels
        print(f"ComparisonPlotWindow: Creating plots for {self.num_channels} channels")
        print(f"ComparisonPlotWindow: Comparing {len(snapshots)} snapshots")

        # Check timing metadata consistency
        self.has_timing = all(
            snapshot.acquisition_time is not None
            and snapshot.pretrigger_time is not None
            for snapshot in snapshots.values()
        )
        if self.has_timing:
            print(f"ComparisonPlotWindow: Using timing metadata for all snapshots")

        # Build comprehensive device color and snapshot style mappings
        self.device_colors, self.snapshot_styles = self._build_mappings()

        # Set up the UI
        self.init_ui()

        # Generate the plots
        self.create_plots()

        # Show window as non-blocking
        self.show()

    def _build_mappings(self):
        """Build comprehensive mappings for device colors and snapshot line styles."""
        # Collect all unique device IDs across all snapshots
        all_device_ids = set()
        for snapshot in self.snapshots.values():
            all_device_ids.update(snapshot.get_data().keys())

        # Build device color mapping
        device_colors = build_device_color_mapping(list(all_device_ids))

        # Assign line styles to snapshots
        snapshot_styles = {}
        snapshot_list = list(self.snapshots.items())
        for style_index, (snapshot_uid, snapshot) in enumerate(snapshot_list):
            style = LINE_STYLES[style_index % len(LINE_STYLES)]
            style_name = LINE_STYLE_NAMES[style_index % len(LINE_STYLE_NAMES)]
            snapshot_styles[snapshot_uid] = (style, style_name)
            print(
                f"ComparisonPlotWindow: Assigned {style_name} line style to snapshot {snapshot.description}"
            )

        return device_colors, snapshot_styles

    def init_ui(self):
        """Initialize a simple UI with comprehensive legend and stacked plots."""
        apply_window_styling(self)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Add comprehensive legend
        self.legend_widget = LegendWidget()
        layout.addWidget(self.legend_widget)

        # Populate legend with device colors
        for device_id, color in self.device_colors.items():
            self.legend_widget.add_device_legend(device_id, color)

        # Populate legend with snapshot line styles
        for snapshot_uid, snapshot in self.snapshots.items():
            style, style_name = self.snapshot_styles[snapshot_uid]
            self.legend_widget.add_snapshot_legend(snapshot.description, style_name)

        # Finalize the legend layout
        self.legend_widget.finalize_layout()

        # Create plot widgets
        self.plot_widgets = create_plot_widgets(self.num_channels, self.has_timing)
        for plot_widget in self.plot_widgets:
            layout.addWidget(plot_widget)

    def create_plots(self):
        """Create comparison plots with consistent device colors and snapshot-specific line styles."""
        print(f"ComparisonPlotWindow: Starting to plot comparison data...")

        # Clear any existing plots
        for plot_widget in self.plot_widgets:
            plot_widget.clear()

        # Plot each snapshot with consistent device colors and unique line styles
        for snapshot_uid, snapshot in self.snapshots.items():
            print(f"ComparisonPlotWindow: Plotting snapshot {snapshot.description}")

            # Get line style for this snapshot
            line_style, style_name = self.snapshot_styles[snapshot_uid]

            # Calculate x-axis data for this snapshot
            x_data, _ = calculate_time_axis(snapshot)

            # Plot each device's data for this snapshot
            for device_id, device_data in snapshot.get_data().items():
                print(
                    f"ComparisonPlotWindow: Plotting device {device_id} from snapshot {snapshot.description}"
                )

                # Get consistent color for this device
                color = self.device_colors[device_id]

                # Plot each channel for this device
                for channel in range(self.num_channels):
                    y_data = device_data[channel, :]

                    # Plot with consistent device color and snapshot-specific line style
                    pen = pg.mkPen(color=color, width=2, style=line_style)
                    self.plot_widgets[channel].plot(x_data, y_data, pen=pen)
                    print(
                        f"ComparisonPlotWindow: Added plot to channel {channel} with color {color} and {style_name} style"
                    )

        # Auto-range all plots to fit data
        for channel, plot_widget in enumerate(self.plot_widgets):
            plot_widget.autoRange()
            print(f"ComparisonPlotWindow: Auto-ranged channel {channel}")

        # Add channel labels
        first_snapshot = next(iter(self.snapshots.values()))
        if hasattr(first_snapshot, "channel_labels"):
            add_channel_labels(self.plot_widgets, first_snapshot.channel_labels)

        print(f"ComparisonPlotWindow: Finished comparison plotting")


def plot_multiple_snapshots(snapshots):
    """
    Create a comparison plot window for multiple snapshots.

    Args:
        snapshots: Dictionary of {uid: snapshot} pairs to compare

    Returns:
        ComparisonPlotWindow: The created comparison plot window
    """
    snapshot_names = [snapshot.description for snapshot in snapshots.values()]
    title = f"VScope Comparison - {', '.join(snapshot_names)}"
    return ComparisonPlotWindow(snapshots, title)
