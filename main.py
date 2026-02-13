import sys
import os

# Add project root to path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from PyQt6.QtWidgets import QApplication, QMessageBox
import logging
from src.ui.main_window import MainWindow
from src.core.logger import setup_logging

# --- Global Exception Handler ---
def exception_hook(exctype, value, traceback_obj):
    """
    Global function to catch unhandled exceptions.
    Logs the error and displays a user-friendly message.
    """
    import traceback
    
    # Format the traceback
    traceback_str = "".join(traceback.format_exception(exctype, value, traceback_obj))
    
    # Log the error
    logging.critical(f"Uncaught Exception:\n{traceback_str}")
    print(f"CRASH: {value}") # Keep simple print for immediate dev feedback
    
    # Show Error Dialog (if QApplication is running)
    if QApplication.instance():
        error_msg = f"An unexpected error occurred:\n{value}\n\nSee log file for details."
        QMessageBox.critical(None, "Stealth Assist Crashed", error_msg)


def main():
    # 1. Setup Logging
    log_file = setup_logging()
    
    # Enable WebEngine OpenGL sharing (Critical for performance/stability)
    from PyQt6.QtCore import Qt
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    # 2. Setup Exception Hook

    sys.excepthook = exception_hook
    
    # 3. Windows Icon Fix (AppUserModelID)
    if sys.platform == 'win32':
        import ctypes
        myappid = 'stealthassist.v2.enterprise' # Arbitrary ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Stealth Assist")
    
    # Set App Icon (Global)
    # The 'os' module is already imported at the top of the file, so no need to re-import here.
    if getattr(sys, 'frozen', False):
         base_path = sys._MEIPASS
    else:
         base_path = os.path.dirname(os.path.abspath(__file__))
         
    icon_path = os.path.join(base_path, "logo.png")
    if not os.path.exists(icon_path):
        icon_path = os.path.join(base_path, "appnote.png")
        
    if os.path.exists(icon_path):
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))
        
    app.setQuitOnLastWindowClosed(True) # Exit when window closes
    
    # Initialize
    window = MainWindow()
    window.show()

    try:
        sys.exit(app.exec())
    except Exception as e:
        logging.critical(f"Main Loop Crash: {e}", exc_info=True)

if __name__ == "__main__":
    main()
