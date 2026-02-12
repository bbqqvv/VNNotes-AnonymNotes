import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QDockWidget, QToolBar, 
                             QMessageBox, QLabel)
from PyQt6.QtGui import QAction, QFont, QIcon
from PyQt6.QtCore import Qt, QUrl

from src.core.stealth import StealthManager
from src.core.config import ConfigManager
from src.features.notes.note_pane import NotePane
from src.features.browser.browser_pane import BrowserPane


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.setWindowTitle("Stealth Assist")
        
        # Load Geometry
        geo = self.config.get_value("window/geometry")
        if geo:
            try:
                self.restoreGeometry(bytes.fromhex(geo))
            except Exception:
                pass
        else:
            self.resize(1000, 700)
            
        self.dock_widgets = []
        
        self.setup_ui()
        self.setup_stealth()
        self.setup_tray() # New Tray Setup
        self.restore_app_state()
        
    def setup_tray(self):
        from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
        from PyQt6.QtGui import QIcon, QAction
        import os
        
        self.tray_icon = QSystemTrayIcon(self)
        
        # Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "appnote.png")
        if os.path.exists(icon_path):
             self.tray_icon.setIcon(QIcon(icon_path))
        else:
             # Fallback or standard icon
             self.tray_icon.setIcon(self.windowIcon())
             
        # Menu
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
        from PyQt6.QtWidgets import QSystemTrayIcon
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_visibility()

    def quit_app(self):
        self.save_app_state() # Ensure save on tray quit
        self.force_quit = True
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def setup_ui(self):
        # Central Widget (Hidden/Empty to allow docks to take over)
        central = QWidget()
        central.hide()
        self.setCentralWidget(central)
        
        # Dock Nesting
        self.setDockNestingEnabled(True)

        # Toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        # Note Action
        note_act = QAction("📝 + Note", self)
        note_act.triggered.connect(lambda: self.add_note_dock())
        toolbar.addAction(note_act)

        # Browser Action
        browser_act = QAction("🌐 + Browser", self)
        browser_act.triggered.connect(lambda: self.add_browser_dock())
        toolbar.addAction(browser_act)

        # Formatting
        toolbar.addSeparator()
        
        bold_act = QAction("B", self)
        bold_act.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        bold_act.triggered.connect(lambda: self.apply_format("bold"))
        toolbar.addAction(bold_act)
        
        italic_act = QAction("I", self)
        italic_act.setFont(QFont("Segoe UI", 9, -1, True))
        italic_act.triggered.connect(lambda: self.apply_format("italic"))
        toolbar.addAction(italic_act)
        
        underline_act = QAction("U", self)
        underline_act.triggered.connect(lambda: self.apply_format("underline"))
        f = underline_act.font()
        f.setUnderline(True)
        underline_act.setFont(f)
        toolbar.addAction(underline_act)
        
        toolbar.addSeparator()
        
        list_act = QAction("List", self)
        list_act.triggered.connect(lambda: self.apply_format("list"))
        toolbar.addAction(list_act)
        
        check_act = QAction("☑ Todo", self)
        check_act.triggered.connect(lambda: self.apply_format("checkbox"))
        toolbar.addAction(check_act)
        
        code_act = QAction("</>", self)
        code_act.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        code_act.triggered.connect(lambda: self.apply_format("code"))
        toolbar.addAction(code_act)
        
        high_act = QAction("🖊", self)
        # high_act.setStyleSheet("color: yellow; background: #333;") # Error: QAction has no setStyleSheet
        # We can't easily style QAction icon without QIcon. 
        # Just use the unicode char for now.
        high_act.triggered.connect(lambda: self.apply_format("highlight"))
        toolbar.addAction(high_act)
        
        toolbar.addSeparator()
        
        search_act = QAction("🔍", self)
        search_act.triggered.connect(self.show_find_dialog)
        toolbar.addAction(search_act)
        
        self.setup_menu()

    def setup_menu(self):
        menubar = self.menuBar()
        view_menu = menubar.addMenu("View")
        
        # Theme Submenu
        theme_menu = view_menu.addMenu("Theme")
        dark_act = QAction("Dark Mode", self)
        dark_act.triggered.connect(lambda: self.apply_theme("dark"))
        theme_menu.addAction(dark_act)
        
        light_act = QAction("Light Mode", self)
        light_act.triggered.connect(lambda: self.apply_theme("light"))
        theme_menu.addAction(light_act)
        
        view_menu.addSeparator()
        
        self.stealth_action = QAction("Super Stealth (Anti-Capture)", self)
        self.stealth_action.setCheckable(True)
        self.stealth_action.setChecked(True)
        self.stealth_action.setToolTip("Hides window from Screen Share/Recording (You can still see it)")
        self.stealth_action.setShortcut("Ctrl+Shift+S")
        self.stealth_action.triggered.connect(self.toggle_stealth)
        view_menu.addAction(self.stealth_action)
        
        self.top_action = QAction("Always on Top", self)
        self.top_action.setCheckable(True)
        self.top_action.setChecked(True)
        self.top_action.triggered.connect(self.toggle_always_on_top)
        view_menu.addAction(self.top_action)
        
        self.toggle_always_on_top(True)
        self.apply_theme("dark") # Default

    def apply_theme(self, mode):
        if mode == "dark":
            style = """
                QMainWindow, QDockWidget { background: #2b2b2b; color: #eee; }
                QTextEdit { background: #333; color: #eee; border: none; }
                QToolBar { background: #222; border-bottom: 1px solid #444; spacing: 5px; }
                QDockWidget::title { background: #222; padding: 5px; }
                QMenuBar { background: #222; color: #eee; }
                QMenuBar::item:selected { background: #444; }
                QMenu { background: #333; color: #eee; }
                QMenu::item:selected { background: #555; }
            """
        else:
            style = """
                QMainWindow, QDockWidget { background: #f5f5f5; color: #000; }
                QTextEdit { background: #fff; color: #000; border: none; }
                QToolBar { background: #e0e0e0; border-bottom: 1px solid #ccc; spacing: 5px; }
                QDockWidget::title { background: #e0e0e0; padding: 5px; }
                QMenuBar { background: #e0e0e0; color: #000; }
                QMenuBar::item:selected { background: #ccc; }
                QMenu { background: #fff; color: #000; }
                QMenu::item:selected { background: #ddd; }
            """
        self.setStyleSheet(style)
        
        # Propagate to panes if needed
        for dock in self.dock_widgets:
            widget = dock.widget()
            if isinstance(widget, NotePane):
                # NotePane has its own styleSheet in __init__, we might need to override it 
                # or make sure global style applies.
                # Global style usually applies if local not strictly set.
                # Let's force update or reset NotePane style.
                if mode == "dark":
                     widget.setStyleSheet("""
                        QTextEdit { background-color: #333; color: #eee; font-family: 'Segoe UI'; font-size: 14px; border: none; padding: 10px; }
                     """)
                else:
                     widget.setStyleSheet("""
                        QTextEdit { background-color: #fff; color: #000; font-family: 'Segoe UI'; font-size: 14px; border: none; padding: 10px; }
                     """)

    def add_note_dock(self, content="", title=None, obj_name=None):
        count = len(self.dock_widgets) + 1
        name = obj_name if obj_name else f"NoteDock_{count}_{Qt.GlobalColor.black}" # Unique ID better
        # Simple unique ID generation could be better, but count works if we save sequentially
        # Better: use timestamp or uuid if needed, but for now strict ordering is ok if we save cleanly
        
        if not title:
            title = f"Note {count}"
            
        dock = QDockWidget(title, self)
        dock.setObjectName(name) # Important for saveState
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        # Disable floating to keep stealth simple
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
        note_pane = NotePane()
        if content:
            note_pane.setHtml(content)
        
        # Track focus
        note_pane.focus_received.connect(self.set_active_pane)
        
        dock.setWidget(note_pane)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, dock)
        
        self.dock_widgets.append(dock)
        
        # Connect close event to remove from list? 
        # QDockWidget close just hides it by default usually, unless attribute set.
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dock.destroyed.connect(lambda: self.dock_widgets.remove(dock) if dock in self.dock_widgets else None)
        
        return dock

    def set_active_pane(self, pane):
        self.active_pane = pane

    def apply_format(self, fmt_type):
        if self.active_pane:
            self.active_pane.apply_format(fmt_type)
        elif self.dock_widgets:
            # Fallback to last added or first
            self.dock_widgets[-1].widget().apply_format(fmt_type)

    def add_browser_dock(self, url=None, title="Mini Browser", obj_name=None):
        count = len(self.dock_widgets) + 1
        name = obj_name if obj_name else f"BrowserDock_{count}"
        
        dock = QDockWidget(title, self)
        dock.setObjectName(name)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
        browser = BrowserPane()
        if url:
            browser.browser.setUrl(QUrl(url))
            
        dock.setWidget(browser)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.dock_widgets.append(dock)
        
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dock.destroyed.connect(lambda: self.dock_widgets.remove(dock) if dock in self.dock_widgets else None)
        
        return dock

    def add_ai_dock(self, title="AI Copilot", obj_name="AIDock_Main"):
        # Check if already exists? Maybe allow only one AI dock
        existing = self.findChild(QDockWidget, obj_name)
        if existing:
            existing.show()
            existing.raise_()
            return existing
            
        dock = QDockWidget(title, self)
        dock.setObjectName(obj_name)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetClosable)
        
        pane = AIPane()
        dock.setWidget(pane)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.dock_widgets.append(dock)
        
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dock.destroyed.connect(lambda: self.dock_widgets.remove(dock) if dock in self.dock_widgets else None)
        return dock



    # ... setup_stealth ...

    def save_app_state(self):
        # 1. Config (INI) - Layout & Geometry
        self.config.set_value("window/geometry", self.saveGeometry())
        self.config.set_value("window/dock_state", self.saveState())
        
        # 2. Data (JSON) - Content
        from src.core.storage import StorageManager
        storage = StorageManager()
        
        notes_data = []
        browser_data = []
        
        for dock in self.dock_widgets:
            # Save even if hidden, so we don't lose data of closed docks if we wanted to persist them?
            # Actually, if user closed it, maybe they want it gone. 
            # But "stealth" app usually persists everything. 
            # Let's save all valid docks in the list.
            if not dock.widget(): continue
            
            widget = dock.widget()
            if isinstance(widget, NotePane):
                notes_data.append({
                    "obj_name": dock.objectName(),
                    "title": dock.windowTitle(),
                    "content": widget.toHtml()
                })
            elif isinstance(widget, BrowserPane):
                browser_data.append({
                    "obj_name": dock.objectName(),
                    "title": dock.windowTitle(),
                    "url": widget.browser.url().toString()
                })
                
        full_data = {
            "notes": notes_data,
            "browsers": browser_data,
            "theme": "dark" # TODO: track actual theme state
        }
        
        storage.save_data(full_data)

    def restore_app_state(self):
        # 1. Load Data (JSON)
        from src.core.storage import StorageManager
        storage = StorageManager()
        data = storage.load_data()
        
        # Restore Notes
        notes_list = data.get("notes", [])
        for item in notes_list:
            dock = self.add_note_dock(title=item.get("title", "Note"), 
                                      obj_name=item.get("obj_name"))
            if dock and dock.widget():
                dock.widget().setHtml(item.get("content", ""))
                
        # Restore Browsers
        browser_list = data.get("browsers", [])
        for item in browser_list:
            dock = self.add_browser_dock(title=item.get("title", "Browser"),
                                         obj_name=item.get("obj_name"))
            if dock and dock.widget():
                dock.widget().load_url(item.get("url", "https://google.com"))

        # 2. Restore Layout & Geometry (INI)
        # MUST be done AFTER adding docks, otherwise restoreState won't find the docks to place.
        geo = self.config.get_value("window/geometry")
        if geo:
            try:
                self.restoreGeometry(bytes.fromhex(geo))
            except Exception:
                pass
                
        state = self.config.get_value("window/dock_state")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        self.save_app_state()
        
        if getattr(self, "force_quit", False):
            QMainWindow.closeEvent(self, event)
        else:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage("Stealth Assist", "App is running in background.", 
                                       self.tray_icon.MessageIcon.Information, 2000)

    # ... Stealth methods ...
    def setup_stealth(self):
        # Global Hotkey listener
        import keyboard
        import threading
        
        def check_hotkey():
            # Toggle visibility on Ctrl+Shift+Space
            keyboard.add_hotkey('ctrl+shift+space', self.toggle_visibility_safe)
            keyboard.wait()
            
        # Run in daemon thread
        threading.Thread(target=check_hotkey, daemon=True).start()

    def toggle_visibility_safe(self):
        # Keyboard callback runs in different thread, need to emit signal or use invokes
        # PyQt is not thread safe for UI updates from other threads directly usually, 
        # but simple show/hide might work or crash. Better use QMetaObject.invokeMethod.
        from PyQt6.QtCore import QMetaObject, Q_ARG
        QMetaObject.invokeMethod(self, "toggle_visibility", Qt.ConnectionType.QueuedConnection)

    from PyQt6.QtCore import pyqtSlot
    @pyqtSlot()
    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
            self.raise_()

    def change_opacity(self, value):
        opacity = value / 100.0
        self.setWindowOpacity(opacity)

    def showEvent(self, event):
        super().showEvent(event)
        if self.stealth_action.isChecked():
            self.toggle_stealth(True)

    def toggle_stealth(self, checked):
        hwnd = int(self.winId())
        StealthManager.set_stealth_mode(hwnd, checked)
        if checked:
            self.statusBar().showMessage("Stealth Enabled", 2000)
        else:
            self.statusBar().showMessage("Stealth Disabled", 2000)

    def show_find_dialog(self):
        if not self.active_pane:
            return
            
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "Find in Note", "Search text:")
        if ok and text:
             # Find in active pane (QTextEdit)
             # QTextEdit.find() returns bool
             found = self.active_pane.find(text)
             if not found:
                 # Try from beginning
                 # Move cursor to start
                 from PyQt6.QtGui import QTextCursor
                 start_cursor = self.active_pane.textCursor()
                 start_cursor.movePosition(QTextCursor.MoveOperation.Start)
                 self.active_pane.setTextCursor(start_cursor)
                 if not self.active_pane.find(text):
                      self.statusBar().showMessage(f"'{text}' not found.", 2000)

    def toggle_always_on_top(self, checked):
        flags = self.windowFlags()
        # Ensure Tool flag is always present to keep it hidden from taskbar
        flags |= Qt.WindowType.Tool
        
        if checked:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        
        self.show()
