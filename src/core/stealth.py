import logging
import ctypes
from typing import Optional
from PyQt6.QtCore import QObject, QEvent, Qt
from PyQt6.QtWidgets import QWidget, QApplication

class StealthManager:
    """
    Manages the window display affinity to hide windows from screen capture.
    """
    
    # Constants from Windows API
    WDA_NONE = 0x00000000
    WDA_MONITOR = 0x00000001
    WDA_EXCLUDEFROMCAPTURE = 0x00000011
    
    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_LAYERED = 0x00080000

    @staticmethod
    def set_stealth_mode(hwnd: int, enable: bool = True) -> bool:
        """
        Enables or disables stealth mode for the given window handle (HWND).
        
        Args:
            hwnd (int): The window handle.
            enable (bool): True to enable stealth (exclude from capture), False to disable.
            
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        try:
            user32 = ctypes.windll.user32
            affinity = StealthManager.WDA_EXCLUDEFROMCAPTURE if enable else StealthManager.WDA_NONE
            
            result = user32.SetWindowDisplayAffinity(hwnd, affinity)
            
            if result:
                # logging.debug(f"StealthManager: Stealth mode {'enabled' if enable else 'disabled'} for HWND {hwnd}")
                return True
            else:
                error_code = ctypes.GetLastError()
                logging.error(f"StealthManager: Failed to set affinity. Error code: {error_code}")
                return False
                
        except Exception as e:
            logging.error(f"StealthManager Exception: {e}", exc_info=True)
            return False

    @staticmethod
    def apply_to_all_windows(app, enable: bool = True):
        """
        Applies stealth mode to all top-level widgets in the application.
        """
        for widget in app.topLevelWidgets():
            if widget.isWindow() and widget.winId():
                StealthManager.set_stealth_mode(int(widget.winId()), enable)

    @staticmethod
    def set_click_through(hwnd: int, enable: bool = True):
        """
        Enables click-through (transparent to mouse events) for the window.
        """
        try:
            user32 = ctypes.windll.user32
            # Get current extended style
            style = user32.GetWindowLongW(hwnd, StealthManager.GWL_EXSTYLE)
            
            if enable:
                new_style = style | StealthManager.WS_EX_TRANSPARENT | StealthManager.WS_EX_LAYERED
            else:
                new_style = style & ~StealthManager.WS_EX_TRANSPARENT
                
            user32.SetWindowLongW(hwnd, StealthManager.GWL_EXSTYLE, new_style)
            return True
        except Exception as e:
            logging.error(f"StealthManager Click-Through Exception: {e}", exc_info=True)
            return False

class StealthEventFilter(QObject):
    """
    Global event filter to apply stealth mode to new windows (tooltips, popups) as they appear.
    """
    def __init__(self, stealth_manager, enable: bool = False):
        super().__init__()
        self.stealth_manager = stealth_manager
        self.enabled = enable

    def set_enabled(self, enable: bool):
        self.enabled = enable
        # Re-apply to all existing windows when enabled
        if enable:
            app = QApplication.instance()
            if app:
                StealthManager.apply_to_all_windows(app, True)

    def eventFilter(self, obj, event):
        # Plan v4: Lifecycle & Re-entrancy Guards
        # 1. Broad guard for deleted/zombie objects
        try:
            if not self.enabled:
                return super().eventFilter(obj, event)

            if event.type() == QEvent.Type.Show:
                # 2. Check if object still exists and IS a window
                if isinstance(obj, QWidget) and obj.isWindow():
                    # 3. Check for valid winId (Qt may return 0/None for closing widgets)
                    hwnd = int(obj.winId())
                    if hwnd:
                        # 4. Apply stealth (StealthManager has its own internals/guards)
                        StealthManager.set_stealth_mode(hwnd, True)
        except (RuntimeError, AttributeError, ValueError):
            # Object deleted mid-filter or invalid winId
            pass
        except Exception as e:
            # Prevent exception noise during shutdown
            if "KeyboardInterrupt" not in str(e):
                logging.debug(f"Stealth Filter Info: {e}")
            
        return super().eventFilter(obj, event)
