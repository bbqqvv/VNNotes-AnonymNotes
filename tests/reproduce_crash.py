import os
import sys
import logging
import time

# Mock environment - TRY TO REMOVE SOFTWARE RENDERING TO SEE IF IT CRASHES
# os.environ["QT_OPENGL"] = "software" 

# Add project root
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# CRITICAL: Import WebEngine BEFORE QApplication
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    print("QtWebEngineWidgets not found, skipping web tests.")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

# Setup minimal logging to console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger("Reproduction")

def run_test():
    logger.info("Starting Reproduction Test (Crash Attempt)...")
    
    # Enable the attribute that we suspect is causing the crash
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    
    # DO NOT set AA_ShareOpenGLContexts as it might be the "fix"
    
    app = QApplication(sys.argv)
    logger.info("QApplication created.")
    
    from src.ui.main_window import MainWindow
    logger.info("MainWindow class imported.")
    
    try:
        logger.info("Initializing MainWindow...")
        window = MainWindow()
        logger.info("MainWindow initialized.")
        
        logger.info("Opening 10 sample notes to stress layout...")
        for i in range(10):
            window.add_note_dock(title=f"Sample Note {i}")
        
        logger.info("Showing MainWindow...")
        window.show()
        logger.info("MainWindow shown.")
        
        QTimer.singleShot(6000, lambda: app.quit())
        
        logger.info("Starting event loop...")
        app.exec()
        logger.info("Event loop finished normally.")
        
    except Exception as e:
        logger.error(f"REPRODUCTION CRASH: {e}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    success = run_test()
    if success:
        logger.info("Reproduction test COMPLETED WITHOUT CRASH.")
        sys.exit(0)
    else:
        logger.error("Reproduction test TRIGGERED CRASH.")
        sys.exit(1)
