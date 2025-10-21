import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# Configure PyQtGraph for light theme
pg.setConfigOption("background", "#F8F9FA")  # Light grey background
pg.setConfigOption("foreground", "#212529")  # Dark grey foreground

# Define a set of 8 distinct colors for different devices
DEVICE_COLORS = [
    "#1f77b4",  # Blue
    "#ff7f0e",  # Orange
    "#2ca02c",  # Green
    "#d62728",  # Red
    "#9467bd",  # Purple
    "#8c564b",  # Brown
    "#e377c2",  # Pink
    "#7f7f7f",  # Grey
]

# Define line styles for different snapshots
LINE_STYLES = [
    Qt.PenStyle.SolidLine,  # Solid
    Qt.PenStyle.DashLine,  # Dashed
    Qt.PenStyle.DotLine,  # Dotted
    Qt.PenStyle.DashDotLine,  # Dash-dot
    Qt.PenStyle.DashDotDotLine,  # Dash-dot-dot
]

LINE_STYLE_NAMES = [
    "Solid",
    "Dashed",
    "Dotted",
    "Dash-dot",
    "Dash-dot-dot",
]


class LegendWidget(QWidget):
    """
    Compact legend widget with 2 rows: title/snapshots on top, devices on bottom.
    """

    def __init__(self):
        super().__init__()
        self.setStyleSheet(
            """
            QWidget {
                background-color: #F8F9FA;
                border: 1px solid #DEE2E6;
                border-radius: 4px;
                padding: 4px;
            }
            QLabel {
                color: #495057;
                background-color: transparent;
                border: none;
                padding: 1px;
                font-size: 11px;
            }
        """
        )

        # Main vertical layout for 2 rows
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(2)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.setLayout(self.main_layout)

        # Top row for title or snapshots
        self.top_row = QHBoxLayout()
        self.top_row.setSpacing(8)
        self.main_layout.addLayout(self.top_row)

        # Bottom row for devices
        self.bottom_row = QHBoxLayout()
        self.bottom_row.setSpacing(8)
        self.bottom_row.addStretch()  # Center the devices
        self.main_layout.addLayout(self.bottom_row)

        self.setMaximumHeight(60)  # Very compact height

    def set_title(self, title):
        """Set a simple title for single snapshot plots."""
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.top_row.addWidget(title_label)

    def add_snapshot_legend(self, snapshot_description, line_style_name):
        """Add a snapshot line style legend entry to the top row."""
        # Create compact snapshot entry
        snapshot_widget = QWidget()
        snapshot_layout = QHBoxLayout()
        snapshot_layout.setSpacing(4)
        snapshot_layout.setContentsMargins(0, 0, 0, 0)
        snapshot_widget.setLayout(snapshot_layout)

        # Line style indicator
        if line_style_name == "Solid":
            style_char = "━━━"
        elif line_style_name == "Dashed":
            style_char = "╌╌╌"
        elif line_style_name == "Dotted":
            style_char = "┅┅┅"
        elif line_style_name == "Dash-dot":
            style_char = "╍╍╍"
        else:
            style_char = "┄┄┄"

        style_label = QLabel(style_char)
        style_label.setStyleSheet("font-size: 12px; font-weight: bold;")

        # Snapshot name
        name_label = QLabel(snapshot_description)
        name_label.setStyleSheet("font-weight: bold; font-size: 11px;")

        snapshot_layout.addWidget(style_label)
        snapshot_layout.addWidget(name_label)

        self.top_row.addWidget(snapshot_widget)

    def add_device_legend(self, device_id, color):
        """Add a device color legend entry to the bottom row."""
        # Create compact device entry
        device_widget = QWidget()
        device_layout = QHBoxLayout()
        device_layout.setSpacing(3)
        device_layout.setContentsMargins(0, 0, 0, 0)
        device_widget.setLayout(device_layout)

        # Colored square
        color_label = QLabel("■")
        color_label.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: bold;"
        )

        # Device name
        name_label = QLabel(device_id)
        name_label.setStyleSheet("font-weight: bold; font-size: 11px;")

        device_layout.addWidget(color_label)
        device_layout.addWidget(name_label)

        self.bottom_row.insertWidget(
            self.bottom_row.count() - 1, device_widget
        )  # Insert before stretch

    def finalize_layout(self):
        """Call this after adding all items to finalize the layout."""
        # Center the top row content (title or snapshots)
        if self.top_row.count() == 0:
            self.top_row.addStretch()
        else:
            # Add stretches on both sides to center snapshots
            self.top_row.insertStretch(0)
            self.top_row.addStretch()

        # Center the bottom row content (devices) - remove the existing stretch and add centered stretches
        if self.bottom_row.count() > 1:  # Remove the initial stretch we added
            stretch_item = self.bottom_row.takeAt(
                self.bottom_row.count() - 1
            )  # Remove last stretch
            # Add stretches on both sides to center devices
            self.bottom_row.insertStretch(0)
            self.bottom_row.addStretch()
