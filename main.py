import os
import sys

# 1. FORCE SOFTWARE RENDERING (DIAMOND-STANDARD FIX FOR WHITE SCREEN)
# MUST BE BEFORE ANY QT IMPORTS
os.environ["QT_OPENGL"] = "software"
os.environ["QTWEBENGINE_DISABLE_LOGGING"] = "1"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--disable-logging --log-level=3 --log-file=NUL "
    "--disable-gpu --disable-gpu-compositing "
    "--num-raster-threads=2 --enable-begin-frame-scheduling"
)

# Cleanup: Delete debug.log if it exists (Chromium artifact)
try:
    if os.path.exists("debug.log"):
        os.remove("debug.log")
except:
    pass

# 3. Windows Icon Fix (AppUserModelID) - MUST BE AT TOP
if sys.platform == 'win32':
    import ctypes
    MY_APP_ID = 'vtech.vnnotes.stable.v2'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(MY_APP_ID)

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import logging
from src.ui.main_window import MainWindow
from src.core.logger import setup_logging

def exception_hook(exctype, value, traceback_obj):
    import traceback
    traceback_str = "".join(traceback.format_exception(exctype, value, traceback_obj))
    logging.critical(f"Uncaught Exception:\n{traceback_str}")
    if QApplication.instance():
        error_msg = f"An unexpected error occurred:\n{value}\n\nSee log file for details."
        QMessageBox.critical(None, "VNNotes Crashed", error_msg)

def main():
    sys.excepthook = exception_hook
    log_file = setup_logging()
    
    # --- SENIOR DPI FIX ---
    # software rendering works best with 'Round' or no specific policy in Qt6.
    # 'PassThrough' often creates fractional raster errors that lead to white screens.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.Round
    )
    
    # Ensure DWM (Windows Taskbar) can correctly see the window buffers
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    
    QApplication.setOrganizationName("vtechdigitalsolution")
    QApplication.setApplicationName("VNNotes")
    
    app = QApplication(sys.argv)
    
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
         
    icon_path = os.path.join(base_path, "logo.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_path, "appnote.png")
        
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    app.setQuitOnLastWindowClosed(True) 
    
    window = MainWindow()
    window.show()

    try:
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"Main Loop Crash: {e}", exc_info=True)

if __name__ == "__main__":
    main()


