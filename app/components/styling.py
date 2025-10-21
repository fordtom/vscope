from PyQt6.QtWidgets import QDoubleSpinBox

# Color theme for UI elements
COLOR_THEME = {
    # Main application colors
    "background": {
        "main": "#F8F9FA",  # Very light grey for main background
        "panel": "#FFFFFF",  # White for panels/frames
        "input": "#FFFFFF",  # White for input fields
        "button": "#E9ECEF",  # Light grey for normal buttons
        "button_hover": "#DEE2E6",  # Slightly darker grey for hover
        "alternate": "#F1F3F4",  # Alternate background for lists
    },
    # Text colors
    "text": {
        "primary": "#212529",  # Dark grey for primary text
        "secondary": "#6C757D",  # Medium grey for secondary text
        "label": "#495057",  # Dark grey for labels
        "placeholder": "#ADB5BD",  # Light grey for placeholder text
        "white": "#FFFFFF",  # White text for dark backgrounds
    },
    # Border and frame colors
    "border": {
        "normal": "#DEE2E6",  # Light grey for normal borders
        "focus": "#80BDFF",  # Light blue for focused elements
        "frame": "#CED4DA",  # Medium grey for frame borders
    },
    # State-specific button colors (existing run button theme)
    "run_button": {
        "run": "#007BFF",  # Blue - slightly darker than before
        "stop": "#FD7E14",  # Orange - slightly darker than before
        "acquiring": "#28A745",  # Green - slightly darker than before
        "error": "#DC3545",  # Red - slightly darker than before
    },
    # Standard button colors
    "button": {
        "normal": "#E9ECEF",  # Light grey for normal buttons
        "hover": "#DEE2E6",  # Slightly darker grey for hover
        "pressed": "#CED4DA",  # Medium grey for pressed state
        "primary": "#007BFF",  # Blue for primary buttons
        "primary_hover": "#0056B3",  # Darker blue for primary hover
        "secondary": "#6C757D",  # Grey for secondary buttons
        "secondary_hover": "#545B62",  # Darker grey for secondary hover
        "save": "#28A745",  # Green for save button
        "save_hover": "#1E7E34",  # Darker green for save hover
        "saving": "#FD7E14",  # Orange for saving state
    },
    # Input field colors
    "input": {
        "background": "#FFFFFF",  # White background
        "border": "#CED4DA",  # Light grey border
        "border_focus": "#80BDFF",  # Light blue border when focused
        "text": "#495057",  # Dark grey text
        "placeholder": "#ADB5BD",  # Light grey placeholder
    },
    # List and table colors
    "list": {
        "background": "#FFFFFF",  # White background
        "alternate": "#F8F9FA",  # Very light grey for alternating rows
        "selected": "#E3F2FD",  # Light blue for selected items
        "selected_text": "#1565C0",  # Dark blue text for selected items
        "hover": "#F5F5F5",  # Light grey for hover
        "border": "#DEE2E6",  # Light grey border
    },
    # Scrollbar colors
    "scrollbar": {
        "background": "#F8F9FA",  # Light grey background
        "handle": "#CED4DA",  # Medium grey handle
        "handle_hover": "#ADB5BD",  # Darker grey handle on hover
    },
    # Frame and panel colors
    "frame": {
        "background": "#FFFFFF",  # White background for frames
        "border": "#DEE2E6",  # Light grey border
        "title_background": "#F8F9FA",  # Very light grey for title areas
        "title_text": "#495057",  # Dark grey for title text
    },
    # Dialog colors
    "dialog": {
        "background": "#FFFFFF",  # White background
        "border": "#CED4DA",  # Medium grey border
        "title_background": "#F8F9FA",  # Light grey title background
        "title_text": "#495057",  # Dark grey title text
    },
}


