from PyQt6.QtWidgets import QFrame, QVBoxLayout, QGridLayout, QLabel, QAbstractSpinBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.components.styling import SignificantFiguresSpinBox


class RTBufferControls(QFrame):
    """Middle panel widget for real-time buffer read/write controls."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)

        layout = QVBoxLayout(self)

        title_label = QLabel("RT Buffer Controls")
        title_label.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)
        layout.addLayout(grid_layout)

        self.buffer_inputs = []
        buffer_index = 1
        for row in range(4):
            for col in range(0, 8, 2):
                label = QLabel(f"Buffer {buffer_index:02d}:")
                label.setAlignment(
                    Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                )
                grid_layout.addWidget(label, row, col)

                buffer_input = SignificantFiguresSpinBox()
                buffer_input.setRange(-1000.0, 1000.0)
                buffer_input.setValue(0.0)
                buffer_input.setDecimals(9)
                buffer_input.setMinimumWidth(80)
                buffer_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
                grid_layout.addWidget(buffer_input, row, col + 1)

                self.buffer_inputs.append(buffer_input)
                buffer_index += 1
