import logging
import re
from PyQt6 import sip  # REQUIRED for zombie object checks

from PyQt6.QtWidgets import QDockWidget, QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from src.features.notes.note_pane import NotePane

logger = logging.getLogger(__name__)


class TabManager:
    """
    Manages tab bar hooks, context menus, close/close-others/close-all,
    tab-to-dock mapping, and tab selection/rename interactions.
    v7.0 (ULTIMATE STABILITY): Added sip.isdeleted guards + v6.9 Nuclear Safety.
    """

    def __init__(self, main_window):
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
        """Standardized ToolTip-ID lookup for tabs (v7.0 - ULTIMATE)."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return None
            if index < 0 or index >= tab_bar.count(): return None
            
            # 1. PRO LOOKUP: Direct widget query from parent
            parent = tab_bar.parentWidget()
            if parent and not sip.isdeleted(parent):
                try:
                    if hasattr(parent, 'widget'):
                        w = parent.widget(index)
                        if w and not sip.isdeleted(w) and isinstance(w, QDockWidget):
                            return w
                except (AttributeError, RuntimeError): pass

            # 2. FAIL-SAFE: ToolTip ID lookup
            tip = tab_bar.tabToolTip(index)
            if tip:
                match = re.search(r"\[ID: (.*?)\]", tip)
                if match:
                    obj_name = match.group(1)
                    dock = self.mw.dock_manager.get_dock(obj_name)
                    if dock and not sip.isdeleted(dock): return dock
                
            # 3. ABSOLUTE FALLBACK: Title matching
            title = tab_bar.tabText(index)
            if title:
                available = self.mw.dock_manager.get_all_content_docks()
                for d in available:
                    try:
                        if not d or sip.isdeleted(d): continue
                        if claimed_docks is not None and d in claimed_docks: continue
                        if d.windowTitle() == title and not d.isFloating():
                            return d
                    except RuntimeError: continue
                
            return None
        except (RuntimeError, Exception):
            return None

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
                        widget.setFocus() 
        except (RuntimeError, Exception): pass

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
            
            docks = self.get_docks_in_tab_order(tab_bar)
            for dock in docks:
                if dock and not sip.isdeleted(dock):
                    self._close_specific_dock(dock, skip_save=True)
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
            for dock in all_docks:
                try:
                    if not dock or sip.isdeleted(dock): continue
                    self._close_specific_dock(dock, skip_save=True)
                except (RuntimeError, Exception): continue
                
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
