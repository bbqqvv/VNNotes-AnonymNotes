import os
import sys
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize

def get_project_root():
    """Returns the absolute path to the project root directory."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_icon_dir(is_dark=True):
    """Returns the path to the appropriate icon directory based on theme."""
    folder = "dark_theme" if is_dark else "light_theme"
    return os.path.join(get_project_root(), "assets", "icons", folder)

def get_icon(name, is_dark=True):
    """Returns a QIcon object for the given icon name and theme."""
    path = os.path.join(get_icon_dir(is_dark), name)
    if not os.path.exists(path):
        # Fallback to general assets if not in theme folder (optional)
        path = os.path.join(get_project_root(), "assets", name)
    
    return QIcon(path)

def setup_themed_button(button, icon_name, is_dark=True, icon_size=16):
    """Configures a QPushButton with the correct themed icon."""
    icon = get_icon(icon_name, is_dark)
    button.setIcon(icon)
    button.setIconSize(QSize(icon_size, icon_size))
