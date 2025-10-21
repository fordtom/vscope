from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Mapping

import tomllib
import tomli_w
from platformdirs import user_config_dir

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QCheckBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
)

# Module-level cache for settings
_SETTINGS_CACHE: Dict[str, Any] | None = None
_CONFIG_DIR: Path | None = None
_CONFIG_PATH: Path | None = None


def get_default_settings() -> Dict[str, Any]:
    """Return default settings used when no config file exists.

    Dummy values for initial implementation; can be expanded as needed.
    """
    return {
        # Acquisition sample rate for timing calculations (Hz)
        "onboard_polling_rate": 50_000.0,
        # Cache garbage collection retention in days
        "cache_gc_days": 31,
        # Serial interface configuration (used when opening devices)
        # Defaults: 115200 baud, 8N1
        "serial_baud": 115200,
        "serial_data_bits": 8,  # 5,6,7,8
        "serial_stop_bits": 1.0,  # 1, 1.5, 2
        "serial_parity": "N",  # N,E,O,M,S
        # USB device detection overrides (blank = use built-in defaults)
        # Accept multiple values as comma/space-separated lists for VID/PID
        "usb_vid": "",
        "usb_pid": "",
        # Optional regex to further filter by port name/description
        "usb_name_regex": "",
    }


def get_config_dir() -> Path:
    global _CONFIG_DIR
    if _CONFIG_DIR is None:
        if sys.platform == "win32":
            _CONFIG_DIR = Path(user_config_dir("vscope", appauthor=False))
        else:
            base = os.environ.get("XDG_CONFIG_HOME")
            if base:
                _CONFIG_DIR = Path(base) / "vscope"
            else:
                _CONFIG_DIR = Path.home() / ".config" / "vscope"
    return _CONFIG_DIR


def get_config_path() -> Path:
    """Primary config file path: vscope/config.toml in user config dir."""
    global _CONFIG_PATH
    if _CONFIG_PATH is None:
        _CONFIG_PATH = get_config_dir() / "config.toml"
    return _CONFIG_PATH


def get_legacy_config_path() -> Path:
    """Legacy filename kept for backward compatibility: .vscopeconfig"""
    return get_config_dir() / ".vscopeconfig"


def _read_config_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as fp:
            data = tomllib.load(fp)
            if not isinstance(data, dict):
                return {}
            return data
    except Exception:
        # On any parse or IO error, fall back to defaults
        return {}


