from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PyQt6.QtCore import Qt


class NotifyDialog(QDialog):
    """A simple reusable notification dialog with a message and an OK button.

    Use for non-blocking informational/warning messages that require acknowledgment.
    """

    def __init__(
        self,
        parent=None,
        *,
        title: str = "Notice",
        message: str = "",
        rich_text: bool = False,
        minimum_width: int = 420,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(minimum_width)

        layout = QVBoxLayout(self)

        self._label = QLabel()
        if rich_text:
            self._label.setTextFormat(Qt.TextFormat.RichText)
        else:
            self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setWordWrap(True)
        self._label.setText(message)
        layout.addWidget(self._label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

    def set_message(self, message: str, *, rich_text: Optional[bool] = None) -> None:
        if rich_text is not None:
            self._label.setTextFormat(
                Qt.TextFormat.RichText if rich_text else Qt.TextFormat.PlainText
            )
        self._label.setText(message)
