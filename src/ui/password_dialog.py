import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QDialogButtonBox)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
from src.utils.ui_utils import get_icon

class PasswordDialog(QDialog):
    """
    A custom password input dialog with a 'Show Password' toggle button.
    """
    def __init__(self, title="Security", message="Enter password:", is_dark=True, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(300)
        self._is_dark = is_dark
        
        layout = QVBoxLayout(self)
        
        if message:
            layout.addWidget(QLabel(message))
            
        # Password Input Row
        input_layout = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        input_layout.addWidget(self.password_input)
        
        self.toggle_btn = QPushButton()
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setFixedWidth(30)
        self.toggle_btn.setFlat(True)
        self._update_toggle_icon()
        self.toggle_btn.clicked.connect(self._toggle_visibility)
        input_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(input_layout)
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
    def _update_toggle_icon(self):
        # Use unlock for visible, lock for hidden
        icon_name = "unlock.svg" if not self.password_input.echoMode() == QLineEdit.EchoMode.Password else "lock.svg"
        self.toggle_btn.setIcon(get_icon(icon_name, self._is_dark))
        
    def _toggle_visibility(self):
        if self.password_input.echoMode() == QLineEdit.EchoMode.Password:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._update_toggle_icon()
        
    def get_password(self):
        return self.password_input.text()

    @staticmethod
    def get_input(parent, title="Security", message="Enter password:", is_dark=True):
        dialog = PasswordDialog(title, message, is_dark, parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_password(), True
        return "", False