def _write_config_file(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fp:
        tomli_w.dump(dict(data), fp)


def load_settings(force_reload: bool = False) -> Dict[str, Any]:
    """Load settings from config file, overlaying defaults.

    The loaded settings are cached module-wide and returned. Use
    force_reload=True to bypass the cache.
    """
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is not None and not force_reload:
        return _SETTINGS_CACHE

    defaults = get_default_settings()

    # Prefer new path; if absent, try legacy filename once for back-compat
    new_path = get_config_path()
    if new_path.exists():
        file_values = _read_config_file(new_path)
    else:
        legacy_path = get_legacy_config_path()
        file_values = _read_config_file(legacy_path) if legacy_path.exists() else {}

    # Overlay: values from file override defaults, unknown keys kept as-is
    merged: Dict[str, Any] = {**defaults, **file_values}
    _SETTINGS_CACHE = merged
    return merged


def save_settings(settings: Mapping[str, Any]) -> None:
    """Persist provided settings to the config file and update cache."""
    global _SETTINGS_CACHE
    _write_config_file(get_config_path(), settings)
    _SETTINGS_CACHE = dict(settings)


def get_settings() -> Dict[str, Any]:
    """Get the current settings (loading from disk if necessary)."""
    return load_settings(force_reload=False)


class SettingsDialog(QDialog):
    """Generic settings editor for flat key/value settings.

    Widgets are chosen by value type (bool/int/float/str). Unknown types are
    rendered as strings.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")

        self._inputs: Dict[str, Any] = {}
        form = QFormLayout(self)

        current = get_settings()

        # Only expose the supported settings in a stable order
        visible_keys = [
            "onboard_polling_rate",
            "cache_gc_days",
            # Serial interface settings
            "serial_baud",
            "serial_data_bits",
            "serial_stop_bits",
            "serial_parity",
            "usb_vid",
            "usb_pid",
            "usb_name_regex",
        ]

        for key in visible_keys:
            value = current.get(key, get_default_settings().get(key))

            # Custom widgets for serial settings for better UX and value safety
            if key == "serial_baud":
                widget = QSpinBox()
                widget.setRange(300, 10_000_000)
                widget.setSingleStep(100)
                try:
                    # Common baud rates as quick picks via keyboard arrows
                    pass
                except Exception:
                    pass
            elif key == "cache_gc_days":
                widget = QComboBox()
                for days in (1, 3, 7, 14, 31, 90):
                    label = f"{days} day" if days == 1 else f"{days} days"
                    widget.addItem(label, int(days))
            elif key == "serial_data_bits":
                widget = QComboBox()
                for bits in (5, 6, 7, 8):
                    widget.addItem(str(bits), bits)
            elif key == "serial_stop_bits":
                widget = QComboBox()
                for sb in (1.0, 1.5, 2.0):
                    widget.addItem(str(sb).rstrip("0").rstrip("."), sb)
            elif key == "serial_parity":
                widget = QComboBox()
                parity_options = [
                    ("N", "None (N)"),
                    ("E", "Even (E)"),
                    ("O", "Odd (O)"),
                    ("M", "Mark (M)"),
                    ("S", "Space (S)"),
                ]
                for code, label in parity_options:
                    widget.addItem(label, code)
            else:
                widget = self._create_input_for_value(value)

            # Specialize the sample rate control for better UX
            if key == "onboard_polling_rate" and hasattr(widget, "setDecimals"):
                try:
                    # Configure as a Hz input with sensible bounds
                    widget.setDecimals(1)
                    widget.setRange(1.0, 10_000_000.0)
                    widget.setSingleStep(1_000.0)
                    if hasattr(widget, "setSuffix"):
                        widget.setSuffix(" Hz")
                except Exception:
                    pass

            self._set_widget_value(widget, value)
            self._inputs[key] = widget
            form.addRow(key, widget)

            # Provide helpful placeholders for USB settings
            try:
                from PyQt6.QtWidgets import (
                    QLineEdit,
                )  # local import to avoid type issues

                if isinstance(widget, QLineEdit):
                    if key == "usb_vid":
                        widget.setPlaceholderText("e.g., 0x1D50, 0x2A03")
                    elif key == "usb_pid":
                        widget.setPlaceholderText("e.g., 0x6015, 0x0043")
                    elif key == "usb_name_regex":
                        widget.setPlaceholderText(
                            "Optional regex to filter name, e.g., application"
                        )
            except Exception:
                # Placeholders are optional; ignore if widget/types unavailable
                pass

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save_clicked)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        # Widen dialog to 1.5x the default suggested width
        size_hint = self.sizeHint()
        self.resize(int(size_hint.width() * 1.5), size_hint.height())

    def _create_input_for_value(self, value: Any):
        if isinstance(value, bool):
            return QCheckBox()
        if isinstance(value, int) and not isinstance(value, bool):
            spin = QSpinBox()
            spin.setRange(-2_000_000_000, 2_000_000_000)
            return spin
        if isinstance(value, float):
            dspin = QDoubleSpinBox()
            dspin.setRange(-1e12, 1e12)
            dspin.setDecimals(6)
            return dspin
        # Fallback to string
        return QLineEdit()

    def _set_widget_value(self, widget, value: Any) -> None:
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value))
        elif isinstance(widget, QComboBox):
            # Match by stored user data when available, fallback by text
            try:
                idx = widget.findData(value)
                if idx < 0 and isinstance(value, str):
                    idx = widget.findData(value.upper())
                if idx < 0:
                    idx = widget.findText(str(value))
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            except Exception:
                pass
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))

    def _get_widget_value(self, widget, original: Any) -> Any:
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QSpinBox):
            return int(widget.value())
        if isinstance(widget, QDoubleSpinBox):
            return float(widget.value())
        if isinstance(widget, QComboBox):
            data = widget.currentData()
            return data if data is not None else widget.currentText()
        if isinstance(widget, QLineEdit):
            # Preserve type if original was stringifiable numeric? Keep as text.
            return widget.text()
        return widget.text() if hasattr(widget, "text") else original

    def _on_save_clicked(self) -> None:
        current = get_settings()
        # Only persist the supported subset, dropping any legacy/unused keys
        visible_keys = [
            "onboard_polling_rate",
            "cache_gc_days",
            "serial_baud",
            "serial_data_bits",
            "serial_stop_bits",
            "serial_parity",
            "usb_vid",
            "usb_pid",
            "usb_name_regex",
        ]
        result: Dict[str, Any] = {}
        for key in visible_keys:
            widget = self._inputs.get(key)
            if widget is not None:
                result[key] = self._get_widget_value(widget, current.get(key))
            else:
                result[key] = current.get(key, get_default_settings().get(key))

        save_settings(result)
        self.accept()
