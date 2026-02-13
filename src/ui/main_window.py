import json
import os
import sys
import threading
import logging

from PyQt6.QtWidgets import (QMainWindow, QWidget, QDockWidget, QToolBar, 
                             QMessageBox, QLabel, QSizePolicy, QSlider,
                             QSystemTrayIcon, QMenu, QApplication, QFileDialog)
from PyQt6.QtGui import QAction, QFont, QIcon, QDesktopServices, QTextCursor
from PyQt6.QtCore import Qt, QUrl, QSize, QTimer, pyqtSlot, QMetaObject, Q_ARG, QByteArray
from PyQt6 import QtCore

from src.core.stealth import StealthManager
from src.core.config import ConfigManager
from src.core.storage import StorageManager
from src.core.reader import UniversalReader
from src.core.version import check_for_updates, CURRENT_VERSION
from src.features.notes.note_pane import NotePane
from src.features.browser.browser_pane import BrowserPane
from src.features.teleprompter.teleprompter_dialog import TeleprompterDialog
from src.features.clipboard.clipboard_manager import ClipboardManager
from src.ui.branding import BrandingOverlay
from src.ui.managers.dock_manager import DockManager
from src.ui.managers.menu_toolbar_manager import MenuToolbarManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.setWindowTitle("VNNotes")
        
        # Paths
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        icon_path = os.path.join(self.base_path, "logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # State
        self.dock_widgets = []
        self.active_pane = None
        self.current_theme = "dark"
        
        # Managers
        self.dock_manager = DockManager(self)
        self.menu_manager = MenuToolbarManager(self)
        self.clipboard_manager = ClipboardManager()
        
        # Setup UI
        self.setup_window()
        self.setup_ui()
        self.setup_stealth()
        self.setup_tray()
        
        # Final Setup
        self.setup_status_bar_widgets()
        # self.restore_app_state() - Removed duplicate call
        
        # Dynamically hook into tab bars for double-click renaming

        self.tab_hook_timer = QTimer(self)
        self.tab_hook_timer.timeout.connect(self.hook_tab_bars)
        self.tab_hook_timer.start(1000) # Check every second
        
        # Periodic status bar updates
        self.status_update_timer = QTimer(self)
        self.status_update_timer.timeout.connect(self.update_status_bar_info)
        self.status_update_timer.start(200) # Fast updates for char count/pos

        
        # Restore State
        QTimer.singleShot(100, self.restore_app_state)
        
        # --- Auto-Save Timer ---
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(60000) # 60 seconds
        self.autosave_timer.timeout.connect(self.auto_save)
        
        # Load preference
        autosave_enabled = self.config.get_value("app/autosave_enabled", True)
        if isinstance(autosave_enabled, str):
            autosave_enabled = autosave_enabled.lower() == 'true'
            
        autosave_act = self.menu_manager.actions.get("autosave")
        if autosave_act:
            autosave_act.setChecked(autosave_enabled)
            
        if autosave_enabled:
            self.autosave_timer.start()

        # Check for updates
        # QTimer.singleShot(3000, lambda: self.check_for_updates(manual=False))

    def auto_save(self):
        """Background auto-save"""
        self.save_app_state()
        # Optional: Show subtle indicator? 
        # self.statusBar().showMessage("Auto-saved", 1000)

    def setup_window(self):
        self.resize(1280, 800)
        geo = self.config.get_value("window/geometry")
        if geo:
            try:
                self.restoreGeometry(bytes.fromhex(geo))
            except Exception:
                pass
        else:
            self.setWindowState(Qt.WindowState.WindowMaximized)
            
        self.setDockNestingEnabled(True)
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | 
                            QMainWindow.DockOption.AllowNestedDocks | 
                            QMainWindow.DockOption.AnimatedDocks | 
                            QMainWindow.DockOption.GroupedDragging)

        
        self.setCorner(Qt.Corner.TopLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.TopRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)


    def setup_ui(self):
        # 1. Branding Overlay (Permanent Central Widget)
        self.branding = BrandingOverlay(self)
        self.setCentralWidget(self.branding)
        
        # 2. Toolbar & Actions (Delegated to specialized methods for clarity)
        self.setup_actions()
        self.setup_toolbar()
        self.setup_menu()
        
        # 3. Apply Theme
        self.apply_theme("dark")

    def setup_actions(self):
        self.menu_manager.setup_actions()

    def setup_toolbar(self):
        self.menu_manager.setup_toolbar()

    def setup_menu(self):
        self.menu_manager.setup_menu()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        
        tray_menu = QMenu()
        show_act = QAction("Show/Hide", self)
        show_act.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(show_act)
        
        tray_menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_act)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()


    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_visibility()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
            self.raise_()

    def quit_app(self):
        self.save_app_state()
        QApplication.quit()

    def apply_theme(self, mode):
        self.current_theme = mode
        if hasattr(self, 'branding'):
            self.branding.update()
            
        # Get path for close icon to use in CSS
        folder = "dark_theme" if mode == "dark" else "light_theme"
        close_icon_url = os.path.join(self.base_path, "assets", "icons", folder, "close.svg").replace("\\", "/")

        
        if mode == "dark":
            style = f"""
                QMainWindow, QDockWidget {{ background: #2b2b2b; color: #eeeeee; }}
                QTextEdit, NotePane {{ background: #333333; color: #eeeeee; border: none; font-family: 'Segoe UI', sans-serif; font-size: 13px; padding: 6px; }}
                QToolBar {{ background: #1e1e1e; border-bottom: 1px solid #333; spacing: 4px; padding: 2px; min-height: 26px; }}
                QToolButton {{ background: transparent; border-radius: 4px; padding: 2px; color: #eeeeee; }}
                QToolButton:hover {{ background: #3a3a3a; }}
                QMenuBar {{ background: #1e1e1e; color: #eeeeee; border-bottom: 1px solid #333; padding: 2px; }}
                QMenuBar::item {{ padding: 4px 8px; }}
                QMenuBar::item:selected {{ background: #3a3a3a; }}
                QMenu {{ background: #2b2b2b; color: #eeeeee; padding: 4px; border: 1px solid #444; }}
                QMenu::item:selected {{ background: #3c3c3c; }}
                QStatusBar {{ background: #2b2b2b; color: #eeeeee; border-top: 1px solid #444; min-height: 18px; }}
                QStatusBar QLabel {{ color: #eeeeee; font-size: 11px; padding: 0px 4px; }}
                
                QTabBar {{
                    background: #1e1e1e;
                    border-bottom: 1px solid #333;
                }}
                QTabBar::tab {{
                    background: #252525;
                    color: #888888;
                    padding: 2px 16px 2px 8px; /* Hyper-compact */
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    margin-right: 1px;
                    min-width: 50px;
                    font-size: 11px;
                    border: 1px solid transparent;
                }}
                QTabBar::tab:selected {{
                    background: #333333;
                    color: #eeeeee;
                    border-bottom: 2px solid #3498db;
                }}
                QTabBar::tab:hover {{
                    background: #2a2a2a;
                    color: #cccccc;
                }}
                
                QTabBar::close-button {{
                    image: url("{close_icon_url}");
                    subcontrol-position: right;
                    margin-right: 2px;
                    width: 12px;
                    height: 12px;
                    border-radius: 6px;
                    background: transparent;
                }}
                QTabBar::close-button:hover {{
                    background-color: #ff5f56;
                }}
            """
        else:
            style = f"""
                QMainWindow, QDockWidget {{ background: #ffffff; color: #333333; }}
                QTextEdit, NotePane {{ background: #ffffff; color: #333333; border: none; font-family: 'Segoe UI', sans-serif; font-size: 13px; padding: 6px; }}
                QToolBar {{ background: #f3f4f6; border-bottom: 1px solid #e5e7eb; spacing: 4px; padding: 2px; min-height: 26px; }}
                QToolButton {{ background: transparent; border-radius: 4px; padding: 2px; color: #333333; }}
                QToolButton:hover {{ background: #e5e7eb; }}
                QMenuBar {{ background: #f3f4f6; color: #333333; border-bottom: 1px solid #e5e7eb; padding: 2px; }}
                QMenuBar::item {{ padding: 4px 8px; }}
                QMenuBar::item:selected {{ background: #e5e7eb; }}
                QMenu {{ background: #ffffff; color: #333333; padding: 4px; border: 1px solid #e5e7eb; }}
                QMenu::item:selected {{ background: #f3f4f6; }}
                QStatusBar {{ background: #ffffff; color: #333333; border-top: 1px solid #e5e7eb; min-height: 18px; }}
                QStatusBar QLabel {{ color: #333333; font-size: 11px; padding: 0px 4px; }}
                
                QTabBar {{
                    background: #f3f4f6;
                    border-bottom: 1px solid #e5e7eb;
                }}
                QTabBar::tab {{
                    background: #e5e7eb;
                    color: #666666;
                    padding: 2px 16px 2px 8px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    margin-right: 1px;
                    min-width: 50px;
                    font-size: 11px;
                    border: 1px solid transparent;
                }}
                QTabBar::tab:selected {{
                    background: #ffffff;
                    color: #333333;
                    border-bottom: 2px solid #3498db;
                }}
                QTabBar::tab:hover {{
                    background: #ececec;
                    color: #333333;
                }}
                
                QTabBar::close-button {{
                    image: url("{close_icon_url}");
                    subcontrol-position: right;
                    margin-right: 2px;
                    width: 12px;
                    height: 12px;
                    border-radius: 6px;
                    background: transparent;
                }}
                QTabBar::close-button:hover {{
                    background-color: #ff5f56;
                }}
            """
        self.setStyleSheet(style)
        self.update_icons()



    def update_icons(self):
        self.menu_manager.update_icons()
        
        if hasattr(self, 'label_ghost'):
            self.label_ghost.setPixmap(self._get_icon("ghost.svg").pixmap(16, 16))

    def _get_icon(self, filename):
        folder = "dark_theme" if self.current_theme == "dark" else "light_theme"
        path = os.path.join(self.base_path, "assets", "icons", folder, filename)
        return QIcon(path) if os.path.exists(path) else QIcon()

    def update_branding_visibility(self):
        """Show branding only when no docks are visible."""
        # Clean list and check for visible docks
        visible_docks = []
        valid_docks = []
        
        for dock in self.dock_widgets:
            try:
                # Only count if it's not floating and is visible
                if dock.isVisible() and not dock.isFloating():
                    visible_docks.append(dock)
                elif dock.isFloating() and dock.isVisible():
                    # Floating docks shouldn't necessarily hide the branding? 
                    # Actually they should probably count as "using the app".
                    visible_docks.append(dock)
                    
                valid_docks.append(dock)
            except RuntimeError:
                # C++ object deleted
                pass
                
        self.dock_widgets = valid_docks
        
        logging.info(f"Branding Check: {len(visible_docks)} visible docks out of {len(valid_docks)} total.")
        
        if visible_docks:
            self.branding.hide()
        else:
            if self.centralWidget() != self.branding:
                self.setCentralWidget(self.branding)
            self.branding.show()
            self.branding.update() # Force repaint

    def check_docks_closed(self):
        self.update_branding_visibility()

    # --- Dock Management ---
    def add_note_dock(self, content="", title=None, obj_name=None):
        dock = self.dock_manager.add_note_dock(content, title, obj_name)
        return dock

    def add_browser_dock(self, url=None):
        dock = self.dock_manager.add_browser_dock(url)
        return dock





    def add_clipboard_dock(self):
        self.dock_manager.add_clipboard_dock(self.clipboard_manager)

    def paste_from_clipboard(self, text):
        """Sets system clipboard and inserts into active note if possible."""
        # 1. Update system clipboard
        self.clipboard_manager.clipboard.setText(text)
        
        # 2. Insert into active note
        from src.features.notes.note_pane import NotePane
        if self.active_pane and isinstance(self.active_pane, NotePane):
            self.active_pane.insertPlainText(text)
            self.statusBar().showMessage("Pasted from clipboard history", 2000)
            self.active_pane.setFocus()
        else:
            self.statusBar().showMessage("Copied to clipboard (Open a note to paste)", 2000)

    def set_active_pane(self, pane):
        self.active_pane = pane

    def apply_format(self, fmt_type):
        if self.active_pane:
            self.active_pane.apply_format(fmt_type)

    def insert_image_to_active_note(self):
        if self.active_pane and hasattr(self.active_pane, 'insert_image_from_file'):
            self.active_pane.insert_image_from_file()

    # --- Persistence ---
    def save_current_work(self):
        """Manual save triggered by user"""
        self.save_app_state()
        self.statusBar().showMessage("Saved successfully!", 2000)

    def save_app_state(self):
        # Convert QByteArray to Hex string for stable INI storage
        self.config.set_value("window/geometry", str(self.saveGeometry().toHex(), 'utf-8'))
        self.config.set_value("window/dock_state_v4", str(self.saveState().toHex(), 'utf-8'))
        
        storage = StorageManager()
        notes_data = []
        browser_data = []
        
        for dock in self.dock_widgets:
            try:
                widget = dock.widget()
                if not widget: continue
                if isinstance(widget, NotePane):
                    notes_data.append({"obj_name": dock.objectName(), "title": dock.windowTitle(), "content": widget.toHtml()})
                elif isinstance(widget, BrowserPane):
                    browser_data.append({"obj_name": dock.objectName(), "title": dock.windowTitle(), "url": widget.browser.url().toString()})
            except RuntimeError:
                continue
                
        storage.save_data({"notes": notes_data, "browsers": browser_data})

    def restore_app_state(self):
        logging.info("Starting restore_app_state...")
        storage = StorageManager()
        data = storage.load_data()
        
        # 1. AGGRESSIVE CLEANUP: Find ALL QDockWidgets, not just tracked ones
        # This fixes the "Ghost Dock" accumulation issue (Note 38, Browser 28, etc.)
        for dock in self.findChildren(QDockWidget):
            try:
                dock.close()
                dock.setParent(None)
                dock.deleteLater()
            except RuntimeError:
                pass
        self.dock_widgets.clear()
        
        # 2. Fresh install check
        is_fresh = not data
        
        # 3. Restore Notes (Limit to 5 to prevent overflow)
        notes = data.get("notes", [])
        if is_fresh:
            self.add_note_dock()
        else:
            for i, item in enumerate(notes):
                if i >= 5: break # Safety Cap
                dock = self.add_note_dock(title=item.get("title"), obj_name=item.get("obj_name"))
                if dock and dock.widget():
                    try:
                        dock.widget().setHtml(item.get("content", ""))
                    except RuntimeError:
                        pass
        
        # 4. Restore Browsers (Limit to 5)
        for i, item in enumerate(data.get("browsers", [])):
            if i >= 5: break # Safety Cap
            dock = self.add_browser_dock()
            if dock and dock.widget():
                try:
                    dock.widget().load_url(item.get("url", "https://google.com"))
                except RuntimeError:
                    pass

        # GUI State
        try:
            geo = self.config.get_value("window/geometry")
            if geo:
                if isinstance(geo, str):
                    self.restoreGeometry(QByteArray.fromHex(geo.encode()))
                else:
                    self.restoreGeometry(geo)
        except Exception as e:
            logging.error(f"Failed to restore geometry: {e}")
            
        try:
            state = self.config.get_value("window/dock_state_v4")
            if state:
                if isinstance(state, str):
                    self.restoreState(QByteArray.fromHex(state.encode()))
                else:
                    self.restoreState(state)
        except Exception as e:
            logging.error(f"Failed to restore state: {e}")
        
        # Cleanup
        self.update_branding_visibility()
        for dock in self.dock_widgets:
            try:
                dock.setFloating(False)
            except RuntimeError:
                pass


    def show_find_dialog(self):
        if not self.active_pane:
            return
            
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Find in Note", "Search text:")
        if ok and text:
            # Find in active pane (QTextEdit)
            from PyQt6.QtGui import QTextDocument
            found = self.active_pane.find(text)
            if not found:
                # Try from beginning
                from PyQt6.QtGui import QTextCursor
                start_cursor = self.active_pane.textCursor()
                start_cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.active_pane.setTextCursor(start_cursor)
                if not self.active_pane.find(text):
                    self.statusBar().showMessage(f"'{text}' not found.", 2000)

    # --- Utils ---

    def setup_stealth(self):
        # Initialize Global Stealth Filter
        from src.core.stealth import StealthEventFilter
        self.stealth_filter = StealthEventFilter(StealthManager, False)
        QApplication.instance().installEventFilter(self.stealth_filter)

        import keyboard
        def check_hotkey():
            keyboard.add_hotkey('ctrl+shift+space', lambda: QMetaObject.invokeMethod(self, "toggle_visibility", Qt.ConnectionType.QueuedConnection))
            keyboard.add_hotkey('ctrl+shift+f9', lambda: QMetaObject.invokeMethod(self, "toggle_ghost_click_external", Qt.ConnectionType.QueuedConnection))
            keyboard.wait()
        threading.Thread(target=check_hotkey, daemon=True).start()
        
        # Apply initial stealth state after window is shown
        def initial_stealth():
            stealth_act = self.menu_manager.actions.get("stealth")
            if stealth_act:
                self.toggle_stealth(stealth_act.isChecked())
        QTimer.singleShot(1000, initial_stealth)

    def toggle_stealth(self, checked):
        # Update global filter state
        if hasattr(self, 'stealth_filter'):
            self.stealth_filter.set_enabled(checked)
            
        # Apply to Main Window
        StealthManager.set_stealth_mode(int(self.winId()), checked)
        
        # Apply to all other top-level windows (Floating Docks, Browsers, Tooltips that exist)
        StealthManager.apply_to_all_windows(QApplication.instance(), checked)
        
        self.statusBar().showMessage("Stealth " + ("Enabled" if checked else "Disabled"), 2000)

    @pyqtSlot()
    def toggle_ghost_click_external(self):
        # Priority: If Teleprompter is open, toggle IT instead of Main Window
        if hasattr(self, 'teleprompter') and self.teleprompter and self.teleprompter.isVisible():
            # Toggle the button state directly to keep UI in sync
            self.teleprompter.btn_click_through.click()
            return

        ghost_click_act = self.menu_manager.actions.get("ghost_click")
        if ghost_click_act:
            new_state = not ghost_click_act.isChecked()
            ghost_click_act.setChecked(new_state)
            self.toggle_ghost_click(new_state)

    def toggle_ghost_click(self, checked):
        if StealthManager.set_click_through(int(self.winId()), checked):
            self.statusBar().showMessage("Ghost Click " + ("Enabled" if checked else "Disabled"), 2000)
        else:
            ghost_click_act = self.menu_manager.actions.get("ghost_click")
            if ghost_click_act:
                ghost_click_act.setChecked(not checked)



    def toggle_always_on_top(self):
        on_top_act = self.menu_manager.actions.get("always_on_top")
        on_top = on_top_act.isChecked() if on_top_act else False
        flags = self.windowFlags()
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            
        # IMPORTANT: Do not use Qt.WindowType.Tool as it hides the taskbar icon
        # flags &= ~Qt.WindowType.Tool 
        
        self.setWindowFlags(flags)
        self.show()

    def toggle_autosave(self):
        """Toggles the auto-save timer based on user action."""
        # Sync with menu action
        enabled = False
        autosave_act = self.menu_manager.actions.get("autosave")
        if autosave_act:
            enabled = autosave_act.isChecked()
            
        if enabled:
            if not self.autosave_timer.isActive():
                self.autosave_timer.start()
            self.statusBar().showMessage("Auto-Save Enabled", 2000)
        else:
            if self.autosave_timer.isActive():
                self.autosave_timer.stop()
            self.statusBar().showMessage("Auto-Save Disabled", 2000)
            
        # Save preference
        self.config.set_value("app/autosave_enabled", enabled)

    def change_window_opacity(self, value):
        self.setWindowOpacity(value / 100.0)

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Word & Text Files (*.docx *.txt *.md *.py *.js *.html);;All Files (*)")
        if path:
            content = UniversalReader.read_file(path)
            if content:
                # Content is already HTML-ready from UniversalReader (.docx via mammoth or .txt via internal logic)
                self.add_note_dock(content=content, title=os.path.basename(path))

    def show_shortcuts_dialog(self):
        QMessageBox.information(self, "Shortcuts", "Ctrl+N: Note\nCtrl+Shift+B: Browser\nCtrl+Shift+P: Prompter\nCtrl+Shift+S: Stealth\nCtrl+Shift+F9: Ghost Click")

    def open_teleprompter(self):
        content = self.active_pane.toHtml() if self.active_pane else ""
        self.teleprompter = TeleprompterDialog(content, None)
        self.teleprompter.show()

    def check_for_updates(self, manual=True):
        has_update, latest_version, url, error = check_for_updates()
        if has_update:
            QMessageBox.information(self, "Update", f"v{latest_version} available at {url}")
        elif manual:
            QMessageBox.information(self, "Update", "Up to date!")

    def rename_active_note(self):
        """Standard rename method (useful for shortcut)"""
        if not self.active_pane:
            return
            
        # Find which dock this pane belongs to
        for dock in self.dock_widgets:
            if dock.widget() == self.active_pane:
                self._show_rename_dialog(dock)
                break

    def _show_rename_dialog(self, dock):
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename Note", "New name:", text=dock.windowTitle())
        if ok and new_name.strip():
            dock.setWindowTitle(new_name.strip())
            self.save_app_state()

    def hook_tab_bars(self):
        """Finds all QTabBars in the window and connects to their signals."""
        from PyQt6.QtWidgets import QTabBar
        if not hasattr(self, '_hooked_tabbars'):
            self._hooked_tabbars = set()
            
        for tab_bar in self.findChildren(QTabBar):
            # Force tooltips to be the full tab text (for truncated tabs)
            for i in range(tab_bar.count()):
                text = tab_bar.tabText(i)
                if tab_bar.tabToolTip(i) != text:
                    tab_bar.setTabToolTip(i, text)

            if tab_bar not in self._hooked_tabbars:
                tab_bar.tabBarDoubleClicked.connect(lambda idx, tb=tab_bar: self.on_tab_double_clicked(tb, idx))
                tab_bar.currentChanged.connect(lambda idx, tb=tab_bar: self.on_tab_changed(tb, idx))
                
                # Tab Closing Support
                tab_bar.setTabsClosable(True)
                tab_bar.tabCloseRequested.connect(lambda idx, tb=tab_bar: self.on_tab_close_requested(tb, idx))
                
                # Context Menu Support for Deletion
                tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                tab_bar.customContextMenuRequested.connect(lambda pos, tb=tab_bar: self.on_tab_context_menu(tb, pos))
                
                self._hooked_tabbars.add(tab_bar)

    def on_tab_close_requested(self, tab_bar, index):
        """Called when the (x) button on a tab is clicked."""
        self.close_dock_at_tab_index(tab_bar, index)

    def on_tab_context_menu(self, tab_bar, pos):

        """Shows right-click menu for tabs."""
        index = tab_bar.tabAt(pos)
        if index < 0:
            return
            
        menu = QMenu(self)
        rename_act = QAction("Rename Note", self)
        rename_act.triggered.connect(lambda: self.on_tab_double_clicked(tab_bar, index))
        
        close_act = QAction("Close Note", self)
        close_act.triggered.connect(lambda: self.close_dock_at_tab_index(tab_bar, index))
        
        menu.addAction(rename_act)
        menu.addSeparator()
        menu.addAction(close_act)
        menu.exec(tab_bar.mapToGlobal(pos))



    def close_dock_at_tab_index(self, tab_bar, index):
        """Helper to find and remove a dock widget by its tab index."""
        title = tab_bar.tabText(index)
        dock_to_close = None
        
        # Find dock first safely
        for dock in self.dock_widgets:
            try:
                if dock.windowTitle() == title and not dock.isFloating():
                    dock_to_close = dock
                    break
            except RuntimeError:
                continue
                
        if dock_to_close:
            dock = dock_to_close
            # Cleanup active pane reference if this dock is being closed
            try:
                if dock.widget() == self.active_pane:
                    self.set_active_pane(None)
            except RuntimeError:
                self.set_active_pane(None)
                
            # Remove dock
            try:
                dock.close()
                dock.deleteLater()
            except RuntimeError:
                pass
                
            if dock in self.dock_widgets:
                self.dock_widgets.remove(dock)
            
            self.save_app_state()
            self.update_branding_visibility()

    def on_tab_changed(self, tab_bar, index):

        """Called when a tab is selected."""
        title = tab_bar.tabText(index)
        for dock in self.dock_widgets:
            if dock.windowTitle() == title and not dock.isFloating():
                widget = dock.widget()
                if isinstance(widget, NotePane):
                    self.set_active_pane(widget)
                else:
                    self.set_active_pane(None)
                break

    def on_tab_double_clicked(self, tab_bar, index):
        """Called when a tab is double-clicked."""
        title = tab_bar.tabText(index)
        for dock in self.dock_widgets:
            if dock.windowTitle() == title and not dock.isFloating():
                self._show_rename_dialog(dock)
                return


    def setup_status_bar_widgets(self):
        """Initializes the labels in the status bar."""
        from PyQt6.QtWidgets import QLabel
        
        # Create labels
        self.status_pos_label = QLabel("Ln 1, Col 1")
        self.status_char_label = QLabel("0 characters")
        self.status_zoom_label = QLabel("100%")
        self.status_eol_label = QLabel("Windows (CRLF)")
        self.status_enc_label = QLabel("UTF-8")
        
        # Add to status bar (permanent right side)
        sb = self.statusBar()
        sb.addPermanentWidget(self.status_pos_label)
        sb.addPermanentWidget(QLabel("  |  ")) # Separator
        sb.addPermanentWidget(self.status_char_label)
        sb.addPermanentWidget(QLabel("  |  "))
        sb.addPermanentWidget(self.status_zoom_label)
        sb.addPermanentWidget(QLabel("  |  "))
        sb.addPermanentWidget(self.status_eol_label)
        sb.addPermanentWidget(QLabel("  |  "))
        sb.addPermanentWidget(self.status_enc_label)
        sb.addPermanentWidget(QLabel("   ")) # Padding

    def update_status_bar_info(self):
        """Updates the status bar labels based on the active pane's content and cursor."""
        if not self.active_pane:
            self.status_pos_label.setText("")
            self.status_char_label.setText("")
            return
            
        try:
            # Check if C++ object is still valid
            if not self.active_pane.isVisible():
                 pass # Fall through to try block, but sometimes isVisible fails too

            # Get line/col
            cursor = self.active_pane.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.status_pos_label.setText(f"Ln {line}, Col {col}")
            
            # Count chars
            text = self.active_pane.toPlainText()
            self.status_char_label.setText(f"{len(text)} characters")
            
            # Zoom
            # self.status_zoom_label.setText(f"{self.active_pane.font().pointSize()}pt")
            
        except RuntimeError:
            # Widget deleted
            self.active_pane = None
            self.status_pos_label.setText("")
            self.status_char_label.setText("")
        
        # We can hardcode zoom/encoding for now unless we implement zoom/saving logic
        # self.status_zoom_label.setText("100%")
        # self.status_enc_label.setText("UTF-8")

    def closeEvent(self, event):
        self.save_app_state()
        super().closeEvent(event)


