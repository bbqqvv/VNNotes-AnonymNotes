import os
import sys
import logging
import time

# Mock environment
os.environ["QT_OPENGL"] = "software"

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
logger = logging.getLogger("Diagnostic")

def run_test():
    logger.info("Starting Aggressive Diagnostic Test (V3)...")
    
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    app = QApplication(sys.argv)
    logger.info("QApplication created.")
    
    from src.ui.main_window import MainWindow
    logger.info("MainWindow class imported.")
    
    try:
        logger.info("Initializing MainWindow...")
        window = MainWindow()
        logger.info("MainWindow initialized.")
        
        # Manually trigger opening 5 notes to force TabBars to exist
        logger.info("Opening 5 sample notes...")
        for i in range(5):
            window.add_note_dock(title=f"Sample Note {i}", content=f"Content {i}")
        
        logger.info("Notes opened.")
        
        logger.info("Showing MainWindow...")
        window.show()
        logger.info("MainWindow shown.")
        
        logger.info("Waiting for TabHook and layout (10 seconds)...")
        # Ensure we wait longer than the 1.5s timer in TabManager
        
        # Use a timer to exit after some time
        QTimer.singleShot(10000, lambda: app.quit())
        
        logger.info("Starting event loop...")
        app.exec()
        logger.info("Event loop finished normally.")
        
    except Exception as e:
        logger.error(f"DIAGNOSTIC CRASH: {e}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    success = run_test()
    if success:
        logger.info("Aggressive Diagnostic test COMPLETED SUCCESSFULLY.")
        sys.exit(0)
    else:
        logger.error("Aggressive Diagnostic test FAILED.")
        sys.exit(1)
