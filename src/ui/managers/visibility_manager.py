import logging
import threading
import time

from PyQt6.QtWidgets import QDockWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QMetaObject, pyqtSlot

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
        from src.features.browser.browser_pane import BrowserPane

        if self.mw.isVisible():
            # Capture state BEFORE hiding
            all_docks = self.mw.findChildren(QDockWidget)
            all_browsers = self.mw.findChildren(BrowserPane)

            self.mw.hide()
            for dock in all_docks:
                if dock.isFloating() and dock.isVisible():
                    dock.hide()
                    dock.setProperty("was_floating_visible", True)
            # Mark browsers that were visible so we can restore them
            for browser in all_browsers:
                if browser.isVisible():
                    browser.setProperty("was_visible", True)
                    browser.hide()
        else:
            self.mw.show()
            self.mw.activateWindow()
            self.mw.raise_()

            def restore_docks():
                all_docks = self.mw.findChildren(QDockWidget)
                all_browsers = self.mw.findChildren(BrowserPane)
                for dock in all_docks:
                    try:
                        if dock.property("was_floating_visible") or \
                           (not dock.isFloating() and not dock.isVisible()):
                            dock.show()
                            dock.setProperty("was_floating_visible", False)
                    except RuntimeError:
                        continue
                # Restore browsers that were visible before hiding
                for browser in all_browsers:
                    try:
                        if browser.property("was_visible"):
                            browser.show()
                            browser.setProperty("was_visible", False)
                    except RuntimeError:
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
            self.mw.teleprompter.btn_click_through.click()
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
