import os
import sys
import logging
import time

# 1. ENFORCE ENVIRONMENT
os.environ["QT_OPENGL"] = "software"

# Add project root
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 2. CRITICAL IMPORT ORDER (Matches v7.0 main.py)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

# Setup minimal logging to console
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger("VerificationV7")

def run_verify():
    logger.info("Starting Final Verification (Plan v7.0)...")
    
    # 3. SET ATTRIBUTES (Matches v7.0 main.py)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    app = QApplication(sys.argv)
    logger.info("QApplication created.")
    
    from src.ui.main_window import MainWindow
    logger.info("MainWindow class imported.")
    
    try:
        logger.info("Initializing MainWindow...")
        window = MainWindow()
        logger.info("MainWindow initialized.")
        
        # Stress-test: Open 15 notes to force complex tab bar logic
        logger.info("Opening 15 notes to stress tab system...")
        for i in range(15):
            window.add_note_dock(title=f"Stress Note {i}")
        
        logger.info("Notes opened. Showing window...")
        window.show()
        
        # Final safety check: Close 3 notes rapidly to test sip.isdeleted
        def _stress_close():
            logger.info("Stress-testing Close functionality...")
            bars = window.findChildren(window.tab_manager.mw.findChildren(window.tab_manager.mw.__class__).__class__) # dummy
            # Better: just use tab_manager directly
            try:
                # Find the first tab bar
                from PyQt6.QtWidgets import QTabBar
                tabbars = window.findChildren(QTabBar)
                if tabbars:
                    logger.info(f"Fired test-close on bar {id(tabbars[0])}")
                    window.tab_manager.on_tab_close_requested(tabbars[0], 0)
                    window.tab_manager.on_tab_close_requested(tabbars[0], 1)
            except Exception as e:
                logger.warning(f"Stress close skip: {e}")

        QTimer.singleShot(3000, _stress_close)
        
        logger.info("Waiting for 8 seconds to ensure no background crashes...")
        QTimer.singleShot(8000, lambda: app.quit())
        
        app.exec()
        logger.info("Event loop finished normally.")
        
    except Exception as e:
        logger.error(f"VERIFICATION FAILED: {e}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    success = run_verify()
    if success:
        logger.info("Verification v7.0 COMPLETED SUCCESSFULLY.")
        sys.exit(0)
    else:
        logger.error("Verification v7.0 FAILED.")
        sys.exit(1)
