from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QAbstractSpinBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.components.styling import COLOR_THEME


class VScopeControls(QFrame):
    """Top panel widget containing VScope controls and status.
    Provides UI elements and simple view-state methods; no device logic here.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.Box)

        self.run_state: str = "run"
        self._save_original_text: str | None = None
        self._save_original_style: str | None = None

        layout = QVBoxLayout(self)

        title_label = QLabel("VScope Controls")
        title_label.setFont(QFont("Arial", 15, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(8)
        layout.addLayout(grid_layout)

        # Buttons and labels
        self.refresh_button = QPushButton("Refresh")
        self.run_button = QPushButton("Run")
        self.save_button = QPushButton("Save")
        self.channels_label = QLabel("Channels:")
        self.samples_label = QLabel("Samples:")

        # Row 0
        grid_layout.addWidget(self.refresh_button, 0, 0)
        grid_layout.addWidget(self.run_button, 0, 1)

        self.channels_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        grid_layout.addWidget(self.channels_label, 0, 2)

        acq_time_label = QLabel("Acquisition Time:")
        acq_time_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        grid_layout.addWidget(acq_time_label, 0, 3)

        self.acq_time_input = QDoubleSpinBox()
        self.acq_time_input.setRange(0.001, 10000.0)
        self.acq_time_input.setValue(1.0)
        self.acq_time_input.setDecimals(3)
        self.acq_time_input.setSuffix(" s")
        self.acq_time_input.setMinimumWidth(80)
        self.acq_time_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        grid_layout.addWidget(self.acq_time_input, 0, 4)

        # Row 1
        grid_layout.addWidget(self.save_button, 1, 0)

        self.trigger_button = QPushButton("Trigger")
        grid_layout.addWidget(self.trigger_button, 1, 1)

        self.samples_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        grid_layout.addWidget(self.samples_label, 1, 2)

        pretrigger_label = QLabel("Pretrigger Time:")
        pretrigger_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        grid_layout.addWidget(pretrigger_label, 1, 3)

        self.pretrigger_input = QDoubleSpinBox()
        self.pretrigger_input.setRange(0.0, 1000.0)
        self.pretrigger_input.setValue(0.0)
        self.pretrigger_input.setDecimals(3)
        self.pretrigger_input.setSuffix(" s")
        self.pretrigger_input.setMinimumWidth(80)
        self.pretrigger_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        grid_layout.addWidget(self.pretrigger_input, 1, 4)

    # ---- View update helpers ----
    def set_refresh_count_label(self, device_count: int | None) -> None:
        if device_count is None or device_count == 0:
            self.refresh_button.setText("Refresh")
        else:
            self.refresh_button.setText(f"Refresh ({device_count})")

    def set_channel_samples_labels(
        self, channels: int | None, samples: int | None
    ) -> None:
        self.channels_label.setText(
            "MISMATCH" if channels is None else f"{channels} Channels"
        )
        self.samples_label.setText(
            "MISMATCH" if samples is None else f"{samples} Samples"
        )

    def set_run_state(self, state: str) -> None:
        state_config = {
            "run": ("Run", COLOR_THEME["run_button"]["run"]),
            "stop": ("Stop", COLOR_THEME["run_button"]["stop"]),
            "acquiring": ("Acquiring", COLOR_THEME["run_button"]["acquiring"]),
            "error": ("Error", COLOR_THEME["run_button"]["error"]),
        }
        if state in state_config:
            text, color = state_config[state]
            self.run_button.setText(text)
            self.run_button.setStyleSheet(
                f"background-color: {color}; color: {COLOR_THEME['text']['white']}; font-weight: bold;"
            )
            self.run_state = state
            self._update_trigger_for_run_state(state)

    def _update_trigger_for_run_state(self, run_state: str) -> None:
        if run_state in ("error", "acquiring"):
            self.trigger_button.setText("")
            self.trigger_button.setStyleSheet(
                f"background-color: {COLOR_THEME['button']['normal']}; "
                f"color: {COLOR_THEME['text']['secondary']}; "
                f"border-color: {COLOR_THEME['border']['normal']};"
            )
            self.trigger_button.setEnabled(False)
        elif run_state == "stop":
            self.trigger_button.setText("Trigger")
            self.trigger_button.setStyleSheet(
                f"background-color: {COLOR_THEME['run_button']['acquiring']}; "
                f"color: {COLOR_THEME['text']['white']}; font-weight: bold;"
            )
            self.trigger_button.setEnabled(True)
        elif run_state == "run":
            self.trigger_button.setText("View Live")
            self.trigger_button.setStyleSheet(
                f"background-color: {COLOR_THEME['run_button']['run']}; "
                f"color: {COLOR_THEME['text']['white']}; font-weight: bold;"
            )
            self.trigger_button.setEnabled(True)

    def set_timing_inputs(
        self, acquisition_time: float, pretrigger_time: float
    ) -> None:
        self.acq_time_input.setValue(acquisition_time)
        self.pretrigger_input.setValue(pretrigger_time)

    def get_acq_time_value(self) -> float:
        return self.acq_time_input.value()

    def get_pretrigger_value(self) -> float:
        return self.pretrigger_input.value()

    def set_save_button_saving(self, saving: bool) -> None:
        if saving:
            self._save_original_text = self.save_button.text()
            self._save_original_style = self.save_button.styleSheet()
            self.save_button.setText("Saving...")
            self.save_button.setStyleSheet(
                f"background-color: {COLOR_THEME['button']['saving']}; "
                f"color: {COLOR_THEME['text']['white']}; font-weight: bold;"
            )
            self.save_button.setEnabled(False)
        else:
            if self._save_original_text is not None:
                self.save_button.setText(self._save_original_text)
            if self._save_original_style is not None:
                self.save_button.setStyleSheet(self._save_original_style)
            self.save_button.setEnabled(True)
            self._save_original_text = None
            self._save_original_style = None

    def get_run_state(self) -> str:
        return self.run_state