def apply_light_mode(app):
    """Force light mode by setting application style and palette"""
    # Set a consistent style across platforms
    app.setStyle("Fusion")

    # Create a light palette
    from PyQt6.QtGui import QPalette, QColor

    light_palette = QPalette()

    # Set main colors
    light_palette.setColor(
        QPalette.ColorRole.Window, QColor(COLOR_THEME["background"]["main"])
    )
    light_palette.setColor(
        QPalette.ColorRole.WindowText, QColor(COLOR_THEME["text"]["primary"])
    )
    light_palette.setColor(
        QPalette.ColorRole.Base, QColor(COLOR_THEME["input"]["background"])
    )
    light_palette.setColor(
        QPalette.ColorRole.AlternateBase, QColor(COLOR_THEME["background"]["alternate"])
    )
    light_palette.setColor(
        QPalette.ColorRole.Text, QColor(COLOR_THEME["text"]["primary"])
    )
    light_palette.setColor(
        QPalette.ColorRole.Button, QColor(COLOR_THEME["button"]["normal"])
    )
    light_palette.setColor(
        QPalette.ColorRole.ButtonText, QColor(COLOR_THEME["text"]["primary"])
    )
    light_palette.setColor(
        QPalette.ColorRole.Highlight, QColor(COLOR_THEME["list"]["selected"])
    )
    light_palette.setColor(
        QPalette.ColorRole.HighlightedText, QColor(COLOR_THEME["list"]["selected_text"])
    )
    light_palette.setColor(
        QPalette.ColorRole.PlaceholderText, QColor(COLOR_THEME["text"]["placeholder"])
    )

    # Apply the same colors for different states
    for color_group in [
        QPalette.ColorGroup.Active,
        QPalette.ColorGroup.Inactive,
        QPalette.ColorGroup.Disabled,
    ]:
        light_palette.setColor(
            color_group,
            QPalette.ColorRole.Window,
            QColor(COLOR_THEME["background"]["main"]),
        )
        light_palette.setColor(
            color_group,
            QPalette.ColorRole.WindowText,
            QColor(COLOR_THEME["text"]["primary"]),
        )
        light_palette.setColor(
            color_group,
            QPalette.ColorRole.Base,
            QColor(COLOR_THEME["input"]["background"]),
        )
        light_palette.setColor(
            color_group, QPalette.ColorRole.Text, QColor(COLOR_THEME["text"]["primary"])
        )
        light_palette.setColor(
            color_group,
            QPalette.ColorRole.Button,
            QColor(COLOR_THEME["button"]["normal"]),
        )
        light_palette.setColor(
            color_group,
            QPalette.ColorRole.ButtonText,
            QColor(COLOR_THEME["text"]["primary"]),
        )

    # Disabled state should be lighter
    light_palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(COLOR_THEME["text"]["secondary"]),
    )
    light_palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor(COLOR_THEME["text"]["secondary"]),
    )
    light_palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(COLOR_THEME["text"]["secondary"]),
    )

    app.setPalette(light_palette)


