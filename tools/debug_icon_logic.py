
import os
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QIcon

class MockWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_theme = "light" # Force Light Mode
        self.check_icon("note.svg")
        
        self.current_theme = "dark" # Force Dark Mode
        self.check_icon("note.svg")

    def check_icon(self, filename):
        print(f"\n--- Testing Theme: {getattr(self, 'current_theme', 'dark')} ---")
        icon = self._icon(filename)
        print(f"Result Icon Null? {icon.isNull()}")

    def _icon(self, filename):
        base_path = os.getcwd()
        
        # LOGIC FROM main_window.py
        folder = "dark_theme" # Default
        if getattr(self, "current_theme", "dark") == "light":
            folder = "light_theme"
            
        path = os.path.join(base_path, "assets", "icons", folder, filename)
        
        print(f"Request: {filename}")
        print(f"Theme Attribute: {getattr(self, 'current_theme', 'dark')}")
        print(f"Selected Folder: {folder}")
        print(f"Constructed Path: {path}")
        print(f"File Exists: {os.path.exists(path)}")
        
        if os.path.exists(path):
            return QIcon(path)
        return QIcon()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MockWindow()
