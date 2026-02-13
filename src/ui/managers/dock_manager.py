from PyQt6.QtWidgets import QDockWidget, QMessageBox
from PyQt6.QtCore import Qt
from src.features.notes.note_pane import NotePane
from src.features.browser.browser_pane import BrowserPane

class DockManager:
    """
    Manages the creation, placement, and lifecycle of dock widgets.
    Handles 'Smart Docking' (Tabification) logic.
    """
    def __init__(self, main_window):
        self.main_window = main_window
        # We access main_window.dock_widgets list directly or maintain our own?
        # Maintaining sync is hard, so let's reference the main window's list for now
        # or better: MainWindow delegates all dock ops to this manager.

    def add_note_dock(self, content="", title=None, obj_name=None):
        count = len(self.main_window.dock_widgets) + 1
        name = obj_name if obj_name else f"NoteDock_{count}_{Qt.GlobalColor.black}"
        
        if not title:
            title = f"Note {count}"
            
        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(name)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetClosable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose) # Truly delete on close
        
        note_pane = NotePane()
        if content:
            note_pane.setHtml(content)
        
        # Track focus (Delegate back to main window if needed)
        if hasattr(self.main_window, 'set_active_pane'):
            note_pane.focus_received.connect(self.main_window.set_active_pane)
        
        dock.setWidget(note_pane)
        
        
        # Smart Docking Strategy: Tabify if other VISIBLE notes exist
        valid_docks = self._get_valid_docks()
        existing_notes = [d for d in valid_docks 
                          if isinstance(d.widget(), NotePane) and d != dock and d.isVisible() and not d.isFloating()]
        
        if existing_notes:
            self.main_window.tabifyDockWidget(existing_notes[0], dock)
        else:
            self.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
            
        dock.show()
        dock.raise_()
        self._register_dock(dock)

        dock.show()
        dock.raise_()
        self._register_dock(dock)

    def _get_valid_docks(self):
        """Returns a list of valid (non-deleted) dock widgets."""
        valid = []
        for d in self.main_window.dock_widgets:
            try:
                if not d.widget(): continue # access to check validity
                valid.append(d)
            except RuntimeError:
                pass
        return valid

    def add_browser_dock(self, url=None):
        # Filter specifically by object name or class name string to be safe
        valid_docks = self._get_valid_docks()
        existing_count = 0
        for d in valid_docks:
            if d.objectName().startswith("BrowserDock_"):
                existing_count += 1
        count = existing_count + 1
        
        dock = QDockWidget(f"Mini Browser {count}", self.main_window)
        dock.setObjectName(f"BrowserDock_{count}")
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetClosable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        browser = BrowserPane(url, self.main_window)
        browser = BrowserPane(url, self.main_window)
        dock.setWidget(browser)
        
        # Connect title updates
        browser.title_changed.connect(lambda t: self._update_dock_title(dock, t))

        
        # Check for existing browsers to tabify
        existing_browsers = [d for d in valid_docks 
                             if d.objectName().startswith("BrowserDock_") and d != dock and d.isVisible() and not d.isFloating()]
        
        if existing_browsers:
            self.main_window.tabifyDockWidget(existing_browsers[0], dock)
        else:
            # Simplify: Always add to Right Area. 
            # Since Notes are in Left Area, this effectively creates size-by-side.
            # This avoids 'splitDockWidget' failures with tabbed/hidden widgets.
            self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
            
        dock.show()
        dock.raise_()
        self._register_dock(dock)


        
    def add_clipboard_dock(self, clipboard_manager_instance):
        # Check if exists
        for dock in self.main_window.dock_widgets:
             if dock.objectName() == "ClipboardDock":
                dock.show()
                dock.raise_()
                return

        dock = QDockWidget("Clipboard History", self.main_window)
        dock.setObjectName("ClipboardDock")
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetClosable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        
        from src.features.clipboard.clipboard_pane import ClipboardPane
        clipboard_pane = ClipboardPane()
        
        # Connect signals
        clipboard_manager_instance.history_updated.connect(clipboard_pane.update_history)
        if hasattr(self.main_window, 'paste_from_clipboard'):
             clipboard_pane.item_clicked.connect(self.main_window.paste_from_clipboard)
        
        clipboard_pane.update_history(clipboard_manager_instance.get_history())

        dock.setWidget(clipboard_pane)
        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._register_dock(dock)

    def _register_dock(self, dock):
        self.main_window.dock_widgets.append(dock)
        self.main_window.dock_widgets.append(dock)
        # Connect visibility change to branding update
        if hasattr(self.main_window, 'check_docks_closed'):
            dock.visibilityChanged.connect(lambda: self.main_window.check_docks_closed())
            self.main_window.update_branding_visibility()
            
    def _update_dock_title(self, dock, title):
        """Updates dock title and tooltip, ensuring full text is available."""
        if not title: return
        dock.setWindowTitle(title)
        dock.setToolTip(title) # Set tooltip on the dock itself
        # Trigger tooltip update on tab bar immediately if possible
        if hasattr(self.main_window, 'hook_tab_bars'):
             self.main_window.hook_tab_bars()

            
        # Handle cleanup when dock is deleted
        dock.destroyed.connect(lambda: self._on_dock_destroyed(dock))

    def _on_dock_destroyed(self, dock):
        try:
            # Handle list removal carefully
            if hasattr(self.main_window, 'dock_widgets') and dock in self.main_window.dock_widgets:
                self.main_window.dock_widgets.remove(dock)
            
            # Check for branding update
            if getattr(self.main_window, 'check_docks_closed', None):
                 try:
                    self.main_window.check_docks_closed()
                 except RuntimeError:
                    pass # MainWindow might be deleting
                    
        except RuntimeError:
            pass # Container or items already deleted

    def close_all_notes(self):
        """Closes all Note docks."""
        # Create a copy of the list to avoid modification issues while iterating
        for dock in self.main_window.dock_widgets[:]: 
            try:
                if not dock.widget(): continue
                if isinstance(dock.widget(), NotePane):
                    dock.close() # Will trigger WA_DeleteOnClose and _on_dock_destroyed
            except RuntimeError:
                pass

    def close_all_browsers(self):
        """Closes all Browser docks."""
        for dock in self.main_window.dock_widgets[:]:
            try:
                if dock.objectName().startswith("BrowserDock_"):
                    dock.close()
            except RuntimeError:
                pass

    def close_all_docks(self):
        """Closes ALL docks (Notes + Browsers + Clipboard)."""
        for dock in self.main_window.dock_widgets[:]:
            try:
                dock.close()
            except RuntimeError:
                pass
