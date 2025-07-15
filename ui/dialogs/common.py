"""
Common dialog utilities and base classes
"""

from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import Qt
from config.settings import DARK_THEME_STYLE


class BaseDialog(QDialog):
    """Base dialog class with common styling and functionality"""
    
    def __init__(self, parent=None, title="Dialog", min_width=400, min_height=300):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(min_width, min_height)
        self.setStyleSheet(DARK_THEME_STYLE)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)


def show_info_dialog(parent, title: str, message: str):
    """Show standardized info dialog"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setStyleSheet(DARK_THEME_STYLE)
    return msg_box.exec()


def show_error_dialog(parent, title: str, message: str):
    """Show standardized error dialog"""
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setStyleSheet(DARK_THEME_STYLE)
    return msg_box.exec()