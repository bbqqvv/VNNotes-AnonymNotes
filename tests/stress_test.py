import sys
import os
import logging
import random
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, Qt, QCoreApplication

# Ensure we have the project root in path
sys.path.append(os.getcwd())

# MUST set before QApplication instance (Plan v7.8 Sync)
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

# Force software rendering for headless/remote environment stability
os.environ["QT_OPENGL"] = "software"

from src.ui.main_window import MainWindow
from src.core.context import ServiceContext

def stress_test():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    ctx = ServiceContext.get_instance()
    
    print("Starting Stress Test...")
    
    iterations = 20
    
    def run_step(i):
        if i >= iterations:
            print("Stress Test Completed Successfully!")
            app.quit()
            return

        try:
            print(f"[{time.time():.2f}] Step {i+1}/{iterations}: Operating...")
            
            # 1. Add/Remove notes
            print(f"[{time.time():.2f}] Adding note...")
            note = window.add_note_dock(title=f"Stress Note {i}", content=f"Content for {i}")
            
            # 2. Toggle Sidebar
            print(f"[{time.time():.2f}] Toggling sidebar...")
            window.toggle_sidebar()
            
            # 3. Random Theme Switch
            print(f"[{time.time():.2f}] Switching theme...")
            theme = "dark" if i % 2 == 0 else "light"
            window.theme_manager.apply_theme() # Simplified call
            
            # 4. Close the dock immediately
            if note:
                print(f"[{time.time():.2f}] Closing note...")
                note.close()
                
            # 5. Simulate branding update
            print(f"[{time.time():.2f}] Updating branding...")
            window.update_branding_visibility(immediate=True)
            
            # 6. Trigger autosave if manager exists
            if hasattr(window, 'session_manager'):
                print(f"[{time.time():.2f}] Triggering autosave...")
                window.session_manager.auto_save()
            
            # Schedule next step
            QTimer.singleShot(200, lambda: run_step(i + 1))
            
        except Exception as e:
            print(f"CRASH DETECTED at step {i}: {e}")
            import traceback
            traceback.print_exc()
            app.quit()

    # Wait for settlement before starting
    QTimer.singleShot(2000, lambda: run_step(0))
    
    # Global timeout to prevent hanging
    QTimer.singleShot(30000, app.quit)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    stress_test()
