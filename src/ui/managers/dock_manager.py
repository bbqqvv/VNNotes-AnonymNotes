from PyQt6.QtWidgets import QDockWidget, QMessageBox
from PyQt6.QtCore import Qt
import uuid
import logging

class DockManager:
    """
    Manages the creation, placement, and lifecycle of dock widgets.
    Handles 'Smart Docking' (Tabification) logic.
    """
    def __init__(self, main_window):
        self.main_window = main_window

    def add_note_dock(self, content="", title=None, obj_name=None, anchor_dock=None, file_path=None):
        if not obj_name:
            # Standardize naming to match services (NoteDock_N format ideally)
            # For now, keep the UUID logic for uniqueness but ensure it's recognizable
            uid = uuid.uuid4().hex
            obj_name = f"NoteDock_{uid[:8]}"
        
        # Check if dock already exists
        existing_dock = self.main_window.findChild(QDockWidget, obj_name)
        if existing_dock:
            existing_dock.show()
            existing_dock.raise_()
            return existing_dock
        
        dock = QDockWidget(title or "Note", self.main_window)
        dock.setObjectName(obj_name)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetClosable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        from src.features.notes.note_pane import NotePane
        note_pane = NotePane()
        note_pane.file_path = file_path
        if content:
            # Use deferred content for lazy loading only if it's large, 
            # but for restoration we often want it immediate.
            note_pane._deferred_content = content
        
        # Connect signals
        if hasattr(self.main_window, 'set_active_pane'):
            note_pane.focus_received.connect(self.main_window.set_active_pane)
        if hasattr(self.main_window, 'on_content_changed'):
            note_pane.textChanged.connect(self.main_window.on_content_changed)
        
        dock.setWidget(note_pane)
        
        # Tabification logic
        if anchor_dock:
             self.main_window.tabifyDockWidget(anchor_dock, dock)
        else:
            main_docks = [d for d in self.main_window.findChildren(QDockWidget) 
                          if d.objectName() != "SidebarDock" and d != dock]
            if main_docks:
                self.main_window.tabifyDockWidget(main_docks[-1], dock)
            else:
                self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        
        dock.show()
        dock.raise_()
        self._register_dock(dock)
        return dock

    def add_browser_dock(self, url=None, obj_name=None, anchor_dock=None):
        if not obj_name:
            # Standardize naming to match BrowserService logic
            max_id = 0
            for d in self.main_window.findChildren(QDockWidget):
                name = d.objectName()
                if name.startswith("BrowserDock_"):
                    try:
                        bid = int(name.split("_")[1])
                        if bid > max_id: max_id = bid
                    except (ValueError, IndexError): pass
            obj_name = f"BrowserDock_{max_id + 1}"

        # Check if exists
        existing_dock = self.main_window.findChild(QDockWidget, obj_name)
        if existing_dock:
            existing_dock.show()
            existing_dock.raise_()
            return existing_dock

        dock = QDockWidget("Mini Browser", self.main_window)
        dock.setObjectName(obj_name)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetClosable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        from src.features.browser.browser_pane import BrowserPane
        browser = BrowserPane(url, self.main_window)
        dock.setWidget(browser)
        
        browser.title_changed.connect(lambda t: self._update_dock_title(dock, t))

        # Tabification
        if anchor_dock:
             self.main_window.tabifyDockWidget(anchor_dock, dock)
        else:
            main_docks = [d for d in self.main_window.findChildren(QDockWidget) 
                          if d.objectName() != "SidebarDock" and d != dock]
            if main_docks:
                self.main_window.tabifyDockWidget(main_docks[-1], dock)
            else:
                self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
            
        dock.show()
        dock.raise_()
        self._register_dock(dock)
        
        # Sidebar refresh
        if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
            self.main_window.sidebar.refresh_tree()
        return dock

    def add_clipboard_dock(self, clipboard_manager_instance):
        existing = self.main_window.findChild(QDockWidget, "ClipboardDock")
        if existing:
            existing.show()
            existing.raise_()
            return existing

        dock = QDockWidget("Clipboard History", self.main_window)
        dock.setObjectName("ClipboardDock")
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        
        from src.features.clipboard.clipboard_pane import ClipboardPane
        clipboard_pane = ClipboardPane()
        
        clipboard_manager_instance.history_updated.connect(clipboard_pane.update_history)
        if hasattr(self.main_window, 'paste_from_clipboard'):
             clipboard_pane.item_clicked.connect(self.main_window.paste_from_clipboard)
        
        clipboard_pane.item_remove_requested.connect(clipboard_manager_instance.remove_item)
        clipboard_pane.clear_all_requested.connect(clipboard_manager_instance.clear_history)
        clipboard_pane.update_history(clipboard_manager_instance.get_history())

        dock.setWidget(clipboard_pane)
        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._register_dock(dock)
        return dock

    def _register_dock(self, dock):
        if hasattr(self.main_window, 'check_docks_closed'):
            dock.visibilityChanged.connect(lambda _: self.main_window.check_docks_closed())
        
        # Connection for destroyed to cleanup sidebar
        dock.destroyed.connect(lambda: self._on_dock_destroyed(dock))

    def _update_dock_title(self, dock, title):
        if not title: return
        dock.setWindowTitle(title)
        dock.setToolTip(title)
        
        if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
            try:
                self.main_window.sidebar.refresh_tree()
            except RuntimeError: pass

    def _on_dock_destroyed(self, dock):
        try:
            if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
                self.main_window.sidebar.refresh_tree()
            if hasattr(self.main_window, 'check_docks_closed'):
                self.main_window.check_docks_closed()
        except RuntimeError: pass

    def close_all_notes(self):
        from src.features.notes.note_pane import NotePane
        for dock in self.main_window.findChildren(QDockWidget):
            if isinstance(dock.widget(), NotePane):
                dock.close()

    def close_all_browsers(self):
        for dock in self.main_window.findChildren(QDockWidget):
            if dock.objectName().startswith("BrowserDock_"):
                dock.close()

    def close_all_docks(self):
        for dock in self.main_window.findChildren(QDockWidget):
            if dock.objectName() != "SidebarDock":
                dock.close()
