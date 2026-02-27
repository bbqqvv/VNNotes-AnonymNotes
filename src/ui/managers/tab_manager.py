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
                        # Plan v15.9: Use StrongFocus so user can click to switch mode, 
                        # or Tab into it (though clicking is the primary trigger).
                        tab_bar.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
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
                        # Plan v16.3: Connect tabBarClicked to ensure redundant clicks (same tab)
                        # still trigger the sidebar sync logic.
                        tab_bar.tabBarClicked.connect(
                            lambda idx, tb=tab_bar: self.on_tab_changed(tb, idx))
                        
                        # Plan v13.9: Connect tabMoved to sync visual numbering (1, 2, 3...)
                        tab_bar.tabMoved.connect(
                            lambda f, t, tb=tab_bar: self._on_tab_moved(f, t, tb))
                        
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
            import traceback
            logger.error(traceback.format_exc())

    def on_tab_context_menu(self, tab_bar, pos):
        """Shows right-click menu for tabs."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            index = tab_bar.tabAt(pos)
            menu = QMenu(self.mw)

            if index >= 0:
                try:
                    # Rename Note action
                    rename_icon = self.mw.theme_manager.get_icon("rename.svg")
                    rename_act = QAction(rename_icon, "Rename Note", self.mw)
                    rename_act.triggered.connect(lambda: self.on_tab_double_clicked(tab_bar, index))
                    menu.addAction(rename_act)
                    menu.addSeparator()

                    # Individual Close actions
                    close_act = QAction("Close Note", self.mw)
                    close_act.triggered.connect(lambda: self.close_dock_at_tab_index(tab_bar, index))
                    
                    close_others_act = QAction("Close Other Tabs", self.mw)
                    close_others_act.triggered.connect(lambda: self.close_other_tabs(tab_bar, index))
                    
                    menu.addAction(close_act)
                    menu.addAction(close_others_act)
                    menu.addSeparator()
                except Exception as e:
                    logger.debug(f"TabManager: Optional menu items failed for index {index}: {e}")

            # App-wide Close All (Always show)
            close_all_act = QAction("Close All Tabs", self.mw)
            close_all_act.triggered.connect(lambda: self.close_all_tabs(tab_bar))
            menu.addAction(close_all_act)

            menu.exec(tab_bar.mapToGlobal(pos))
        except Exception as e:
            logger.error(f"TabManager error: {e}")
            import traceback
            logger.error(traceback.format_exc())

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
        Plan v13.0: Uses unique object names for robust matching.
        """
        if index < 0 or not tab_bar or sip.isdeleted(tab_bar): return None
        
        try:
            # 1. Strategy: Direct widget query from parent (Fastest & Safest)
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
                                p = w.parent()
                                if p and isinstance(p, QDockWidget):
                                    target_dock = p
                            
                            if target_dock:
                                self._update_tab_tooltip(tab_bar, index, target_dock)
                                return target_dock
                except (AttributeError, RuntimeError): pass

            # 2. Strategy: Cross-referencing Registry with Title and Metadata
            tab_text = tab_bar.tabText(index)
            if not tab_text: return None
            
            # Search registry for a dock that matches this title
            for dock in self.mw.dock_manager.get_all_content_docks():
                if dock and not sip.isdeleted(dock) and dock.windowTitle() == tab_text:
                    if claimed_docks is not None and dock in claimed_docks: continue
                    
                    self._update_tab_tooltip(tab_bar, index, dock)
                    logger.debug(f"TabManager: Resolved dock '{dock.windowTitle()}' via Strategy 2 (Title Match)")
                    return dock
            
            logger.debug(f"TabManager: Strategy 2 failed (exact match) for '{tab_text}'. Trying Strategy 3 (Fuzzy/Intentional)...")

            # 3. Strategy: Fuzzy/Intentional Title Match (v16.5)
            # Important because Strategy 2 fails if the tab has " (2)" suffix but registry title doesn't yet sync
            import re
            clean_tab_text = re.sub(r" \((\d+)\)$", "", tab_text).strip()
            
            for dock in self.mw.dock_manager.get_all_content_docks():
                if dock and not sip.isdeleted(dock):
                    if claimed_docks is not None and dock in claimed_docks: continue
                    
                    # Check intentional title property first
                    intentional = dock.property("vnn_intentional_title")
                    if intentional and intentional == clean_tab_text:
                        logger.debug(f"TabManager: Resolved dock via Strategy 3 (Intentional Property): {intentional}")
                        self._update_tab_tooltip(tab_bar, index, dock)
                        return dock
                    
                    # Fuzzy match on current window title
                    curr_title = dock.windowTitle()
                    clean_curr = re.sub(r" \((\d+)\)$", "", curr_title).strip()
                    if clean_curr == clean_tab_text:
                        logger.debug(f"TabManager: Resolved dock via Strategy 3 (Fuzzy Title Match): {curr_title}")
                        self._update_tab_tooltip(tab_bar, index, dock)
                        return dock

            logger.error(f"TabManager: FAILED to resolve dock for tab '{tab_text}' at index {index}")
        except Exception as e:
            logger.error(f"TabManager error in _get_dock_at_index: {e}")
            import traceback
            logger.error(traceback.format_exc())
        return None

    def _update_tab_tooltip(self, tab_bar, index, dock):
        """Enhances tab tooltips with rich folder and content context."""
        try:
            if sip.isdeleted(tab_bar) or sip.isdeleted(dock): return
            
            obj_name = dock.objectName()
            if obj_name.startswith("NoteDock_") and hasattr(self.mw, 'note_service'):
                note = self.mw.note_service.get_note_by_id(obj_name)
                if note:
                    folder = note.get("folder", "General")
                    title = note.get("title", "Note")
                    # Rich tooltip content
                    tooltip = f"Title: {title}\nFolder: {folder}\nID: {obj_name}"
                    tab_bar.setTabToolTip(index, tooltip)
                    return
            
            tab_bar.setTabToolTip(index, dock.windowTitle())
        except Exception as e:
            logger.error(f"TabManager error: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def on_tab_changed(self, tab_bar, index):
        """Called when a tab is selected."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            logger.debug(f"TabManager: on_tab_changed triggered for index {index}")
            target_dock = self._get_dock_at_index(tab_bar, index)
            if target_dock and not sip.isdeleted(target_dock):
                widget = target_dock.widget()
                if widget and not sip.isdeleted(widget):
                    if isinstance(widget, NotePane):
                        logger.debug(f"TabManager: Setting active pane to {target_dock.windowTitle()} (Forcing Sidebar Sync)")
                        self.mw.set_active_pane(widget, dock=target_dock, force_sync=True)
                        
                        # Plan v2.5: Only focus editor if a TabBar DOES NOT have focus.
                        # This is the most reliable way to ensure we don't steal focus after a click.
                        from PyQt6.QtWidgets import QTabBar
                        focused = QApplication.focusWidget()
                        if not isinstance(focused, QTabBar):
                            widget.setFocus() 
                else:
                    logger.debug(f"TabManager: Target dock {target_dock.objectName()} has no valid widget.")
            else:
                logger.debug(f"TabManager: Could not resolve dock for index {index}")
        except (RuntimeError, Exception) as e:
            logger.error(f"TabManager: on_tab_changed error: {e}")

    def _on_tab_moved(self, from_idx, to_idx, tab_bar):
        """Called when a tab is rearranged â€” triggers title re-numbering (1, 2, 3...)"""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            if hasattr(self.mw, 'dock_manager'):
                # Force a refresh of all note titles to match new visual order
                self.mw.dock_manager.refresh_all_note_titles()
        except Exception: pass

    def eventFilter(self, watched, event):
        """Intercepts Tab/Shift+Tab keys on the TabBar to cycle tabs."""
        from PyQt6.QtWidgets import QTabBar
        from PyQt6.QtCore import QEvent
        
        if isinstance(watched, QTabBar):
            # Plan v16.4: Intercept Context Menu directly to guarantee it survives 
            # Qt's internal signal droppings when docks are rearranged.
            if event.type() == QEvent.Type.ContextMenu:
                self.on_tab_context_menu(watched, event.pos())
                return True

            # Plan v2.5: Capture focus on click (tab or bar)
            if event.type() == QEvent.Type.MouseButtonPress:
                watched.setFocus()
                return False # Let QTabBar handle selection
                
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                modifiers = event.modifiers()
                
                # Plan v15.6: If Control is pressed, we no longer intercept here.
                # The user wants PLAIN Tab for switching when the TabBar is focused.
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    return False

                # Use standard int() comparison for maximum PyQt version compatibility
                if key == int(Qt.Key.Key_Tab):
                    count = watched.count()
                    if count > 1:
                        new_idx = (watched.currentIndex() + 1) % count
                        watched.setCurrentIndex(new_idx)
                        # CRITICAL: Keep focus on TabBar for sequential Tab-switching
                        watched.setFocus()
                    return True # Consume Tab key
                elif key == int(Qt.Key.Key_Backtab): # Shift+Tab
                    count = watched.count()
                    if count > 1:
                        new_idx = (watched.currentIndex() - 1 + count) % count
                        watched.setCurrentIndex(new_idx)
                        # CRITICAL: Keep focus on TabBar for sequential Tab-switching
                        watched.setFocus()
                    return True # Consume Shift+Tab

        return super().eventFilter(watched, event)

    def switch_to_next_tab(self):
        """Global shortcut handler to switch to the next tab in the active area."""
        logger.debug("TabManager: Triggering Next Tab")
        self._switch_tab_relative(1)

    def switch_to_previous_tab(self):
        """Global shortcut handler to switch to the previous tab in the active area."""
        logger.debug("TabManager: Triggering Previous Tab")
        self._switch_tab_relative(-1)

    def _switch_tab_relative(self, offset):
        """Helper to switch tabs relative to the currently active one."""
        try:
            from PyQt6.QtWidgets import QTabBar
            
            # Strategy 1: Use the explicitly tracked active dock
            active_dock = self.mw._active_dock
            
            # Strategy 2: If no active dock, check which widget has focus
            focused_widget = QApplication.focusWidget()
            
            # Find all tabbars
            tabbars = self.mw.findChildren(QTabBar)
            if not tabbars:
                logger.debug("TabManager: No tab bars found in window.")
                return

            target_tab_bar = None
            current_idx = -1

            # Search for the tab bar containing the active dock or focused widget
            for tab_bar in tabbars:
                if sip.isdeleted(tab_bar): continue
                
                # Check if this tab bar contains our active dock
                if active_dock and not sip.isdeleted(active_dock):
                    for i in range(tab_bar.count()):
                        dock = self._get_dock_at_index(tab_bar, i)
                        if dock == active_dock:
                            target_tab_bar = tab_bar
                            current_idx = i
                            break
                
                if target_tab_bar: break

                # Fallback: Check if the focused widget is inside the same docking area as this tab bar
                # We check if the tab bar's ancestor is a common parent of the focused widget.
                is_related = False
                if focused_widget:
                    if tab_bar.isAncestorOf(focused_widget):
                        is_related = True
                    else:
                        # Check shared top-level window hierarchy
                        tp = tab_bar.parentWidget()
                        fp = focused_widget.parentWidget()
                        # Typical QDockWidget setup: TabBar and DockWidget share a parent in the layout
                        if tp and fp and tp == fp:
                            is_related = True
                
                if is_related:
                    target_tab_bar = tab_bar
                    current_idx = tab_bar.currentIndex()
                    logger.debug(f"TabManager: Identified target tab bar via focus relation to {type(focused_widget).__name__}")
                    break

            # If still nothing, use the first visible tab bar
            if not target_tab_bar:
                for tab_bar in tabbars:
                    if not sip.isdeleted(tab_bar) and tab_bar.isVisible():
                        target_tab_bar = tab_bar
                        current_idx = tab_bar.currentIndex()
                        logger.debug("TabManager: Falling back to first visible TabBar")
                        break

            if target_tab_bar and current_idx != -1:
                count = target_tab_bar.count()
                if count > 1:
                    new_idx = (current_idx + offset + count) % count
                    logger.debug(f"TabManager: Switching tab to index {new_idx}")
                    target_tab_bar.setCurrentIndex(new_idx)
                else:
                    logger.debug("TabManager: Target tab bar only has 1 tab.")
            else:
                logger.debug("TabManager: Could not identify target tab bar.")

        except Exception as e:
            logger.error(f"TabManager: Error switching tabs: {e}")

    def on_tab_double_clicked(self, tab_bar, index):
        """Called when a tab is double-clicked â€” opens rename dialog."""
        try:
            if not tab_bar or sip.isdeleted(tab_bar): return
            dock = self._get_dock_at_index(tab_bar, index)
            if dock and not sip.isdeleted(dock):
                self.mw.dialog_manager.show_rename_dialog(dock)
        except Exception as e:
            logger.error(f"TabManager error: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # â”€â”€ Close / Reopen support â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
        except Exception as e:
            logger.error(f"TabManager error: {e}")
            import traceback
            logger.error(traceback.format_exc())

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
        except Exception as e:
            logger.error(f"TabManager error: {e}")
            import traceback
            logger.error(traceback.format_exc())

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
        except Exception as e:
            logger.error(f"TabManager error: {e}")
            import traceback
            logger.error(traceback.format_exc())

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
        except Exception as e:
            logger.error(f"TabManager error: {e}")
            import traceback
            logger.error(traceback.format_exc())