def get_stylesheet():
    """Generate comprehensive QSS stylesheet for the application"""
    return f"""
    /* Main application background */
    QWidget {{
        color: {COLOR_THEME["text"]["primary"]};
        background-color: {COLOR_THEME["background"]["main"]};
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 12px;
    }}
    
    /* Main window and panels */
    QMainWindow {{
        background-color: {COLOR_THEME["background"]["main"]};
    }}
    
    /* Frames and panels */
    QFrame {{
        background-color: {COLOR_THEME["frame"]["background"]};
        border: 1px solid {COLOR_THEME["frame"]["border"]};
        border-radius: 6px;
        padding: 6px;
    }}
    
    /* Labels */
    QLabel {{
        color: {COLOR_THEME["text"]["label"]};
        background-color: transparent;
        border: none;
        padding: 1px;
        font-size: 12px;
    }}
    
    /* Push buttons */
    QPushButton {{
        background-color: {COLOR_THEME["button"]["normal"]};
        border: 1px solid {COLOR_THEME["border"]["normal"]};
        border-radius: 4px;
        padding: 4px 8px;
        color: {COLOR_THEME["text"]["primary"]};
        font-weight: 500;
        font-size: 12px;
        min-height: 18px;
    }}
    
    QPushButton:hover {{
        background-color: {COLOR_THEME["button"]["hover"]};
        border-color: {COLOR_THEME["border"]["focus"]};
    }}
    
    QPushButton:pressed {{
        background-color: {COLOR_THEME["button"]["pressed"]};
        border-color: {COLOR_THEME["border"]["focus"]};
    }}
    
    QPushButton:disabled {{
        background-color: {COLOR_THEME["background"]["button"]};
        color: {COLOR_THEME["text"]["secondary"]};
        border-color: {COLOR_THEME["border"]["normal"]};
    }}
    
    /* Input fields */
    QLineEdit, QDoubleSpinBox {{
        background-color: {COLOR_THEME["input"]["background"]};
        border: 1px solid {COLOR_THEME["input"]["border"]};
        border-radius: 4px;
        padding: 3px 6px;
        color: {COLOR_THEME["input"]["text"]};
        font-size: 12px;
        selection-background-color: {COLOR_THEME["list"]["selected"]};
        selection-color: {COLOR_THEME["list"]["selected_text"]};
    }}
    
    QLineEdit:focus, QDoubleSpinBox:focus {{
        border-color: {COLOR_THEME["input"]["border_focus"]};
        outline: none;
    }}
    
    QLineEdit::placeholder {{
        color: {COLOR_THEME["input"]["placeholder"]};
    }}
    
    /* Spin box specific */
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        background-color: {COLOR_THEME["button"]["normal"]};
        border: 1px solid {COLOR_THEME["border"]["normal"]};
        border-radius: 2px;
        width: 16px;
    }}
    
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {COLOR_THEME["button"]["hover"]};
    }}
    
    /* List widgets */
    QListWidget {{
        background-color: {COLOR_THEME["list"]["background"]};
        border: 1px solid {COLOR_THEME["list"]["border"]};
        border-radius: 4px;
        color: {COLOR_THEME["text"]["primary"]};
        font-size: 12px;
        selection-background-color: {COLOR_THEME["list"]["selected"]};
        selection-color: {COLOR_THEME["list"]["selected_text"]};
        outline: none;
    }}
    
    QListWidget::item {{
        padding: 3px 6px;
        border-bottom: 1px solid {COLOR_THEME["background"]["alternate"]};
    }}
    
    QListWidget::item:selected {{
        background-color: {COLOR_THEME["list"]["selected"]};
        color: {COLOR_THEME["list"]["selected_text"]};
    }}
    
    QListWidget::item:hover {{
        background-color: {COLOR_THEME["list"]["hover"]};
    }}
    
    /* Scrollbars */
    QScrollBar:vertical {{
        background-color: {COLOR_THEME["scrollbar"]["background"]};
        width: 12px;
        border-radius: 6px;
        margin: 0;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {COLOR_THEME["scrollbar"]["handle"]};
        border-radius: 6px;
        min-height: 20px;
        margin: 2px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {COLOR_THEME["scrollbar"]["handle_hover"]};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar:horizontal {{
        background-color: {COLOR_THEME["scrollbar"]["background"]};
        height: 12px;
        border-radius: 6px;
        margin: 0;
    }}
    
    QScrollBar::handle:horizontal {{
        background-color: {COLOR_THEME["scrollbar"]["handle"]};
        border-radius: 6px;
        min-width: 20px;
        margin: 2px;
    }}
    
    QScrollBar::handle:horizontal:hover {{
        background-color: {COLOR_THEME["scrollbar"]["handle_hover"]};
    }}
    
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}
    
    /* Dialogs */
    QDialog {{
        background-color: {COLOR_THEME["dialog"]["background"]};
        border: 1px solid {COLOR_THEME["dialog"]["border"]};
        border-radius: 8px;
        font-size: 12px;
    }}
    
    QDialogButtonBox QPushButton {{
        min-width: 80px;
    }}
    
    /* Menu bars and menus */
    QMenuBar {{
        background-color: {COLOR_THEME["frame"]["background"]};
        border-bottom: 1px solid {COLOR_THEME["border"]["normal"]};
        padding: 1px;
        font-size: 12px;
    }}
    
    QMenuBar::item {{
        background-color: transparent;
        padding: 3px 6px;
        border-radius: 4px;
    }}
    
    QMenuBar::item:selected {{
        background-color: {COLOR_THEME["button"]["hover"]};
    }}
    
    QMenu {{
        background-color: {COLOR_THEME["frame"]["background"]};
        border: 1px solid {COLOR_THEME["border"]["normal"]};
        border-radius: 4px;
        padding: 3px;
        font-size: 12px;
    }}
    
    QMenu::item {{
        padding: 3px 12px;
        border-radius: 4px;
    }}
    
    QMenu::item:selected {{
        background-color: {COLOR_THEME["list"]["selected"]};
        color: {COLOR_THEME["list"]["selected_text"]};
    }}
    
    /* Tool tips */
    QToolTip {{
        background-color: {COLOR_THEME["dialog"]["background"]};
        color: {COLOR_THEME["text"]["primary"]};
        border: 1px solid {COLOR_THEME["border"]["normal"]};
        border-radius: 4px;
        padding: 3px 6px;
        font-size: 12px;
    }}
    """


