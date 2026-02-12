import ctypes
from typing import Optional

class StealthManager:
    """
    Manages the window display affinity to hide windows from screen capture.
    """
    
    # Constants from Windows API
    WDA_NONE = 0x00000000
    WDA_MONITOR = 0x00000001
    WDA_EXCLUDEFROMCAPTURE = 0x00000011
    
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
                # print(f"StealthManager: Stealth mode {'enabled' if enable else 'disabled'} for HWND {hwnd}")
                return True
            else:
                error_code = ctypes.GetLastError()
                print(f"StealthManager Error: Failed to set affinity. Error code: {error_code}")
                return False
                
        except Exception as e:
            print(f"StealthManager Exception: {e}")
            return False
