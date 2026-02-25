import logging
import threading
import time

from PyQt6.QtWidgets import QDockWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QMetaObject, pyqtSlot
from PyQt6 import sip

from src.core.stealth import StealthManager

logger = logging.getLogger(__name__)


class VisibilityManager:
    """
    Manages stealth mode, ghost click-through, always-on-top,
    window opacity, and hide/show (toggle visibility) logic.
    """

    def __init__(self, main_window):
        self.mw = main_window
        self._last_hotkey_time = 0

    def setup_stealth(self):
        """Initialize the stealth system: event filter + global hotkeys."""
        from src.core.stealth import StealthEventFilter
        self.mw.stealth_filter = StealthEventFilter(StealthManager, False)
        QApplication.instance().installEventFilter(self.mw.stealth_filter)

        import keyboard

        def safe_toggle():
            current = time.time()
            if current - self._last_hotkey_time > 0.5:
                self._last_hotkey_time = current
                QMetaObject.invokeMethod(
                    self.mw, "toggle_visibility",
                    Qt.ConnectionType.QueuedConnection)

        def check_hotkey():
            keyboard.add_hotkey('ctrl+shift+space', safe_toggle)
            keyboard.add_hotkey(
                'ctrl+shift+f9',
                lambda: QMetaObject.invokeMethod(
                    self.mw, "toggle_ghost_click_external",
                    Qt.ConnectionType.QueuedConnection))
            keyboard.wait()

        threading.Thread(target=check_hotkey, daemon=True).start()

        # Apply initial stealth state after window is shown
        def initial_stealth():
            stealth_act = self.mw.menu_manager.actions.get("stealth")
            if stealth_act:
                self.toggle_stealth(stealth_act.isChecked())

        QTimer.singleShot(1000, initial_stealth)

    def toggle_visibility(self):
        """Hide or show the entire application (including floating docks)."""
        if self.mw.isVisible():
            # Capture state BEFORE hiding
            all_docks = self.mw.findChildren(QDockWidget)
            self.mw.hide()
            for dock in all_docks:
                try:
                    if sip.isdeleted(dock): continue
                    # Mark ONLY docks that are actually visible right now
                    if dock.isVisible():
                        dock.setProperty("was_visible_before_hide", True)
                        # Floating docks must be hidden manually since they are top-level windows
                        if dock.isFloating():
                            dock.hide()
                    else:
                        dock.setProperty("was_visible_before_hide", False)
                except RuntimeError: continue
        else:
            self.mw.show()
            self.mw.activateWindow()
            self.mw.raise_()

            def restore_docks():
                all_docks = self.mw.findChildren(QDockWidget)
                for dock in all_docks:
                    try:
                        # Restore ONLY what was visible before
                        if dock.property("was_visible_before_hide"):
                            dock.show()
                            dock.setProperty("was_visible_before_hide", False)
                    except (RuntimeError, AttributeError):
                        continue
                self.mw.menuBar().raise_()
                self.mw.update()

            QTimer.singleShot(100, restore_docks)

    def toggle_stealth(self, checked):
        if hasattr(self.mw, 'stealth_filter'):
            self.mw.stealth_filter.set_enabled(checked)
        StealthManager.set_stealth_mode(int(self.mw.winId()), checked)
        StealthManager.apply_to_all_windows(QApplication.instance(), checked)
        self.mw.statusBar().showMessage(
            "Stealth " + ("Enabled" if checked else "Disabled"), 2000)

    def toggle_ghost_click_external(self):
        """Priority: toggle Teleprompter's ghost click if open, else main window."""
        if hasattr(self.mw, 'teleprompter') and self.mw.teleprompter and \
           self.mw.teleprompter.isVisible():
            self.mw.teleprompter.btn_lock.click()
            return
        ghost_click_act = self.mw.menu_manager.actions.get("ghost_click")
        if ghost_click_act:
            new_state = not ghost_click_act.isChecked()
            ghost_click_act.setChecked(new_state)
            self.toggle_ghost_click(new_state)

    def toggle_ghost_click(self, checked):
        if StealthManager.set_click_through(int(self.mw.winId()), checked):
            self.mw.statusBar().showMessage(
                "Ghost Click " + ("Enabled" if checked else "Disabled"), 2000)
        else:
            ghost_click_act = self.mw.menu_manager.actions.get("ghost_click")
            if ghost_click_act:
                ghost_click_act.setChecked(not checked)

    def toggle_always_on_top(self):
        on_top_act = self.mw.menu_manager.actions.get("always_on_top")
        on_top = on_top_act.isChecked() if on_top_act else False
        flags = self.mw.windowFlags()
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.mw.setWindowFlags(flags)
        self.mw.show()

    def change_window_opacity(self, value):
        self.mw.setWindowOpacity(value / 100.0)

    def adjust_window_opacity(self, delta):
        """Relative adjustment (v7.1): Increments/Decrements by delta percentage."""
        current = int(self.mw.windowOpacity() * 100)
        new_val = current + delta
        # Clamp between 10% and 100%
        if new_val > 100: new_val = 100
        if new_val < 10: new_val = 10
        self.change_window_opacity(new_val)
        
        # Plan v7.2: Sync the UI Slider
        if hasattr(self.mw, 'menu_manager') and self.mw.menu_manager.opacity_slider:
            # Block signals to prevent recursion since change_window_opacity already called
            self.mw.menu_manager.opacity_slider.blockSignals(True)
            self.mw.menu_manager.opacity_slider.setValue(new_val)
            self.mw.menu_manager.opacity_slider.blockSignals(False)
            if self.mw.menu_manager.opacity_label:
                self.mw.menu_manager.opacity_label.setText(f"{new_val}%")

        self.mw.statusBar().showMessage(f"Opacity: {new_val}%", 1500)