def get_button_style(button_type="normal", state="normal"):
    """Return a stylesheet string for a button type/state."""
    base_style = f"""
        border: 1px solid {COLOR_THEME["border"]["normal"]};
        border-radius: 4px;
        padding: 4px 8px;
        font-weight: 500;
        font-size: 12px;
        min-height: 18px;
    """

    type_colors = {
        "normal": {
            "bg": COLOR_THEME["button"]["normal"],
            "bg_hover": COLOR_THEME["button"]["hover"],
            "bg_pressed": COLOR_THEME["button"]["pressed"],
            "text": COLOR_THEME["text"]["primary"],
        },
        "primary": {
            "bg": COLOR_THEME["button"]["primary"],
            "bg_hover": COLOR_THEME["button"]["primary_hover"],
            "bg_pressed": COLOR_THEME["button"]["primary_hover"],
            "text": COLOR_THEME["text"]["white"],
        },
        "secondary": {
            "bg": COLOR_THEME["button"]["secondary"],
            "bg_hover": COLOR_THEME["button"]["secondary_hover"],
            "bg_pressed": COLOR_THEME["button"]["secondary_hover"],
            "text": COLOR_THEME["text"]["white"],
        },
        "save": {
            "bg": COLOR_THEME["button"]["save"],
            "bg_hover": COLOR_THEME["button"]["save_hover"],
            "bg_pressed": COLOR_THEME["button"]["save_hover"],
            "text": COLOR_THEME["text"]["white"],
        },
        "danger": {
            "bg": COLOR_THEME["run_button"]["error"],
            "bg_hover": "#B02A37",
            "bg_pressed": "#B02A37",
            "text": COLOR_THEME["text"]["white"],
        },
    }

    colors = type_colors.get(button_type, type_colors["normal"])

    if state == "hover":
        return (
            base_style
            + f"""
            background-color: {colors["bg_hover"]};
            color: {colors["text"]};
            border-color: {COLOR_THEME["border"]["focus"]};
        """
        )
    elif state == "pressed":
        return (
            base_style
            + f"""
            background-color: {colors["bg_pressed"]};
            color: {colors["text"]};
            border-color: {COLOR_THEME["border"]["focus"]};
        """
        )
    elif state == "disabled":
        return (
            base_style
            + f"""
            background-color: {COLOR_THEME["background"]["button"]};
            color: {COLOR_THEME["text"]["secondary"]};
            border-color: {COLOR_THEME["border"]["normal"]};
        """
        )
    else:
        return (
            base_style
            + f"""
            background-color: {colors["bg"]};
            color: {colors["text"]};
        """
        )


class SignificantFiguresSpinBox(QDoubleSpinBox):
    """QDoubleSpinBox that displays values with significant figures."""

    def textFromValue(self, value):
        if value == 0:
            return "0"
        return f"{value:.4g}"


__all__ = [
    "COLOR_THEME",
    "apply_light_mode",
    "get_stylesheet",
    "get_button_style",
    "SignificantFiguresSpinBox",
]
