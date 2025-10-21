from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QListWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class SnapshotList(QFrame):
    """Bottom panel widget for listing, selecting and context actions for snapshots."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)

        layout = QVBoxLayout(self)

        title_label = QLabel("Snapshots")
        title_label.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        self.snapshot_list = QListWidget()
        self.snapshot_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.snapshot_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.snapshot_list)
