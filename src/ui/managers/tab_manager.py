import logging
import re
from PyQt6 import sip  # REQUIRED for zombie object checks

from PyQt6.QtWidgets import QDockWidget, QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QObject

from src.features.notes.note_pane import NotePane

logger = logging.getLogger(__name__)


class TabManager(QObject):
    """
    Manages tab bar hooks, context menus, close/close-others/close-all,
    tab-to-dock mapping, and tab selection/rename interactions.
    v7.0 (ULTIMATE STABILITY): Added sip.isdeleted guards + v6.9 Nuclear Safety.
    """

    def __init__(self, main_window):
        super().__init__(main_window) # Parent is MainWindow for lifecycle
        self.mw = main_window
        self._closed_tabs_stack = []  # Stack of {title, content, obj_name}
        self._is_syncing = False      # Re-entrancy Guard

    def hook_tab_bars(self):
        """Finds all QTabBars in the window and connects to their signals."""
        if self._is_syncing: return
        self._is_syncing = True
        
        try:
            from PyQt6.QtWidgets import QTabBar
            tabbars = self.mw.findChildren(QTabBar)
            
            for tab_bar in tabbars:
                try:
                    # v7.0: ULTIMATE ZOMBIE GUARD
                    if not tab_bar or sip.isdeleted(tab_bar):
                        continue
                        
                    if not hasattr(tab_bar, 'count'):
                        continue
                        
                    # Plan v6.9: REMOVED the aggressive ToolTip sync loop.
                    
                    # Signal Setup with pointer-reuse safety
                    if not tab_bar.property("vnn_tab_hooked"):
                        tab_bar.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
                        tab_bar.installEventFilter(self)
                        tab_bar.setProperty("vnn_tab_hooked", True)
                        
                    if not tab_bar.property("hooked"):
                        tab_bar.tabBarDoubleClicked.connect(
                            lambda idx, tb=tab_bar: self.on_tab_double_clicked(tb, idx))
                        tab_bar.currentChanged.connect(
                            lambda idx, tb=tab_bar: self.on_tab_changed(tb, idx))
                        tab_bar.setTabsClosable(True)
                        tab_bar.tabCloseRequested.connect(
                            lambda idx, tb=tab_bar: self.on_tab_close_requested(tb, idx))
                        tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                        tab_bar.customContextMenuRequested.connect(
                            lambda pos, tb=tab_bar: self.on_tab_context_menu(tb, pos))
                        tab_bar.setProperty("hooked", True)
                        logger.debug(f"TabManager (v7.0): Hooked TabBar {id(tab_bar)}")
                except (RuntimeError, Exception): continue
                    
        except Exception as e:
            logger.error(f"TabManager: hook_tab_bars failure: {e}")
        finally:
            self._is_syncing = False

    def on_tab_close_requested(self, tab_bar, index):
        """Called when the (x) button on a tab is clicked."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            logger.debug(f"TabManager: Tab close requested for index {index}")
            self.close_dock_at_tab_index(tab_bar, index)
        except Exception as e:
            logger.error(f"TabManager: on_tab_close_requested error: {e}")

    def on_tab_context_menu(self, tab_bar, pos):
        """Shows right-click menu for tabs."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            index = tab_bar.tabAt(pos)
            menu = QMenu(self.mw)

            if index >= 0:
                rename_icon = self.mw.theme_manager.get_icon("rename.svg")
                rename_act = QAction(rename_icon, "Rename Note", self.mw)
                rename_act.triggered.connect(
                    lambda: self.on_tab_double_clicked(tab_bar, index))

                close_act = QAction("Close Note", self.mw)
                close_act.triggered.connect(
                    lambda: self.close_dock_at_tab_index(tab_bar, index))

                close_others_act = QAction("Close Other Tabs", self.mw)
                close_others_act.triggered.connect(
                    lambda: self.close_other_tabs(tab_bar, index))

                menu.addAction(rename_act)
                menu.addSeparator()
                menu.addAction(close_act)
                menu.addAction(close_others_act)

            menu.addSeparator()
            close_all_act = QAction("Close All Tabs", self.mw)
            close_all_act.triggered.connect(lambda: self.close_all_tabs(tab_bar))
            menu.addAction(close_all_act)

            menu.exec(tab_bar.mapToGlobal(pos))
        except (RuntimeError, Exception): pass

    def get_docks_in_tab_order(self, tab_bar):
        """Returns a list of QDockWidgets corresponding to the tabs in the given tab_bar."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return []
            tab_count = tab_bar.count()
            if tab_count == 0: return []

            ordered = [None] * tab_count
            claimed_docks = set()
            for i in range(tab_count):
                dock = self._get_dock_at_index(tab_bar, i, claimed_docks=claimed_docks)
                ordered[i] = dock
                if dock: claimed_docks.add(dock)
            return ordered
        except (RuntimeError, Exception): return []

    def _get_dock_at_index(self, tab_bar, index, claimed_docks=None):
        """
        Retrieves the QDockWidget associated with the tab at 'index'.
        Plan v12.7.1: Robust identification with relaxed area matching.
        """
        if index < 0 or not tab_bar or sip.isdeleted(tab_bar): return None
        
        try:
            # 1. Strategy: Direct widget query from parent
            parent = tab_bar.parentWidget()
            if parent and not sip.isdeleted(parent):
                try:
                    if hasattr(parent, 'widget'):
                        w = parent.widget(index)
                        if w and not sip.isdeleted(w):
                            target_dock = None
                            if isinstance(w, QDockWidget):
                                target_dock = w
                            else:
                                # Fallback: Sometimes the tab holds the content widget (NotePane),
                                # and its parent is the QDockWidget.
                                p = w.parent()
                                if p and isinstance(p, QDockWidget):
                                    target_dock = p
                            
                            if target_dock:
                                self._update_tab_tooltip(tab_bar, index, target_dock)
                                return target_dock
                except (AttributeError, RuntimeError): pass

            # 2. Strategy: Stack-Based Identification (The "Equivalence Class" trick)
            # Find the visible dock in the same area as this tab bar.
            # In a tab stack, only the ACTIVE tab's dock is visible.
            tab_text = tab_bar.tabText(index)
            if not tab_text: return None
            
            active_idx = tab_bar.currentIndex()
            if active_idx < 0: return None
            
            active_text = tab_bar.tabText(active_idx)
            visible_anchor = None
            
            # Find the ONE dock that is visible and matches the active tab's title
            for dock in self.mw.dock_manager.get_all_content_docks():
                if dock and not sip.isdeleted(dock) and dock.isVisible() and dock.windowTitle() == active_text:
                    # Check if this dock is actually tabified (it should be if there's a tab bar)
                    if self.mw.tabifiedDockWidgets(dock):
                        visible_anchor = dock
                        break
            
            if visible_anchor:
                # Get all docks tabified with this anchor (including the anchor itself)
                stack = [visible_anchor] + self.mw.tabifiedDockWidgets(visible_anchor)
                
                # Match title within this specific stack
                for dock in stack:
                    if dock and not sip.isdeleted(dock) and dock.windowTitle() == tab_text:
                        if claimed_docks is not None and dock in claimed_docks: continue
                        self._update_tab_tooltip(tab_bar, index, dock)
                        return dock
            
            # 3. Strategy: Global Fallback (Last resort)
            for dock in self.mw.dock_manager.get_all_content_docks():
                if dock and not sip.isdeleted(dock) and dock.windowTitle() == tab_text:
                    if claimed_docks is not None and dock in claimed_docks: continue
                    return dock
        except (RuntimeError, Exception):
             pass
        return None

    def _update_tab_tooltip(self, tab_bar, index, dock):
        """Enhances tab tooltips with folder context for notes."""
        try:
            obj_name = dock.objectName()
            if obj_name.startswith("NoteDock_") and hasattr(self.mw, 'note_service'):
                note = self.mw.note_service.get_note_by_id(obj_name)
                if note:
                    folder = note.get("folder", "General")
                    tab_bar.setTabToolTip(index, f"{note['title']} (Folder: {folder})")
                    return
            tab_bar.setTabToolTip(index, dock.windowTitle())
        except (RuntimeError, Exception): pass

    def on_tab_changed(self, tab_bar, index):
        """Called when a tab is selected."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            target_dock = self._get_dock_at_index(tab_bar, index)
            if target_dock and not sip.isdeleted(target_dock):
                widget = target_dock.widget()
                if widget and not sip.isdeleted(widget):
                    if isinstance(widget, NotePane):
                        self.mw.set_active_pane(widget)
                        # Plan v2.5: Only focus editor if a TabBar DOES NOT have focus.
                        # This is the most reliable way to ensure we don't steal focus after a click.
                        from PyQt6.QtWidgets import QTabBar
                        focused = QApplication.focusWidget()
                        if not isinstance(focused, QTabBar):
                            widget.setFocus() 
        except (RuntimeError, Exception): pass

    def eventFilter(self, watched, event):
        """Intercepts Tab/Shift+Tab keys on the TabBar to cycle tabs."""
        from PyQt6.QtWidgets import QTabBar
        from PyQt6.QtCore import QEvent
        
        if isinstance(watched, QTabBar):
            # Plan v2.5: Capture focus on click (tab or bar)
            if event.type() == QEvent.Type.MouseButtonPress:
                watched.setFocus()
                return False # Let QTabBar handle selection
                
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                # Use standard int() comparison for maximum PyQt version compatibility
                if key == int(Qt.Key.Key_Tab):
                    count = watched.count()
                    if count > 1:
                        new_idx = (watched.currentIndex() + 1) % count
                        watched.setCurrentIndex(new_idx)
                    return True # Consume Tab key
                elif key == int(Qt.Key.Key_Backtab): # Shift+Tab
                    count = watched.count()
                    if count > 1:
                        new_idx = (watched.currentIndex() - 1 + count) % count
                        watched.setCurrentIndex(new_idx)
                    return True # Consume Shift+Tab
                
        return super().eventFilter(watched, event)

    def on_tab_double_clicked(self, tab_bar, index):
        """Called when a tab is double-clicked — opens rename dialog."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            dock = self._get_dock_at_index(tab_bar, index)
            if dock and not sip.isdeleted(dock):
                self.mw.dialog_manager.show_rename_dialog(dock)
        except (RuntimeError, Exception): pass

    # ── Close / Reopen support ────────────────────────────────────────

    def close_all_tabs(self, tab_bar):
        """Closes all tabs in the given tab bar."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            
            # Batch optimization
            self.mw._is_batch_closing = True
            try:
                docks = self.get_docks_in_tab_order(tab_bar)
                for dock in docks:
                    if dock and not sip.isdeleted(dock):
                        self._close_specific_dock(dock, skip_save=True)
            finally:
                self.mw._is_batch_closing = False
                
            self.mw.save_app_state()
                
            if hasattr(self.mw, 'check_docks_closed'):
                self.mw.update_branding_visibility(immediate=True)
        except Exception: pass

    def close_other_tabs(self, tab_bar, current_index):
        """Closes all tabs except the one at current_index."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            docks = self.get_docks_in_tab_order(tab_bar)
            for i, dock in enumerate(docks):
                if i != current_index and dock and not sip.isdeleted(dock):
                    self._close_specific_dock(dock, skip_save=True)
            self.mw.save_app_state()
            if hasattr(self.mw, 'check_docks_closed'):
                self.mw.update_branding_visibility(immediate=True)
        except Exception: pass

    def _close_specific_dock(self, dock, skip_save=False):
        """Helper to close a specific dock instance."""
        try:
            if not dock or sip.isdeleted(dock): return
            self._save_closed_tab_info(dock)
            if hasattr(self.mw, 'active_pane') and dock.widget() == self.mw.active_pane:
                self.mw.set_active_pane(None)
            
            # Plan v7.6: Brand this dock as closing so save_app_state ignores it during event sequence
            dock.setProperty("vnn_closing", True)
            
            # Plan v7.7: Nuclear Excision. Immediately remove from QMainWindow layout to prevent 
            # Qt's QDockAreaLayout memory leaks during rapid batch tab closures.
            if hasattr(self.mw, 'removeDockWidget'):
                self.mw.removeDockWidget(dock)
            dock.setParent(None)
            
            dock.close()
            if not skip_save:
                self.mw.save_app_state()
        except (RuntimeError, Exception): pass

    def close_all_tabs_app_wide(self):
        """Closes every content dock in the entire application."""
        try:
            all_docks = self.mw.dock_manager.get_all_content_docks()
            if not all_docks: return
            
            self.mw.set_active_pane(None)
            self.mw._is_batch_closing = True
            try:
                for dock in all_docks:
                    try:
                        if not dock or sip.isdeleted(dock): continue
                        self._close_specific_dock(dock, skip_save=True)
                    except (RuntimeError, Exception): continue
            finally:
                self.mw._is_batch_closing = False
                
            self.mw.save_app_state()
                
            if hasattr(self.mw, 'check_docks_closed'):
                self.mw.update_branding_visibility(immediate=True)
        except Exception: pass

    def close_dock_at_tab_index(self, tab_bar, index):
        """Helper to find and remove a dock widget by its tab index."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            dock_to_close = self._get_dock_at_index(tab_bar, index)
            if dock_to_close and not sip.isdeleted(dock_to_close):
                self._close_specific_dock(dock_to_close)
        except Exception: pass

    def _save_closed_tab_info(self, dock):
        """Snapshot the dock's title, content, and obj_name before it's deleted."""
        try:
            if not dock or sip.isdeleted(dock): return
            widget = dock.widget()
            if not widget or sip.isdeleted(widget): return
            
            content = ""
            if isinstance(widget, NotePane):
                content = widget.toHtml()
            info = {
                "title": dock.windowTitle(),
                "content": content,
                "obj_name": dock.objectName(),
            }
            self._closed_tabs_stack.append(info)
            if len(self._closed_tabs_stack) > 20:
                self._closed_tabs_stack.pop(0)
        except (RuntimeError, Exception): pass

    def close_active_tab(self):
        """Close the currently active tab/dock (Ctrl+W)."""
        try:
            if not self.mw.active_pane or sip.isdeleted(self.mw.active_pane): return
            for dock in self.mw.findChildren(QDockWidget):
                try:
                    if sip.isdeleted(dock): continue
                    if dock.widget() == self.mw.active_pane and dock.objectName() != "SidebarDock":
                        self._close_specific_dock(dock)
                        return
                except (RuntimeError, Exception): continue
        except (RuntimeError, Exception): pass

    def reopen_last_closed_tab(self):
        """Reopen the most recently closed tab (Ctrl+Shift+T)."""
        try:
            if not self._closed_tabs_stack: return
            info = self._closed_tabs_stack.pop()
            self.mw.dock_manager.add_note_dock(
                content=info["content"],
                title=info["title"],
                obj_name=info["obj_name"],
            )
        except (RuntimeError, Exception): pass
