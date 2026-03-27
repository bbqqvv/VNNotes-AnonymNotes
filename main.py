import os
import sys

# os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] removed for stability

# 1. OPTIMIZED RENDERING (RE-ENABLING GPU FOR PERFORMANCE)
# MUST BE BEFORE ANY QT IMPORTS
# Relax software rendering to allow Hardware Acceleration
os.environ["QT_OPENGL"] = "desktop" 
os.environ["QTWEBENGINE_DISABLE_LOGGING"] = "1"

# Performance flags for Chromium: Hardware acceleration, rasterization, and threading
# Performance & Senior-level optimization flags for Chromium
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--ignore-gpu-blocklist "
    "--enable-gpu-rasterization "
    "--enable-zero-copy "
    "--num-raster-threads=4 "
    "--enable-native-gpu-memory-buffers "
    "--disable-features=UseSkiaRenderer " # Performance stability on Windows
    "--enable-accelerated-video-decode "
    "--disable-reading-from-canvas "      # Privacy + slight speed boost
    "--disk-cache-size=209715200 "        # 200MB Cache for speed
    "--process-per-site"                  # Memory saving for multiple tabs
)

# CRITICAL: Import WebEngine BEFORE QApplication to prevent context crashes
from PyQt6.QtWebEngineWidgets import QWebEngineView

# Cleanup: Delete debug.log if it exists (Chromium artifact)
try:
    if os.path.exists("debug.log"):
        os.remove("debug.log")
except:
    pass

# 3. Windows Icon Fix (AppUserModelID) - MUST BE AT TOP
# if sys.platform == 'win32':
#     import ctypes
#     MY_APP_ID = 'vtech.vnnotes.stable.v3'
#     ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(MY_APP_ID)

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import logging
from src.core.logger import setup_logging

def exception_hook(exctype, value, traceback_obj):
    import traceback
    traceback_str = "".join(traceback.format_exception(exctype, value, traceback_obj))
    with open("FATAL_CRASH.txt", "w", encoding="utf-8") as f:
        f.write(traceback_str)
    
    try:
        logging.critical(f"Uncaught Exception:\n{traceback_str}")
        if QApplication.instance():
            error_msg = f"An unexpected error occurred:\n{value}\n\nSee log file for details."
            QMessageBox.critical(None, "VNNotes Crashed", error_msg)
    except Exception:
        pass

def main():
    sys.excepthook = exception_hook
    log_file = setup_logging()
    
    # --- SENIOR DPI FIX REMOVED ---
    # software rendering works best with 'Round' or no specific policy in Qt6.
    # However, 'Round' completely broke text element bounding boxes at 125% scales
    # causing letters to overlap. We revert to default Qt6 behavior.
    
    # Added AA_ShareOpenGLContexts for WebEngine stability.
    # MUST BE DONE BEFORE CONSTRUCTING QApplication
    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    QApplication.setOrganizationName("vtechdigitalsolution")
    QApplication.setApplicationName("VNNotes")
    
    from src.core.single_app import SingleApplication
    app = SingleApplication(sys.argv)
    
    if app.is_running():
        logging.info("VNNotes is already running. Delegated launch parameters and exiting.")
        sys.exit(0)
    
    # Safe to import MainWindow now that QApplication has the correct context flags
    from src.ui.main_window import MainWindow
    
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
         
    # Check for Ghost-only icon first (for Taskbar)
    icon_path = os.path.join(base_path, "appnote.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_path, "logo.png")
        
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    # Ensure application quits completely when the main window is closed
    app.setQuitOnLastWindowClosed(True) 
    
    window = MainWindow()
    
    # Connecting IPC to MainWindow
    app.message_received.connect(window.handle_custom_uri)
    if len(sys.argv) > 1 and "vnnotes://" in sys.argv[1]:
        # Handle deep link from first launch
        window.handle_custom_uri(sys.argv[1])
        
    window.show()

    try:
        logging.info("Starting app.exec()")
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"Main Loop Crash: {e}", exc_info=True)

if __name__ == "__main__":
    main()