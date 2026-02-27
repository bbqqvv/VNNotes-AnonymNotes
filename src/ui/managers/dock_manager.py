from PyQt6.QtWidgets import QDockWidget, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6 import sip
import uuid
import logging

class DockManager:
    """
    Manages the creation, placement, and lifecycle of dock widgets.
    Handles 'Smart Docking' (Tabification) logic.
    Uses an internal registry for O(1) dock lookups instead of findChildren.
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self._registry = {}  # obj_name -> QDockWidget
        self._identity_recursion_guard = False # Fixes AttributeError Crash

    def add_note_dock(self, content="", title=None, obj_name=None, anchor_dock=None, file_path=None, zoom=100):
        if not obj_name:
            # Standardize naming to match services (NoteDock_N format ideally)
            # For now, keep the UUID logic for uniqueness but ensure it's recognizable
            uid = uuid.uuid4().hex
            obj_name = f"NoteDock_{uid[:8]}"
        
        # Check if dock already exists (O(1) registry lookup)
        existing_dock = self._registry.get(obj_name)
        if existing_dock:
            try:
                existing_dock.show()
                existing_dock.raise_()
                return existing_dock
            except RuntimeError:
                del self._registry[obj_name]
        
        dock = QDockWidget(title or "Note", self.main_window)
        dock.setObjectName(obj_name)
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | 
                         QDockWidget.DockWidgetFeature.DockWidgetClosable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        from src.features.notes.note_pane import NotePane
        note_pane = NotePane(zoom=zoom)
        note_pane.setObjectName(obj_name) # CRITICAL for Zero-Lag sync
        note_pane.file_path = file_path
        # Apply Advanced Editor Preferences (Dev Mode)
        dev_mode = self.main_window.config.get_value("editor/dev_mode", "false").lower() == "true"
        note_pane.toggle_dev_mode(dev_mode)
        
        if content is not None:
            # CORRECT: Use the manager's setter instead of setting on the editor directly
            note_pane.paging_engine.set_deferred_content(content)
        
        # Connect signals
        if hasattr(self.main_window, 'set_active_pane'):
            note_pane.focus_received.connect(self.main_window.set_active_pane)
        if hasattr(self.main_window, 'on_content_changed'):
            note_pane.textChanged.connect(self.main_window.on_content_changed)
        
        # Plan v12.6: Internal link navigation
        note_pane.internal_link_clicked.connect(self.handle_internal_link)
        
        dock.setWidget(note_pane)
        
        # ROOT CAUSE FIX: Register signals BEFORE adding to layout or showing.
        self._register_dock(dock)
        
        # DIAMOND-STANDARD: Ensure that if `showEvent` is swallowed by QTabWidget during restoration
        # or manual tab-switching, `visibilityChanged` acts as a fail-safe lazy-load trigger.
        dock.visibilityChanged.connect(lambda visible: note_pane.load_deferred_content() if visible else None)
        
        # Tabification logic - Skip during restoration (restoreState handles it)
        if not self.main_window._is_restoring:
            if anchor_dock:
                 self.main_window.tabifyDockWidget(anchor_dock, dock)
            else:
                # Use registry for O(1) dock lookup instead of findChildren
                main_docks = [d for d in self.get_all_content_docks()
                              if d != dock 
                              and self.main_window.dockWidgetArea(d) == Qt.DockWidgetArea.RightDockWidgetArea]
                if main_docks:
                    self.main_window.tabifyDockWidget(main_docks[-1], dock)
                else:
                    self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        else:
            # Consistent placement for restoration
            self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        
        dock.show()
        if not self.main_window._is_restoring:
            dock.raise_()
            if hasattr(self.main_window, 'tab_hook_timer'):
                self.main_window.tab_hook_timer.start(500)
            
        return dock

    def add_browser_dock(self, url=None, obj_name=None, anchor_dock=None):
        if not obj_name:
            # Standardize naming to match BrowserService logic
            max_id = 0
            for d in list(self._registry.values()):
                try:
                    name = d.objectName()
                    if name.startswith("BrowserDock_"):
                        bid = int(name.split("_")[1])
                        if bid > max_id: max_id = bid
                except (ValueError, IndexError, RuntimeError): 
                    # RuntimeError handles "wrapped C/C++ object has been deleted"
                    pass
            obj_name = f"BrowserDock_{max_id + 1}"

        # Check if exists (O(1) registry lookup)
        existing_dock = self._registry.get(obj_name)
        if existing_dock:
            try:
                existing_dock.show()
                existing_dock.raise_()
                return existing_dock
            except RuntimeError:
                del self._registry[obj_name]

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

        # ROOT CAUSE FIX: Register signals BEFORE adding to layout or showing.
        self._register_dock(dock)

        # Tabification - Skip during restoration
        if not self.main_window._is_restoring:
            if anchor_dock:
                 self.main_window.tabifyDockWidget(anchor_dock, dock)
            else:
                main_docks = [d for d in self.get_all_content_docks() if d != dock]
                if main_docks:
                    self.main_window.tabifyDockWidget(main_docks[-1], dock)
                else:
                    self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        else:
            self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
            
        dock.show()
        if not self.main_window._is_restoring:
            dock.raise_()
            if hasattr(self.main_window, 'tab_hook_timer'):
                self.main_window.tab_hook_timer.start(500)
        
        # Sidebar refresh
        if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
            self.main_window.sidebar.refresh_tree()
            
        return dock

    def add_clipboard_dock(self, clipboard_manager_instance):
        existing = self._registry.get("ClipboardDock")
        if existing:
            try:
                existing.show()
                existing.raise_()
                return existing
            except RuntimeError:
                del self._registry["ClipboardDock"]

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
        self._register_dock(dock)
        self.main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        # Identity Tagging
        self._update_dock_identity(dock)
        return dock

    def handle_internal_link(self, obj_name):
        """Switches to or opens a note from a vnnote:// link."""
        existing = self.get_dock(obj_name)
        if existing:
            existing.show()
            existing.raise_()
            existing.setFocus()
            return
            
        # If not open, load from service
        if hasattr(self.main_window, 'note_service'):
            note = self.main_window.note_service.get_note_by_id(obj_name)
            if note:
                folder_name = note.get("folder", "General")
                
                # Security Check (Plan v12.7): Prompt password if the folder is locked
                if self.main_window.note_service.is_folder_locked(folder_name):
                    from src.ui.password_dialog import PasswordDialog
                    from PyQt6.QtWidgets import QMessageBox
                    # Determine theme mode for dialog styling
                    is_dark = True
                    if hasattr(self.main_window, 'theme_manager'):
                         is_dark = self.main_window.theme_manager.is_dark_mode
                         
                    pwd, ok = PasswordDialog.get_input(
                        self.main_window, 
                        title=f"Unlock Vault: {folder_name}", 
                        message=f"Enter password to access linked note:", 
                        is_dark=is_dark
                    )
                    
                    if not ok or not self.main_window.note_service.unlock_folder(folder_name, pwd):
                        if ok: # Only show warning if they pressed OK but pwd was wrong
                            QMessageBox.warning(self.main_window, "Access Denied", "Incorrect password.")
                        return
                    # Refresh sidebar to show unlocked folder
                    if hasattr(self.main_window, 'sidebar'):
                        self.main_window.sidebar.refresh_tree()
                        
                content = self.main_window.note_service.get_note_content(obj_name)
                self.add_note_dock(
                    content=content,
                    title=note.get("title", "Note"),
                    obj_name=obj_name
                )

    def _register_dock(self, dock):
        obj_name = dock.objectName()
        self._registry[obj_name] = dock
        
        if hasattr(self.main_window, 'check_docks_closed'):
            dock.visibilityChanged.connect(lambda _: self.main_window.check_docks_closed())
        
        # Identity Tagging (Plan v5)
        self._update_dock_identity(dock)
        
        # Connection for destroyed to cleanup registry, sidebar and MainWindow cache
        dock.destroyed.connect(lambda obj: self._on_dock_destroyed(obj))
        if hasattr(self.main_window, 'on_dock_destroyed'):
            dock.destroyed.connect(self.main_window.on_dock_destroyed)
        
        # Re-trigger tab bar hook (single-shot timer) when dock layout changes
        if hasattr(self.main_window, 'tab_hook_timer'):
            self.main_window.tab_hook_timer.start(1500)

    def _update_dock_title(self, dock, title):
        if not title: return
        dock.setWindowTitle(title)
        # Identity-Aware ToolTip: Combine Title + hidden ID (Plan v5)
        self._update_dock_identity(dock, title)
        
        if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
            try:
                self.main_window.sidebar.refresh_tree()
            except RuntimeError: pass

    def _get_base_title(self, title):
        """Strips ' (N)' suffix to find the intentional name (Plan v13.6)."""
        if not title: return ""
        import re
        match = re.search(r" \((\d+)\)$", title)
        if match:
            return title[:match.start()].strip()
        return title.strip()

    def _update_dock_identity(self, dock, title=None):
        """
        Standardized dynamic title & identification manager (v13.9 Group-Wide Natural Sort).
        Ensures tab numbering follows opening order (1, 2, 3) and updates the whole group.
        """
        if self._identity_recursion_guard:
             return
             
        try:
            self._identity_recursion_guard = True
            
            from src.features.notes.note_pane import NotePane
            from PyQt6 import sip
            
            if sip.isdeleted(dock): return
            
            obj_name = dock.objectName()
            widget = dock.widget()
            
            if isinstance(widget, NotePane) and obj_name.startswith("NoteDock_") and hasattr(self.main_window, 'note_service'):
                # 1. Get Base Identity
                note = self.main_window.note_service.get_note_by_id(obj_name)
                db_title = note.get("title", "Note") if note else (dock.property("vnn_intentional_title") or dock.windowTitle())
                base_title = self._get_base_title(db_title)
                folder = note.get("folder", "General") if note else "General"
                
                # 2. Group-Wide Update: Find all docks sharing this base title
                all_docks = self.get_all_content_docks()
                related_group = []
                for d in all_docks:
                    try:
                        if not sip.isdeleted(d) and d.objectName().startswith("NoteDock_"):
                            # Get the intentional title of each dock in the group
                            # We check DB first, then property, then windowTitle
                            d_note = self.main_window.note_service.get_note_by_id(d.objectName())
                            d_db_title = d_note.get("title", "Note") if d_note else (d.property("vnn_intentional_title") or d.windowTitle())
                            d_base = self._get_base_title(d_db_title)
                            
                            if d_base.lower() == base_title.lower():
                                related_group.append(d)
                    except (RuntimeError, AttributeError): continue

                # 3. Sort by Visual Index (Natural Sort fallback)
                def get_sort_key(d):
                    # Try to get visual index from TabManager for left-to-right numbering
                    visual_idx = 9999
                    if hasattr(self.main_window, 'tab_manager'):
                        from PyQt6.QtWidgets import QTabBar
                        tabbars = self.main_window.findChildren(QTabBar)
                        for tb in tabbars:
                            if not sip.isdeleted(tb):
                                for i in range(tb.count()):
                                    # Cross-call to TabManager to find which dock is at which tab
                                    if self.main_window.tab_manager._get_dock_at_index(tb, i) == d:
                                        visual_idx = i
                                        break
                            if visual_idx != 9999: break
                    
                    opening_order = 0
                    try:
                        opening_order = int(d.objectName().split("_")[1])
                    except Exception: pass
                    
                    return (visual_idx, opening_order)
                
                related_group.sort(key=get_sort_key)
                
                has_collision = len(related_group) > 1

                # 4. Update EVERY dock in the group to ensure consistency
                for idx, group_dock in enumerate(related_group):
                    g_note = self.main_window.note_service.get_note_by_id(group_dock.objectName())
                    g_db_title = g_note.get("title", "Note") if g_note else (group_dock.property("vnn_intentional_title") or group_dock.windowTitle())
                    g_base = self._get_base_title(g_db_title)
                    
                    # Store intentional title (clean) for persistence
                    if not group_dock.property("vnn_intentional_title"):
                         group_dock.setProperty("vnn_intentional_title", g_db_title)

                    target_title = g_db_title
                    if has_collision:
                        # Follow opening order: (1), (2), (3)...
                        target_title = f"{g_base} ({idx + 1})"
                    
                    if group_dock.windowTitle() != target_title:
                        group_dock.setWindowTitle(target_title)
                    
                    # Simplified Tooltip for the group
                    group_dock.setToolTip(target_title)
                return

            # Default fallback for browsers or non-note docks
            actual_title = title or dock.windowTitle()
            dock.setToolTip(actual_title)
            
        except (RuntimeError, AttributeError) as e:
            import logging
            logging.debug(f"DockManager: _update_dock_identity failed: {e}")
        finally:
            self._identity_recursion_guard = False

    def _on_dock_destroyed(self, dock):
        # Clean up registry
        to_remove = [k for k, v in self._registry.items() if v is dock]
        for k in to_remove:
            del self._registry[k]
        
        # Guard against MainWindow already being partially torn down
        if sip.isdeleted(self.main_window):
            return

        try:
            if hasattr(self.main_window, 'sidebar') and self.main_window.sidebar:
                # Plan v12.7.2: Skip expensive refresh during batch closing
                if not getattr(self.main_window, '_is_batch_closing', False):
                    self.main_window.sidebar.refresh_tree()
            if hasattr(self.main_window, 'check_docks_closed'):
                self.main_window.check_docks_closed()
        except (RuntimeError, AttributeError): pass

    # --- Registry Query Helpers ---

    def get_dock(self, obj_name):
        """O(1) dock lookup by object name."""
        dock = self._registry.get(obj_name)
        if dock:
            try:
                _ = dock.objectName()  # Verify not deleted
                return dock
            except RuntimeError:
                del self._registry[obj_name]
        return None

    def get_all_content_docks(self):
        """Returns all registered docks except SidebarDock."""
        result = []
        stale = []
        for name, dock in self._registry.items():
            try:
                if dock.objectName() != "SidebarDock":
                    result.append(dock)
            except RuntimeError:
                stale.append(name)
        for name in stale:
            del self._registry[name]
        return result

    def get_note_docks(self):
        """Returns only note docks."""
        return [d for d in self.get_all_content_docks() if d.objectName().startswith("NoteDock_")]

    def refresh_all_note_titles(self):
        """Re-calculates (1), (2), (3) for all open notes (e.g. after tab move)."""
        seen_bases = set()
        for dock in self.get_note_docks():
            db_title = dock.property("vnn_intentional_title") or dock.windowTitle()
            base = self._get_base_title(db_title).lower()
            if base not in seen_bases:
                self._update_dock_identity(dock)
                seen_bases.add(base)

    def get_browser_docks(self):
        """Returns only browser docks."""
        return [d for d in self.get_all_content_docks() if d.objectName().startswith("BrowserDock_")]

    def close_all_notes(self):
        try:
            for dock in list(self.get_note_docks()):
                if hasattr(self.main_window, 'tab_manager'):
                    self.main_window.tab_manager._close_specific_dock(dock, skip_save=True)
                else:
                    dock.close()
            if hasattr(self.main_window, 'save_app_state'): self.main_window.save_app_state()
        except Exception: pass
            
        if hasattr(self.main_window, 'update_branding_visibility'): 
            self.main_window.update_branding_visibility(immediate=True)

    def close_all_browsers(self):
        try:
            for dock in list(self.get_browser_docks()):
                if hasattr(self.main_window, 'tab_manager'):
                    self.main_window.tab_manager._close_specific_dock(dock, skip_save=True)
                else:
                    dock.close()
            if hasattr(self.main_window, 'save_app_state'): self.main_window.save_app_state()
        except Exception: pass
            
        if hasattr(self.main_window, 'update_branding_visibility'): 
            self.main_window.update_branding_visibility(immediate=True)

    def close_all_docks(self):
        try:
            for dock in list(self.get_all_content_docks()):
                if hasattr(self.main_window, 'tab_manager'):
                    self.main_window.tab_manager._close_specific_dock(dock, skip_save=True)
                else:
                    dock.close()
            if hasattr(self.main_window, 'save_app_state'): self.main_window.save_app_state()
        except Exception: pass
            
        if hasattr(self.main_window, 'update_branding_visibility'): 
            self.main_window.update_branding_visibility(immediate=True)
