import logging

from PyQt6.QtWidgets import QDockWidget, QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from src.features.notes.note_pane import NotePane

logger = logging.getLogger(__name__)


class TabManager:
    """
    Manages tab bar hooks, context menus, close/close-others/close-all,
    tab-to-dock mapping, and tab selection/rename interactions.
    """

    def __init__(self, main_window):
        self.mw = main_window
        self._hooked_tabbars = set()
        self._closed_tabs_stack = []  # Stack of {title, content, obj_name}

    def hook_tab_bars(self):
        """Finds all QTabBars in the window and connects to their signals."""
        from PyQt6.QtWidgets import QTabBar

        for tab_bar in self.mw.findChildren(QTabBar):
            # Force tooltips to be the full tab text (for truncated tabs)
            for i in range(tab_bar.count()):
                text = tab_bar.tabText(i)
                if tab_bar.tabToolTip(i) != text:
                    tab_bar.setTabToolTip(i, text)

            if tab_bar not in self._hooked_tabbars:
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

                self._hooked_tabbars.add(tab_bar)

    def on_tab_close_requested(self, tab_bar, index):
        """Called when the (x) button on a tab is clicked."""
        self.close_dock_at_tab_index(tab_bar, index)

    def on_tab_context_menu(self, tab_bar, pos):
        """Shows right-click menu for tabs."""
        index = tab_bar.tabAt(pos)
        menu = QMenu(self.mw)

        if index >= 0:
            rename_act = QAction("Rename Note", self.mw)
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

    def get_docks_in_tab_order(self, tab_bar):
        """
        Returns a list of QDockWidgets corresponding to the tabs in the given tab_bar.
        Uses activation-based mapping to handle duplicate titles correctly.
        """
        tab_count = tab_bar.count()
        if tab_count == 0:
            return []

        # 1. Identify valid dock groups
        candidates = []
        checked_docks = set()

        for dock in self.mw.findChildren(QDockWidget):
            if dock.objectName() == "SidebarDock":
                continue
            if dock in checked_docks:
                continue

            siblings = self.mw.tabifiedDockWidgets(dock)
            group = [dock] + siblings
            for d in group:
                checked_docks.add(d)

            if len(group) == tab_count:
                candidates.append(group)

        if not candidates:
            return []

        # 2. Filter by title profile
        tab_titles = sorted([tab_bar.tabText(i) for i in range(tab_count)])

        strong_candidates = []
        for group in candidates:
            group_titles = sorted([d.windowTitle() for d in group])
            if group_titles == tab_titles:
                strong_candidates.append(group)

        if not strong_candidates:
            return []

        target_group = strong_candidates[0]

        # 3. Disambiguate by proximity
        if len(strong_candidates) > 1:
            try:
                min_dist = float('inf')
                best_group = strong_candidates[0]
                bar_center = tab_bar.mapToGlobal(tab_bar.rect().center())

                for group in strong_candidates:
                    vis = [d for d in group if d.isVisible()]
                    if vis:
                        d_center = vis[0].mapToGlobal(vis[0].rect().center())
                        dist = (abs(bar_center.x() - d_center.x()) +
                                abs(bar_center.y() - d_center.y()))
                        if dist < min_dist:
                            min_dist = dist
                            best_group = group
                target_group = best_group
            except Exception:
                pass

        # 4. Map Tab Index -> Dock Widget via Activation
        sorted_docks = [None] * tab_count
        original_index = tab_bar.currentIndex()

        try:
            self.mw.setUpdatesEnabled(False)

            for i in range(tab_count):
                tab_bar.setCurrentIndex(i)
                QApplication.processEvents()

                found_dock = None
                for dock in target_group:
                    if dock.isVisible() and not dock.visibleRegion().isEmpty():
                        found_dock = dock
                        break
                    elif dock.isVisible():
                        found_dock = dock

                sorted_docks[i] = found_dock

        except Exception as e:
            logger.error(f"Error mapping tabs: {e}")
        finally:
            if original_index >= 0:
                tab_bar.setCurrentIndex(original_index)
            QApplication.processEvents()
            self.mw.setUpdatesEnabled(True)

        return sorted_docks

    def close_all_tabs(self, tab_bar):
        """Closes all tabs in the given tab bar."""
        docks = self.get_docks_in_tab_order(tab_bar)
        for dock in docks:
            if dock:
                self._close_specific_dock(dock)

    def close_other_tabs(self, tab_bar, current_index):
        """Closes all tabs except the one at current_index."""
        docks = self.get_docks_in_tab_order(tab_bar)
        if current_index < 0 or current_index >= len(docks):
            return

        for i, dock in enumerate(docks):
            if i != current_index and dock:
                self._close_specific_dock(dock)

    def _close_specific_dock(self, dock):
        """Helper to close a specific dock instance."""
        self._save_closed_tab_info(dock)
        try:
            if dock.widget() == self.mw.active_pane:
                self.mw.set_active_pane(None)
            dock.close()
            dock.deleteLater()
        except RuntimeError:
            pass
        self.mw.save_app_state()
        self.mw.update_branding_visibility()

    def close_dock_at_tab_index(self, tab_bar, index):
        """Helper to find and remove a dock widget by its tab index."""
        title = tab_bar.tabText(index)
        dock_to_close = None

        for dock in self.mw.findChildren(QDockWidget):
            try:
                if (dock.windowTitle() == title and
                        not dock.isFloating() and
                        dock.objectName() != "SidebarDock"):
                    dock_to_close = dock
                    break
            except RuntimeError:
                continue

        if dock_to_close:
            self._save_closed_tab_info(dock_to_close)
            try:
                if dock_to_close.widget() == self.mw.active_pane:
                    self.mw.set_active_pane(None)
            except RuntimeError:
                self.mw.set_active_pane(None)

            try:
                dock_to_close.close()
                dock_to_close.deleteLater()
            except RuntimeError:
                pass

            self.mw.save_app_state()
            self.mw.update_branding_visibility()

    def on_tab_changed(self, tab_bar, index):
        """Called when a tab is selected."""
        title = tab_bar.tabText(index)
        for dock in self.mw.findChildren(QDockWidget):
            if dock.windowTitle() == title and not dock.isFloating():
                widget = dock.widget()
                if isinstance(widget, NotePane):
                    self.mw.set_active_pane(widget)
                else:
                    self.mw.set_active_pane(None)
                break

    def on_tab_double_clicked(self, tab_bar, index):
        """Called when a tab is double-clicked — opens rename dialog."""
        title = tab_bar.tabText(index)
        for dock in self.mw.findChildren(QDockWidget):
            if dock.windowTitle() == title and not dock.isFloating():
                self.mw.dialog_manager.show_rename_dialog(dock)
                return

    # ── Close / Reopen support ────────────────────────────────────────

    def _save_closed_tab_info(self, dock):
        """Snapshot the dock's title, content, and obj_name before it's deleted."""
        try:
            widget = dock.widget()
            content = ""
            if isinstance(widget, NotePane):
                content = widget.toHtml()
            info = {
                "title": dock.windowTitle(),
                "content": content,
                "obj_name": dock.objectName(),
            }
            self._closed_tabs_stack.append(info)
            # Keep a max of 20 entries
            if len(self._closed_tabs_stack) > 20:
                self._closed_tabs_stack.pop(0)
        except RuntimeError:
            pass

    def close_active_tab(self):
        """Close the currently active tab/dock (Ctrl+W)."""
        if not self.mw.active_pane:
            return
        # Find the dock that owns the active pane
        for dock in self.mw.findChildren(QDockWidget):
            try:
                if dock.widget() == self.mw.active_pane and dock.objectName() != "SidebarDock":
                    self._save_closed_tab_info(dock)
                    self.mw.set_active_pane(None)
                    dock.close()
                    dock.deleteLater()
                    self.mw.save_app_state()
                    self.mw.update_branding_visibility()
                    return
            except RuntimeError:
                continue

    def reopen_last_closed_tab(self):
        """Reopen the most recently closed tab (Ctrl+Shift+E)."""
        if not self._closed_tabs_stack:
            return
        info = self._closed_tabs_stack.pop()
        self.mw.dock_manager.add_note_dock(
            content=info["content"],
            title=info["title"],
            obj_name=info["obj_name"],
        )

