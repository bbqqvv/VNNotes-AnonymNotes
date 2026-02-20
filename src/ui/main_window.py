import json
import os
import sys
import threading
import logging

from PyQt6.QtWidgets import (QMainWindow, QWidget, QDockWidget, QToolBar, 
                             QMessageBox, QLabel, QSizePolicy, QSlider,
                             QSystemTrayIcon, QMenu, QApplication, QFileDialog, QTabWidget)
from PyQt6.QtGui import QAction, QFont, QIcon, QDesktopServices, QTextCursor
from PyQt6.QtCore import Qt, QUrl, QSize, QTimer, pyqtSlot, QMetaObject, Q_ARG, QByteArray
from PyQt6 import QtCore

from src.features.notes.note_pane import NotePane
from src.features.clipboard.clipboard_manager import ClipboardManager
from src.ui.branding import BrandingOverlay
from src.ui.managers.dock_manager import DockManager
from src.ui.managers.menu_toolbar_manager import MenuToolbarManager
from src.ui.managers.find_manager import FindManager
from src.ui.managers.visibility_manager import VisibilityManager
from src.ui.managers.tab_manager import TabManager
from src.ui.managers.dialog_manager import DialogManager
from src.ui.managers.status_bar_manager import StatusBarManager
from src.core.context import ServiceContext
from src.core.session_manager import SessionManager
from src.ui.sidebar import SidebarWidget
from src.ui.managers.theme_manager import ThemeManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ctx = ServiceContext.get_instance()
        self.config = self.ctx.config
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
        self.active_pane = None
        self.current_theme = self.config.get_value("app/theme", "dark")
        self.active_pane = None
        self.current_theme = self.config.get_value("app/theme", "dark")
        
        # Core Managers
        self.dock_manager = DockManager(self)
        self.menu_manager = MenuToolbarManager(self)
        self.theme_manager = ThemeManager(self, self.config, self.base_path)
        self.session_manager = SessionManager(self, self.ctx)
        self.clipboard_manager = ClipboardManager()
        self._is_restoring = False
        
        # Feature Managers (extracted for maintainability)
        self.find_manager = FindManager(self)
        self.visibility_manager = VisibilityManager(self)
        self.tab_manager = TabManager(self)
        self.dialog_manager = DialogManager(self)
        self.status_bar_manager = StatusBarManager(self)
        
        # Shortcuts to services from context
        self.note_service = self.ctx.notes
        self.browser_service = self.ctx.browser
        
        # Setup UI
        self.setup_window()
        self.setup_ui()
        self.setup_stealth()
        self.setup_tray()
        
        # Final Setup
        self.setup_status_bar_widgets()
        
        # Dynamically hook into tab bars for double-click renaming
        self.tab_hook_timer = QTimer(self)
        self.tab_hook_timer.timeout.connect(self.hook_tab_bars)
        self.tab_hook_timer.start(1000)
        
        # Periodic status bar updates
        self.status_update_timer = QTimer(self)
        self.status_update_timer.timeout.connect(self.update_status_bar_info)
        self.status_update_timer.start(200)

        
        # Restore State
        QTimer.singleShot(100, self.session_manager.restore_app_state)
        
        if self.session_manager:
             self.session_manager.start_autosave()

        # Check for updates
        # QTimer.singleShot(3000, lambda: self.check_for_updates(manual=False))

    def auto_save(self):
         self.session_manager.auto_save()

    def toggle_autosave(self):
        """Toggles the auto-save timer based on user action."""
        enabled = False
        if hasattr(self, 'menu_manager') and "autosave" in self.menu_manager.actions:
            autosave_act = self.menu_manager.actions.get("autosave")
            enabled = autosave_act.isChecked()
            
        if self.session_manager:
            self.session_manager.set_autosave_enabled(enabled)
            
        status = "Enabled" if enabled else "Disabled"
        self.statusBar().showMessage(f"Auto-Save {status}", 2000)

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

        # Prefer Horizontal splitting for Note/Browser areas
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)
        
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
        
        # 3. Sidebar (Note Explorer)
        self.note_service.load_notes() # Ensure data is loaded
        
        self.sidebar = SidebarWidget(self.note_service, self)
        self.sidebar_dock = QDockWidget("Note Explorer", self)
        self.sidebar_dock.setObjectName("SidebarDock")
        self.sidebar_dock.setWidget(self.sidebar)
        
        # Lock Sidebar: Only Closable (No Floating, No Moving)
        self.sidebar_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.sidebar_dock.setFixedWidth(280) # Fixed narrow width
        
        self.sidebar_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock)
        
        # Connect Sidebar signals
        self.sidebar.note_selected.connect(self.on_sidebar_note_selected)
        self.sidebar.note_renamed.connect(self.on_note_renamed)
        self.sidebar.note_deleted.connect(self.on_note_deleted)
        
        # 4. Apply Theme
        self.theme_manager.apply_theme()
        
        # 5. Global Shortcuts
        search_act = QAction("Global Search", self)
        search_act.setShortcut("Ctrl+Shift+F")
        search_act.triggered.connect(self.focus_sidebar_search)
        self.addAction(search_act)

    def focus_sidebar_search(self):
        """Toggles the sidebar search bar."""
        if hasattr(self, 'sidebar_dock') and hasattr(self, 'sidebar'):
            if not self.sidebar_dock.isVisible():
                self.sidebar_dock.show()
            
            # self.sidebar is the widget.
            if hasattr(self.sidebar, 'toggle_search'):
                self.sidebar.toggle_search()

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

    def quit_app(self):
        self.save_app_state()
        QApplication.quit()

    def toggle_sidebar(self):
        logging.info("Toggling Sidebar...")
        if hasattr(self, 'sidebar_dock'):
            if self.sidebar_dock.isVisible():
                logging.info("Sidebar is visible. Closing.")
                self.sidebar_dock.close()
            else:
                logging.info("Sidebar is hidden. Showing.")
                self.sidebar_dock.show()
                self.sidebar_dock.raise_()
                if self.sidebar_dock.isFloating():
                     self.sidebar_dock.setFloating(False)
                
                # Force ensure logic (in case of 0 size)
                # Ensure it's in the layout
                # self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock)
                
                # Check width
                if self.sidebar_dock.width() < 50:
                    self.sidebar_dock.resize(250, self.sidebar_dock.height())
        else:
            logging.error("Sidebar dock not found!")

    # Branding and Visibility Management
    def update_branding_visibility(self):
        """Show branding only when no docks are visible."""
        # Clean list and check for visible docks
        visible_docks = []
        
        for dock in self.findChildren(QDockWidget):
            try:
                # Skip Sidebar and check visibility
                if dock.objectName() == "SidebarDock":
                    continue
                    
                if dock.isVisible():
                    visible_docks.append(dock)
            except RuntimeError:
                pass
        
        logging.debug(f"Branding Check: {len(visible_docks)} visible docks.")
        
        if visible_docks:
            self.branding.hide()
        else:
            if self.centralWidget() != self.branding:
                self.setCentralWidget(self.branding)
            self.branding.show()
            self.branding.update() # Force repaint

    def check_docks_closed(self):
        self.update_branding_visibility()

    # --- File Management (Delegated) ---

    def save_file(self):
        self.dialog_manager.save_file()

    def save_file_as(self):
        self.dialog_manager.save_file_as()

    # --- Dock Management ---
    def add_note_dock(self, content="", title=None, obj_name=None, anchor_dock=None, file_path=None):
        if not obj_name and not self._is_restoring:
            # New note created by user: Get entity from service first
            note_data = self.note_service.add_note(title or "New Note", content)
            obj_name = note_data["obj_name"]
            title = note_data["title"]
            content = note_data["content"]
            
        dock = self.dock_manager.add_note_dock(content, title, obj_name, anchor_dock=anchor_dock, file_path=file_path)
        
        # Realtime Update for Sidebar (Skip during restoration)
        if not self._is_restoring and hasattr(self, 'sidebar'):
            self.sidebar.refresh_tree()
            
        return dock

    def add_browser_dock(self, url=None, anchor_dock=None, obj_name=None):
        if not url and not self._is_restoring:
            # New browser session
            browser_data = self.browser_service.add_browser()
            url = browser_data["url"]
            obj_name = browser_data["obj_name"]
            
        dock = self.dock_manager.add_browser_dock(url, anchor_dock=anchor_dock, obj_name=obj_name)
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
        self.session_manager.save_app_state()
        self.statusBar().showMessage("Saved successfully!", 2000)

    def save_app_state(self):
        self.session_manager.save_app_state()

    @pyqtSlot()
    def on_content_changed(self):
        """Triggered when user types or changes content. Restarts debounce timer."""
        if getattr(self, '_is_restoring', False):
            return
            
        autosave_enabled = self.config.get_value("app/autosave_enabled", True)
        if isinstance(autosave_enabled, str):
            autosave_enabled = autosave_enabled.lower() == 'true'
            
        if autosave_enabled and hasattr(self, 'session_manager'):
            self.session_manager.start_autosave()

        # --- Auto-Update Title from First Line ---
        # Use sender() to be precise about which pane changed
        pane = self.sender()
        from src.features.notes.note_pane import NotePane
        if not isinstance(pane, NotePane):
            pane = self.active_pane
            
        if isinstance(pane, NotePane):
             # Find corresponding dock
             for dock in self.findChildren(QDockWidget):
                 if dock.widget() == pane:
                     plain_text = pane.toPlainText().strip()
                     first_line = plain_text.split('\n')[0] if plain_text else "Untitled"
                     if len(first_line) > 30: first_line = first_line[:30] + "..."
                     
                     if first_line and dock.windowTitle() != first_line:
                         dock.setWindowTitle(first_line)
                         if hasattr(self, 'sidebar'):
                             self.sidebar.refresh_tree()
                     break

    def on_sidebar_note_selected(self, note_obj_name):
        """Opens or focuses a note selected from the sidebar."""
        # Check if already open
        for dock in self.findChildren(QDockWidget):
             if dock.objectName() == note_obj_name:
                 dock.show()
                 dock.raise_()
                 dock.setFocus()
                 return
        
        # If not open, restore it from Service
        logging.info(f"Restoring closed note: {note_obj_name}")
        note_data = self.note_service.get_note_by_id(note_obj_name)
        if note_data:
            self.dock_manager.add_note_dock(note_data.get("content", ""), note_data.get("title", "Untitled"), note_obj_name)
        else:
            logging.error(f"Could not find note data for {note_obj_name}")
            logging.error(f"Could not find note data for {note_obj_name}")

    def _is_dock_deleted(self, dock):
        try:
            # Accessing objectName will raise RuntimeError if deleted
            _ = dock.objectName()
            return False
        except RuntimeError:
            return True

    def on_note_renamed(self, obj_name, new_title):
        """Updates Dock title when note is renamed via Sidebar."""
        try:
            # logging.info(f"on_note_renamed triggered for {obj_name} -> {new_title}")
            
            dock = self.findChild(QDockWidget, obj_name)
            if dock:
                dock.setWindowTitle(new_title)
            else:
                # Robust fallback for when objectName might be slightly different or for child lookups
                for d in self.findChildren(QDockWidget):
                    try:
                        if d.objectName() == obj_name:
                            d.setWindowTitle(new_title)
                            return
                    except RuntimeError:
                        continue
                
                # It's okay if dock isn't open, no need to scream
                pass
        except RuntimeError as e:
            logging.error(f"Error accessing dock: {e}")

    def on_note_deleted(self, obj_name):
        """Closes Dock when note is deleted via Sidebar."""
        try:
            dock = self.findChild(QDockWidget, obj_name)
            if dock:
                dock.close()
            
            # Robust fallback lookup
            for d in self.findChildren(QDockWidget):
                try:
                    if d.objectName() == obj_name:
                        d.close()
                except RuntimeError:
                    pass
        except Exception as e:
            logging.error(f"Error deleting dock: {e}")

    def restore_app_state(self):
        self.session_manager.restore_app_state()

    # --- Delegated to FindManager ---
    def show_find_dialog(self):
        self.find_manager.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.find_manager.reposition()

    def eventFilter(self, obj, event):
        if self.find_manager.handle_key_event(obj, event):
            return True
        return super().eventFilter(obj, event)

    # --- Delegated to VisibilityManager ---

    def setup_stealth(self):
        self.visibility_manager.setup_stealth()

    @pyqtSlot()
    def toggle_visibility(self):
        self.visibility_manager.toggle_visibility()

    def toggle_stealth(self, checked):
        self.visibility_manager.toggle_stealth(checked)

    @pyqtSlot()
    def toggle_ghost_click_external(self):
        self.visibility_manager.toggle_ghost_click_external()

    def toggle_ghost_click(self, checked):
        self.visibility_manager.toggle_ghost_click(checked)

    def toggle_always_on_top(self):
        self.visibility_manager.toggle_always_on_top()

    def change_window_opacity(self, value):
        self.visibility_manager.change_window_opacity(value)

    # --- Delegated to DialogManager ---

    def open_file_dialog(self):
        self.dialog_manager.open_file_dialog()

    def show_shortcuts_dialog(self):
        self.dialog_manager.show_shortcuts_dialog()

    def show_about_dialog(self):
        self.dialog_manager.show_about_dialog()

    def open_teleprompter(self):
        self.dialog_manager.open_teleprompter()

    def check_for_updates(self, manual=True):
        self.dialog_manager.check_for_updates(manual)

    def rename_active_note(self):
        self.dialog_manager.rename_active_note()

    def _show_rename_dialog(self, dock):
        self.dialog_manager.show_rename_dialog(dock)

    # --- Delegated to TabManager ---

    def hook_tab_bars(self):
        self.tab_manager.hook_tab_bars()

    def close_active_tab(self):
        self.tab_manager.close_active_tab()

    def reopen_last_closed_tab(self):
        self.tab_manager.reopen_last_closed_tab()

    # --- Delegated to StatusBarManager ---

    def setup_status_bar_widgets(self):
        self.status_bar_manager.setup_widgets()
        # Create convenience references for backward compatibility
        self.status_pos_label = self.status_bar_manager.status_pos_label
        self.status_char_label = self.status_bar_manager.status_char_label
        self.status_zoom_label = self.status_bar_manager.status_zoom_label
        self.status_eol_label = self.status_bar_manager.status_eol_label
        self.status_enc_label = self.status_bar_manager.status_enc_label

    def update_status_bar_info(self):
        self.status_bar_manager.update_info()

    def closeEvent(self, event):
        self.save_app_state()
        super().closeEvent(event)


