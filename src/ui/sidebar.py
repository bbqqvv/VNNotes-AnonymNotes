import html as html_module
import logging
import os
import re
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QMenu, QMessageBox, QLabel, QHBoxLayout, QFrame, QInputDialog, QToolBar, QLineEdit,
                             QDockWidget, QStyledItemDelegate, QApplication, QStyleOptionViewItem,
                             QTreeWidgetItemIterator, QPushButton, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QThread, QTimer, QRectF
from PyQt6.QtGui import QIcon, QFont, QAction, QTextDocument, QAbstractTextDocumentLayout, QPalette, QPainter, QColor
from PyQt6 import sip
from src.utils.ui_utils import get_icon, get_icon_dir
from src.ui.password_dialog import PasswordDialog

logger = logging.getLogger(__name__)

class HtmlItemDelegate(QStyledItemDelegate):
    """Renders tree items with HTML (for keyword highlighting in search results)."""
    
    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        
        painter.save()
        
        # 1. Prepare HTML Document
        doc = QTextDocument()
        doc.setDefaultFont(options.font)
        # CRITICAL: Remove default <p> tag top/bottom margins that Qt adds
        # when setHtml() is called. Without this, each item renders double-height.
        doc.setDocumentMargin(0)
        
        text = options.text
        if '<' in text and '>' in text:
            doc.setHtml(text)
        else:
            doc.setPlainText(text)
        
        # 2. Draw standard background and selection (WITHOUT TEXT)
        options.text = ""
        style = options.widget.style() if options.widget else QApplication.style()
        style.drawControl(style.ControlElement.CE_ItemViewItem, options, painter, options.widget)
        
        # 3. Calculate text rectangle
        text_rect = style.subElementRect(style.SubElement.SE_ItemViewItemText, options, options.widget)
        
        # 4. Use a very wide text width to prevent wrapping (single-line render)
        doc.setTextWidth(max(text_rect.width(), 9999))
        
        # 5. Draw HTML â€” clip strictly to text_rect to prevent bleeding
        painter.translate(text_rect.left(), text_rect.top())
        clip = QRectF(0, 0, text_rect.width(), text_rect.height())
        
        ctx = QAbstractTextDocumentLayout.PaintContext()
        if option.state & style.StateFlag.State_Selected:
            ctx.palette.setColor(QPalette.ColorRole.Text, option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.HighlightedText))
        else:
            ctx.palette.setColor(QPalette.ColorRole.Text, option.palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text))
        
        painter.setClipRect(clip)
        doc.documentLayout().draw(painter, ctx)
        painter.restore()
    
    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        
        doc = QTextDocument()
        doc.setDefaultFont(options.font)
        doc.setDocumentMargin(0)
        text = options.text
        if '<' in text and '>' in text:
            doc.setHtml(text)
        else:
            doc.setPlainText(text)
        doc.setTextWidth(9999)
        
        # Get base size from superclass if possible, or calculate from doc
        size = super().sizeHint(option, index)
        # Balanced vertical spacing: +4 for compact look (2px top/bottom)
        size.setHeight(max(size.height(), int(doc.size().height()) + 2))
        return size


class NoteTreeWidget(QTreeWidget):
    """Custom QTreeWidget that restricts drag-drop: notes can only be dropped onto folders."""

    def __init__(self, sidebar, parent=None):
        super().__init__(parent)
        self._sidebar = sidebar

    def dropEvent(self, event):
        target_item = self.itemAt(event.position().toPoint())
        source_item = self.currentItem()

        if source_item and target_item:
            source_data = source_item.data(0, Qt.ItemDataRole.UserRole)
            target_data = target_item.data(0, Qt.ItemDataRole.UserRole)

            # Only allow: note â†’ folder. Block note â†’ note, or anything else.
            if source_data and target_data:
                if source_data.get("type") == "note" and target_data.get("type") == "folder":
                    new_folder = target_data["name"]
                    note_obj_name = source_data["obj_name"]
                    if self._sidebar.note_service.move_note(note_obj_name, new_folder):
                        self._sidebar.note_service.save_to_disk()
                    self._sidebar.refresh_tree()
                    event.accept()
                    return

            # Block all other drops (noteâ†’note, etc.)
            event.ignore()
            return

        # If dropping outside any item (e.g. rearranging within same folder visual), ignore
        event.ignore()



class NoteSearchThread(QThread):
    results_found = pyqtSignal(list)
    
    def __init__(self, note_service, query):
        super().__init__()
        self.note_service = note_service
        self.query = query
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
        
    def run(self):
        results = self.note_service.search_notes(
            self.query,
            cancel_check=lambda: self._cancelled
        )
        if not self._cancelled:
            self.results_found.emit(results)

class SidebarWidget(QWidget):
    """
    Sidebar for managing folders and tags.
    Acts as a 'Note Explorer'.
    """
    note_selected = pyqtSignal(str) # Emits note obj_name
    folder_selected = pyqtSignal(str) # Emits folder name
    note_renamed = pyqtSignal(str, str) # obj_name, new_title
    note_deleted = pyqtSignal(str) # obj_name
    search_result_picked = pyqtSignal(str, str, int) # obj_name, query, line
    
    def __init__(self, note_service, parent=None):
        super().__init__(parent)
        self.main_window = parent
        # SENIOR ARCHITECTURE: Use Preferred width to protect user-dragged size
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.note_service = note_service
        
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300) # 300ms debounce
        self.search_timer.timeout.connect(lambda: self.start_search())
        
        self.current_search_thread = None
        self._last_search_results = None  # Cache search results for theme changes
        
        # SENIOR MEMORY: Load last stable width from config
        self._last_stable_width = self.main_window.config.get_value("window/sidebar_width", 250)
        try:
            self._last_stable_width = int(self._last_stable_width)
        except (ValueError, TypeError):
            self._last_stable_width = 250
        
        # Senior Magnet: Snapping & Release Detection
        self._is_snapping = False
        self._pending_collapse = False
        self._in_resize_logic = False
        
        self.setup_ui()
        self._note_item_map = {} # O(1) Mapping for Diamond-Standard performance
        # Senior Fix: Delayed tree refresh to prevent startup flood
        QTimer.singleShot(2000, self.refresh_tree)
        
    def sizeHint(self):
        """Native Qt: The ultimate source of truth for 'NguyÃªn tráº¡ng' width."""
        if self._is_snapping:
            return QSize(0, 0)
        return QSize(int(self._last_stable_width), 600)

    def minimumSizeHint(self):
        """Lock in the stable minimum floor."""
        return QSize(80, 100)

    # Removed custom paintEvent to let standard Qt/QSS handle background
        
    def setup_ui(self):
        # 1. Initialize Tree FIRST
        self.tree = NoteTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(15)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.setObjectName("SidebarTree")
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setVerticalScrollMode(QTreeWidget.ScrollMode.ScrollPerPixel)
        
        # HTML delegate for keyword highlighting in search results (Plan v8.18: Disabled for stability)
        # self._html_delegate = HtmlItemDelegate(self.tree)

        # 2. Setup Layouts
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4) # Add small breathing room between search/header/tree
        
        # 3. Header & Toolbar
        header_frame = QFrame()
        header_frame.setObjectName("SidebarHeader")
        header_frame.setMinimumHeight(40) # Tighter for a compact, balanced look
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(6, 0, 4, 0)
        
        title_label = QLabel("EXPLORER")
        title_label.setObjectName("SidebarTitle")
        title_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(14, 14)) # Larger for better contrast
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.toolbar.setStyleSheet("""
            QToolBar { 
                background: transparent; 
                border: none; 
                spacing: 0px;
            }
            QToolBar QToolButton {
                margin: 0px;
                padding: 1px;
                min-width: 20px;
                min-height: 20px;
            }
        """)
        
        # Actions (icons handled by update_toolbar_icons)
        self.update_toolbar_icons()
        
        header_layout.addWidget(self.toolbar)
        
        layout.addWidget(header_frame)
        
        # 4. Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search notes (Ctrl+Shift+F)...")
        self.search_bar.setObjectName("SidebarSearch")
        self.search_bar.textChanged.connect(lambda: self.search_timer.start())
        self.search_bar.hide()
        layout.addWidget(self.search_bar)
        
        self.search_status = QLabel("")
        self.search_status.setObjectName("SearchStatus")
        self.search_status.setStyleSheet("""
            QLabel#SearchStatus { 
                color: #569CD6; 
                font-size: 11px; 
                font-weight: 500;
                margin-left: 10px; 
                margin-bottom: 5px;
            }
        """)
        self.search_status.hide()
        layout.addWidget(self.search_status)
        
        layout.addWidget(self.tree)
        
    def showEvent(self, event):
        """Ensure layout is recalculated once shown."""
        super().showEvent(event)
        self.tree.updateGeometry()
        if self.tree.viewport():
            self.tree.viewport().update()

    def restore_stable_width(self):
        """Forcefully resets the sidebar to its last known good width."""
        try:
            sd = getattr(self.main_window, 'sidebar_dock', None)
            if sd and hasattr(self, '_last_stable_width'):
                target_w = int(self._last_stable_width)
                # HARD PIN: Temporarily allow any size to ensure the snap works
                sd.setMinimumWidth(0)
                self.main_window.resizeDocks([sd], [target_w], Qt.Orientation.Horizontal)
                # Restore standard minimum after snap
                if target_w >= 180:
                    sd.setMinimumWidth(80)
                    logging.debug(f"Sidebar: Forcefully restored to stable width: {target_w}px")
        except Exception as e:
            logging.error(f"Sidebar: restore_stable_width failed: {e}")

    def resizeEvent(self, event):
        """Standard resize handling with strict persistence rules."""
        try:
            super().resizeEvent(event)
        except Exception: return
        
        current_width = event.size().width()

        # Guard against recursive resize calls or invalid states
        if self._in_resize_logic or self.main_window._is_restoring or self._is_snapping:
            return
            
        self._in_resize_logic = True
        try:
            is_dragging = QApplication.mouseButtons() & Qt.MouseButton.LeftButton
            sd = getattr(self.main_window, 'sidebar_dock', None)
            
            if is_dragging:
                if sd:
                    if current_width < 180:
                        # 1. Visual Snap (The "HÃ­t" Feel)
                        if not self._pending_collapse:
                            self._pending_collapse = True
                            sd.setMinimumWidth(0)
                        self.main_window.resizeDocks([sd], [0], Qt.Orientation.Horizontal)
                        
                        if hasattr(self.main_window, '_sidebar_watchdog') and not self.main_window._sidebar_watchdog.isActive():
                            self.main_window._sidebar_watchdog.start()
                        return
                            
                    elif current_width >= 180:
                        # 2. Manual Update: Only learn new width during ACTIVE drag
                        self._last_stable_width = current_width
                        self.main_window.config.set_value("window/sidebar_width", current_width)
                        
                        if self._pending_collapse:
                            self._pending_collapse = False
                            sd.setMinimumWidth(80)
                            sd.setMaximumWidth(600)
            else:
                # 3. Passive Resize: Ignore for configuration, reset pending flags
                self._pending_collapse = False
        finally:
            self._in_resize_logic = False

    # Removed _check_mouse_release: MainWindow now handles this via eventFilter for safety.

    def _do_auto_collapse(self):
        """Cleanly collapses the sidebar. Safe to call instantly thanks to removeDockWidget."""
        try:
            if hasattr(self.main_window, 'sidebar_dock'):
                sd = self.main_window.sidebar_dock
                if sd.isVisible():
                    # Execute Nuclear Excision instantly
                    self.main_window.toggle_sidebar()
        except RuntimeError:
            pass

    def _get_is_dark(self):
        """Helper to check if dark mode is active."""
        if hasattr(self.main_window, 'theme_manager'):
            return self.main_window.theme_manager.is_dark_mode
        return True

    def _get_base_icon_path(self):
        """Helper to get icon path based on current theme via ui_utils."""
        return get_icon_dir(self._get_is_dark())

    def update_toolbar_icons(self):
        self.toolbar.clear()
        is_dark = self._get_is_dark()
        
        new_note_act = QAction(get_icon("note-add.svg", is_dark), "New Note", self)
        new_note_act.setToolTip("New Note")
        new_note_act.triggered.connect(lambda: self.add_new_note())
        self.toolbar.addAction(new_note_act)
        
        new_folder_act = QAction(get_icon("folder-add.svg", is_dark), "New Folder", self)
        new_folder_act.setToolTip("New Folder")
        new_folder_act.triggered.connect(self.add_new_folder)
        self.toolbar.addAction(new_folder_act)
        
        refresh_act = QAction(get_icon("refresh.svg", is_dark), "Refresh", self)
        refresh_act.setToolTip("Refresh List")
        refresh_act.triggered.connect(self.refresh_tree)
        self.toolbar.addAction(refresh_act)
        
        collapse_act = QAction(get_icon("collapse-all.svg", is_dark), "Collapse All", self)
        collapse_act.setToolTip("Collapse All Folders")
        collapse_act.triggered.connect(self.tree.collapseAll) 
        self.toolbar.addAction(collapse_act)

    def toggle_search(self):
        """Toggles the visibility of the search bar."""
        is_visible = self.search_bar.isVisible()
        self.search_bar.setVisible(not is_visible)
        if not is_visible:
            self.search_bar.setFocus()
            self.search_bar.selectAll()
        else:
            self.search_bar.clear() # Clear search when hiding
            self.search_status.hide()
            self._last_search_results = None  # Clear cache
            self.tree.setItemDelegate(QStyledItemDelegate(self.tree))  # Reset to default
            self.refresh_tree()
            self.tree.setFocus()

    def update_note_title(self, obj_name, new_title):
        """DIAMOND OPTIMIZATION: Instant O(1) update using internal mapping."""
        item = self._note_item_map.get(obj_name)
        if item:
            try:
                item.setText(0, new_title)
                return
            except RuntimeError:
                # Item's C++ object was deleted (e.g. sidebar is in search mode
                # and tree.clear() was called). Remove stale reference.
                self._note_item_map.pop(obj_name, None)

        # Fallback: walk the tree (rare â€” only if map is stale)
        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            i = it.value()
            try:
                data = i.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("type") == "note" and data.get("obj_name") == obj_name:
                    i.setText(0, new_title)
                    self._note_item_map[obj_name] = i  # Re-cache
                    return
            except RuntimeError:
                pass
            it += 1


    def refresh_tree(self):
        # If search is active, skip refresh â€” CSS applies automatically
        if self.search_bar.isVisible() and self.search_bar.text().strip():
            return
        
        # Reset HTML delegate to default for normal tree display
        self.tree.setItemDelegate(QStyledItemDelegate(self.tree))
        
        # Capture current expansion states before clear
        expanded_folders = set()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "folder" and item.isExpanded():
                expanded_folders.add(data.get("name"))
        
        self.tree.blockSignals(True)
        self.tree.clear()
        self._note_item_map.clear() # Reset mapping
        
        is_dark = self._get_is_dark()
        folder_icon = get_icon("folder-open.svg", is_dark)
        note_icon = get_icon("note.svg", is_dark)
        pin_icon = get_icon("pin.svg", is_dark)
        lock_icon_small = get_icon("lock.svg", is_dark)
        
        # 1. Pinned Notes Section
        pinned_notes = self.note_service.get_pinned_notes()
        if pinned_notes:
            pin_folder = QTreeWidgetItem(self.tree)
            pin_folder.setText(0, f"Pinned ({len(pinned_notes)})")
            pin_folder.setIcon(0, pin_icon)
            pin_folder.setData(0, Qt.ItemDataRole.UserRole, {"type": "pinned_folder"})
            pin_folder.setExpanded(True)
            font = pin_folder.font(0)
            font.setBold(True)
            pin_folder.setFont(0, font)
            
            for note in pinned_notes:
                obj_name = note.get("obj_name")
                item = QTreeWidgetItem(pin_folder)
                item.setText(0, note.get("title", "Untitled"))
                
                # Check for lock icon
                if note.get("is_locked"):
                    item.setIcon(0, lock_icon_small)
                else:
                    item.setIcon(0, note_icon)
                    
                item.setData(0, Qt.ItemDataRole.UserRole, {"type": "note", "obj_name": obj_name, "pinned": True})
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsEditable)
                # Tooltip: Contextual path for pinned notes
                folder_name = note.get("folder", "General")
                item.setToolTip(0, note.get('title', 'Note'))
                self._note_item_map[obj_name] = item # Cache for O(1) sync

        notes = self.note_service.get_notes()
        
        config_structure = self._group_notes_by_folder(notes)
        
        # Sort folders (General first, then alphabetical)
        sorted_folders = sorted(config_structure.keys())
        if "General" in sorted_folders:
             sorted_folders.remove("General")
             sorted_folders.insert(0, "General")
             
        for folder in sorted_folders:
            folder_notes = config_structure[folder]
            note_count = len(folder_notes)
            
            # Use name directly since it was sanitized before grouping
            clean_name = folder
            
            folder_item = QTreeWidgetItem(self.tree)
            folder_item.setText(0, f"{clean_name} ({note_count})") 
            
            # Check if fold is locked
            is_locked = self.note_service.is_folder_locked(folder)
            if is_locked:
                folder_item.setIcon(0, lock_icon_small)
            else:
                folder_item.setIcon(0, folder_icon)
                
            folder_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": clean_name})
            
            # Restore expansion state (prevent expansion if locked)
            if is_locked:
                folder_item.setExpanded(False)
            elif clean_name in expanded_folders or clean_name == "Pinned":
                folder_item.setExpanded(True)
            else:
                folder_item.setExpanded(False)
                
            folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable)
            folder_item.setFlags(folder_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled) 
            
            font = folder_item.font(0)
            font.setBold(True)
            font.setPointSize(9)
            folder_item.setFont(0, font)
            
            if is_locked:
                continue # Skip adding child items for a locked folder
                
            # Use folder_notes which we calculated above
            for note in folder_notes:
                obj_name = note.get("obj_name")
                note_item = QTreeWidgetItem(folder_item)
                note_title = note.get("title", "Untitled")
                note_item.setText(0, note_title) # No emoji
                
                # Check for lock icon
                if note.get("is_locked"):
                    note_item.setIcon(0, lock_icon_small)
                else:
                    note_item.setIcon(0, note_icon)

                note_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "note", "obj_name": obj_name})
                # Tooltip: Descriptive context for standard folders
                snippet = note.get("content", "")[:100].replace("\n", " ").strip()
                note_item.setToolTip(0, f"Preview: {snippet}...")
                self._note_item_map[obj_name] = note_item # Cache for O(1) sync
                
                # Enable Drag & EDITING
                note_item.setFlags(note_item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsEditable)
                note_item.setFlags(note_item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
                
                # Professional styling: lighter weight for note items
                note_font = note_item.font(0)
                note_font.setPointSize(9)
                note_item.setFont(0, note_font)

        # â”€â”€ Browser docks section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._add_browser_section()
        self.tree.blockSignals(False)
        
        # FIX: Force immediate layout recalculation to ensure scrollbars appear correctly
        self.tree.updateGeometry()
        if self.tree.viewport():
            self.tree.viewport().update()
            
        # Root Cause Fix: Explicitly check scrollbar visibility
        vsb = self.tree.verticalScrollBar()
        if vsb:
            vsb.update()
            
        # Nudge: Final safety for slow rendering monitors
        QTimer.singleShot(150, lambda: self.tree.updateGeometry())

    def _add_browser_section(self):
        """Add a 'Browsers' folder showing all open BrowserPane docks."""
        base_icon_path = self._get_base_icon_path() # Still needed for some local logic if any, but let's try to remove param
        if not self.main_window:
            return
        browser_docks = []
        all_docks = self.main_window.findChildren(QDockWidget)
        logging.debug(f"[Sidebar] _add_browser_section: found {len(all_docks)} total docks")
        for dock in all_docks:
            try:
                if sip.isdeleted(dock):
                    continue
                obj = dock.objectName()
                logging.debug(f"[Sidebar]   dock: {obj}")
                if obj == "SidebarDock" or not obj.startswith("BrowserDock_"):
                    continue
                browser_docks.append(dock)
            except RuntimeError: continue

        logging.debug(f"[Sidebar] browser_docks count: {len(browser_docks)}")
        if not browser_docks:
            return

        is_dark = self._get_is_dark()
        browser_icon = get_icon("browser.svg", is_dark)
        folder_icon = get_icon("browser.svg", is_dark)

        folder_item = QTreeWidgetItem(self.tree)
        folder_item.setText(0, "Browsers")
        folder_item.setIcon(0, folder_icon)
        folder_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "browser_folder"})
        folder_item.setExpanded(True)
        folder_item.setFlags(folder_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
        folder_item.setFlags(folder_item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
        folder_item.setFlags(folder_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        font = folder_item.font(0)
        font.setBold(True)
        folder_item.setFont(0, font)

        for dock in browser_docks:
            title = dock.windowTitle() or "Mini Browser"
            b_item = QTreeWidgetItem(folder_item)
            b_item.setText(0, title)
            b_item.setIcon(0, browser_icon)
            b_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "browser", "obj_name": dock.objectName()})
            b_item.setToolTip(0, title)
            b_item.setFlags(b_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
            b_item.setFlags(b_item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
            b_item.setFlags(b_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def _focus_browser_dock(self, obj_name):
        """Raise and focus the browser dock with the given object name."""
        if not self.main_window:
            return
        for dock in self.main_window.findChildren(QDockWidget):
            try:
                if not sip.isdeleted(dock) and dock.objectName() == obj_name:
                    dock.show()
                    dock.raise_()
                    dock.setFocus()
                    return
            except RuntimeError: continue

    def _rename_browser_dock(self, obj_name):
        """Show input dialog to rename a browser dock."""
        if not self.main_window:
            return
        for dock in self.main_window.findChildren(QDockWidget):
            try:
                if not sip.isdeleted(dock) and dock.objectName() == obj_name:
                    current_title = dock.windowTitle()
                    new_title, ok = QInputDialog.getText(
                        self, "Rename Browser", "New name:", text=current_title)
                    if ok and new_title.strip():
                        dock.setWindowTitle(new_title.strip())
                        dock.setToolTip(new_title.strip())
                        self.refresh_tree()
                    return
            except RuntimeError: continue

    def _close_browser_dock(self, obj_name):
        """Close a browser dock and delete its persistent data."""
        if not self.main_window:
            return
            
        # 1. Delete from service first
        if hasattr(self.main_window.ctx, 'browser'):
            self.main_window.ctx.browser.delete_browser(obj_name)
            
        # 2. Close the UI dock
        for dock in list(self.main_window.findChildren(QDockWidget)):
            if dock.objectName() == obj_name:
                try:
                    dock.close()
                except RuntimeError:
                    pass
                break
                
        # 3. Deferred refresh
        QTimer.singleShot(50, self.refresh_tree)

    def start_search(self):
        """Kicks off the background search thread."""
        query = self.search_bar.text().strip().lower()
        if not query:
            self.search_status.hide()
            self.refresh_tree()
            return
            
        # Cancel previous thread cleanly if still running
        if self.current_search_thread and self.current_search_thread.isRunning():
            self.current_search_thread.cancel()
            self.current_search_thread.wait(500)  # Wait up to 500ms for graceful exit
            
        self.search_status.setText("Searching...")
        self.search_status.show()
        
        # Immediate visual feedback: Clear tree or keep old results?
        # Better to keep tree but show "Searching..." label
        
        self.current_search_thread = NoteSearchThread(self.note_service, query)
        self.current_search_thread.results_found.connect(self.display_search_results)
        self.current_search_thread.start()

    def display_search_results(self, results):
        """Updates the UI with result list from background thread."""
        self._last_search_results = results  # Cache for theme-change re-display
        query = self.search_bar.text().strip()
        self.search_status.setText(f"Found {len(results)} note(s) matching '{query}'")
        
        # Clear tree to build search results
        self.tree.blockSignals(True)
        self.tree.clear()
        
        # Enable HTML rendering for keyword highlights
        self.tree.setItemDelegate(self._html_delegate)
        
        # Re-use icons
        is_dark = self._get_is_dark()
        note_icon = get_icon("note.svg", is_dark)
        folder_icon = get_icon("folder-open.svg", is_dark)
        # Snippet icon? Maybe a small dot or just text
        
        # Group by Folder for context
        # 1. First, group results by folder
        grouped_results = {}
        for res in results:
            note = res["note"]
            folder = note.get("folder", "General")
            if folder not in grouped_results:
                grouped_results[folder] = []
            grouped_results[folder].append(res)
            
        # 2. Build Tree
        for folder in sorted(grouped_results.keys()):
            folder_item = QTreeWidgetItem(self.tree)
            folder_item.setText(0, f"{folder}")
            folder_item.setIcon(0, folder_icon)
            folder_item.setExpanded(True)
            # Make folder items not selectable/actionable in search mode? Or keep standard?
            # Creating standard folder structure allows drag/drop even in search?
            # For now, simplistic rendering.
            
            for res in grouped_results[folder]:
                note = res["note"]
                matches = res["matches"]
                
                note_item = QTreeWidgetItem(folder_item)
                note_item.setText(0, note.get("title", "Untitled"))
                note_item.setIcon(0, note_icon)
                note_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "note", "obj_name": note.get("obj_name")})
                note_item.setExpanded(True)
                
                # Add Snippets as children with keyword highlighting
                for m in matches:
                    if m["type"] == "content":
                        snippet_item = QTreeWidgetItem(note_item)
                        # Highlight query keyword in snippet text
                        text = m['text']
                        # Add a visual cue to snippets
                        indent_cue = "â€¢ " 
                        highlighted_text = self._highlight_keyword(f"{indent_cue}{text}", query)
                        snippet_item.setText(0, highlighted_text)
                        
                        # Use a professional monospace-ish font for snippets
                        font = QFont("Consolas", 9) if sys.platform == "win32" else QFont("Monospace", 9)
                        font.setItalic(True)
                        snippet_item.setFont(0, font)
                        
                        snippet_item.setData(0, Qt.ItemDataRole.UserRole, {
                            "type": "snippet", 
                            "obj_name": note.get("obj_name"),
                            "line": m["line"]
                        })
                        snippet_item.setToolTip(0, m["text"])
                    elif m["type"] == "status":
                        status_item = QTreeWidgetItem(note_item)
                        status_item.setText(0, m["text"])
                        font = status_item.font(0)
                        font.setItalic(True)
                        status_item.setFont(0, font)

        self.tree.blockSignals(False)
        self.tree.updateGeometry()
        if self.tree.viewport():
            self.tree.viewport().update()
        QTimer.singleShot(100, lambda: self.tree.updateGeometry())

    def select_note(self, obj_name):
        """
        Highlights and scrolls to the specified note in the tree.
        Plan v12.7: Highlights BOTH pinned and folder instances.
        """
        if not obj_name:
            return

        # Plan v16.2: Removed the search_bar visibility guard.
        # This allows the sidebar to sync even if the search bar is open (e.g. empty search).
        # Selection will still fail silently if the specific item is filtered out by search.

        # 1. Block signals to prevent recursive "note_selected" triggers
        self.tree.blockSignals(True)
        self.tree.clearSelection()
        
        found_any = False
        
        # 2. Iterate all items (O(N) for select_note is acceptable for tab sync)
        # to find all instances (e.g. pinned + folder copy)
        from PyQt6.QtWidgets import QTreeWidgetItemIterator
        it = QTreeWidgetItemIterator(self.tree)
        logger.debug(f"[SYNC-TRACE] Sidebar.select_note: Searching for '{obj_name}'")
        while it.value():
            item = it.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            # PLAN V12.7 FIX: Data is a dict, extract 'obj_name'
            if isinstance(data, dict):
                item_obj_name = data.get("obj_name")
                if item_obj_name == obj_name:
                    logger.debug(f"[SYNC-TRACE] Sidebar.select_note: MATCH FOUND for '{obj_name}'")
                    item.setSelected(True)
                    # Expand parents
                    p = item.parent()
                    while p:
                        p.setExpanded(True)
                        p = p.parent()
                    
                    # Only scroll to the first one (usually folder copy, or pinned if top)
                    if not found_any:
                        self.tree.setCurrentItem(item)
                        # Use PositionAtCenter to ensure the note is not "stuck" at the top/bottom boundary
                        self.tree.scrollToItem(item, QTreeWidget.ScrollHint.PositionAtCenter)
                        found_any = True
            it += 1
            
        if not found_any:
            logger.debug(f"[SYNC-TRACE] Sidebar.select_note: NO MATCH found for '{obj_name}' after full iteration.")
        self.tree.blockSignals(False)

    def _highlight_keyword(self, text, keyword):
        """Wraps occurrences of keyword in the text with yellow highlight HTML."""
        if not keyword:
            return text
        safe_text = html_module.escape(text)
        safe_keyword = html_module.escape(keyword)
        
        # Case-insensitive replace with highlighted span
        # Pattern to replace keyword with highlight. Uses a high-contrast but rounded theme.
        pattern = re.compile(re.escape(safe_keyword), re.IGNORECASE)
        highlighted = pattern.sub(
            lambda m: f'<span style="background-color:#FFD700; color:#000000; border-radius:3px; padding:0px 2px;">{m.group()}</span>',
            safe_text
        )
        return highlighted

    def on_item_changed(self, item, column):
        """Handle item renaming."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data: return
        
        new_text = item.text(0)
        
        if data["type"] == "note":
            obj_name = data["obj_name"]
            actual_title = self.note_service.rename_note(obj_name, new_text)
            if actual_title:
                 # Plan v12.7: Update with potentially auto-numbered title
                 if actual_title != new_text:
                     item.setText(0, actual_title)
                 
                 # Sync to storage (Async)
                 self.note_service.save_to_disk()
                 # Emit signal so MainWindow can update Dock Title
                 # Emitting 'actual_title' ensures other components stay in sync
                 self.note_renamed.emit(obj_name, actual_title)
                 
        elif data["type"] == "folder":
            # Strip count suffix "(N)" from UI text to get the actual folder name
            clean_new_text = re.sub(r"\s\(\d+\)$", "", new_text)
            old_name = data["name"]
            if clean_new_text != old_name and clean_new_text.strip():
                if self.note_service.rename_folder(old_name, clean_new_text):
                    # Smart Update: Update internal data, don't rebuild tree
                    data["name"] = new_text
                    item.setData(0, Qt.ItemDataRole.UserRole, data)
                    
                    # Also update all children notes' internal folder data?
                    # NoteService already updated the backend models.
                    # The UI children don't store folder name in their data, 
                    # they rely on parent. So visually it's already done by rename.
                    
                    self.note_service.save_to_disk()
                    self.folder_selected.emit(new_text)

    def delete_selected_folder(self):
        """Deletes/Removes a folder with options."""
        item = self.tree.currentItem()
        if not item: return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "folder": return
        
        folder_name = data.get("name")
        if folder_name == "General":
            QMessageBox.warning(self, "Warning", "Cannot delete 'General' folder.")
            return

        # Improved Dialog with choices
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Folder")
        msg.setText(f"How do you want to delete folder '{folder_name}'?")
        msg.setIcon(QMessageBox.Icon.Question)
        
        move_btn = msg.addButton("Move notes to General", QMessageBox.ButtonRole.ActionRole)
        delete_btn = msg.addButton("Delete folder and all notes", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = msg.addButton(QMessageBox.StandardButton.Cancel)
        
        msg.exec()
        
        if msg.clickedButton() == move_btn:
            if self.note_service.rename_folder(folder_name, "General"):
                self.note_service.save_to_disk()
                self.refresh_tree()
        elif msg.clickedButton() == delete_btn:
            self.delete_all_notes_in_folder(folder_name)
            # Folder will be empty, NoteService doesn't track folders separately, 
            # so it disappears on next refresh if no notes exist.
            self.refresh_tree()

    def delete_all_notes_in_folder(self, folder_name):
        """Bulk deletes all notes in a folder."""
        # Security Check: Folder Lock
        is_locked = self.note_service.is_folder_locked(folder_name)
        if is_locked:
            is_dark = getattr(self.main_window.theme_manager, "is_dark_mode", True) if self.main_window else True
            pwd, ok = PasswordDialog.get_input(self, f"Folder Locked: {folder_name}", 
                                             "Enter folder password to delete all notes inside:", is_dark=is_dark)
            if not ok: return
            if not self.note_service.unlock_folder(folder_name, pwd):
                QMessageBox.warning(self, "Access Denied", "Incorrect folder password.")
                return

        confirm = QMessageBox.question(self, "Delete All Notes", 
                                       f"Are you sure you want to delete all notes in '{folder_name}'?\nThis cannot be undone.",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            deleted_ids = self.note_service.delete_notes_in_folder(folder_name)
            for obj_name in deleted_ids:
                self.note_deleted.emit(obj_name)
            
            self.note_service.save_to_disk()
            self.refresh_tree()


                
    def _group_notes_by_folder(self, notes):
        groups = {}
        for note in notes:
            folder = note.get("folder", "General")
            if folder not in groups:
                groups[folder] = []
            
            if note.get("is_placeholder"):
                continue
                
            groups[folder].append(note)
        return groups

    def on_item_clicked(self, item, column):
        """Handle single click to open note or browser. Ignore if multi-selecting."""
        # Senior Fix: If Ctrl or Shift is held, we are doing a multi-selection for batch operations.
        # Don't trigger a note load which would steal focus and break the selection flow.
        modifiers = QApplication.keyboardModifiers()
        if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data: return
        
        if data.get("type") == "note":
            self.note_selected.emit(data["obj_name"])
        elif data.get("type") == "snippet":
            # Pass the search query and line number for highlighting
            query = self.search_bar.text().strip()
            line = data.get("line", 0)
            self.search_result_picked.emit(data["obj_name"], query, line)
        elif data.get("type") == "browser":
            self._focus_browser_dock(data["obj_name"])

    def on_item_double_clicked(self, item, column):
        """Double click to rename if it's a note, or expand if folder."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and data.get("type") == "note":
            self.tree.editItem(item, 0)
        elif data and data.get("type") == "folder":
             # Toggle expand
             item.setExpanded(not item.isExpanded())

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts (e.g. Delete key)."""
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_items()
        else:
            super().keyPressEvent(event)

    def delete_selected_items(self):
        """Handles deletion of multiple selected notes/folders."""
        items = self.tree.selectedItems()
        if not items: return
        
        # Group by type
        notes = []
        folders = []
        browsers = []
        for item in items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if not data: continue
            if data["type"] == "note":
                notes.append((item, data["obj_name"]))
            elif data["type"] == "folder":
                folders.append((item, data["name"]))
            elif data["type"] == "browser":
                browsers.append((item, data["obj_name"]))
        
        if not notes and not folders and not browsers: return
        
        # Confirmation Message
        msg = "Are you sure you want to delete:\n"
        if notes: msg += f"- {len(notes)} note(s)\n"
        if browsers: msg += f"- {len(browsers)} browser(s)\n"
        if folders: msg += f"- {len(folders)} folder(s) (Notes will move to 'General')\n"
        
        confirm = QMessageBox.question(self, "Batch Delete", msg,
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm != QMessageBox.StandardButton.Yes: return
        
        # Execute Deletions
        # 1. Notes
        for item, obj_name in notes:
            # Security Check: Note Lock
            note_meta = self.note_service.get_note_by_id(obj_name)
            if note_meta and note_meta.get("is_locked"):
                is_dark = getattr(self.main_window.theme_manager, "is_dark_mode", True) if self.main_window else True
                pwd, ok = PasswordDialog.get_input(self, f"Note Locked: {note_meta.get('title')}", 
                                                 "This note is locked. Enter password to delete:", is_dark=is_dark)
                if not ok:
                    continue # Skip this note
                
                if not self.note_service.unlock_note(obj_name, pwd):
                    QMessageBox.warning(self, "Access Denied", f"Incorrect password for '{note_meta.get('title')}'. Skipping.")
                    continue

            if self.note_service.delete_note(obj_name):
                self.note_deleted.emit(obj_name)
                # Visual remove
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    index = self.tree.indexOfTopLevelItem(item)
                    self.tree.takeTopLevelItem(index)
        
        # 2. Folders
        for item, folder_name in folders:
            if folder_name == "General": continue # Protection
            if self.note_service.rename_folder(folder_name, "General"):
                # Folders move notes to general, so we refresh to be safe
                pass
        
        if folders:
            self.note_service.save_to_disk()
            self.refresh_tree()
        elif notes:
            self.note_service.save_to_disk()

        # 3. Browsers
        for item, obj_name in browsers:
            self._close_browser_dock(obj_name)
            
    def delete_selected_item(self):
        # Legacy fallback, redirect to batch logic
        self.delete_selected_items()

    def add_new_note(self, folder=None, is_open=1, is_placeholder=0):
        """Adds a new note. If folder is None, uses currently selected item's folder."""
        target_folder = folder
        
        # ... (rest of folder logic) ...
        if not target_folder:
            item = self.tree.currentItem()
            if item:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data:
                    if data.get("type") == "folder":
                        target_folder = data.get("name")
                    elif data.get("type") == "note":
                        # Find parent folder of the note
                        parent = item.parent()
                        if parent:
                            parent_data = parent.data(0, Qt.ItemDataRole.UserRole)
                            if parent_data and parent_data.get("type") == "folder":
                                target_folder = parent_data.get("name")
                            else:
                                target_folder = parent.text(0).split(' (')[0]
        
        if not target_folder:
            target_folder = "General"

        # Create new note via service
        note_data = self.note_service.add_note(
            title="New Note", 
            content="", 
            folder=target_folder, 
            is_open=is_open,
            is_placeholder=is_placeholder
        )
        self.note_service.save_to_disk()
        
        if is_open and self.main_window:
            # We call the MainWindow method which handles both UI (Dock) and Sidebar Refresh
            self.main_window.add_note_dock(
                obj_name=note_data["obj_name"], 
                title=note_data["title"], 
                content=""
            )
            # After refresh, highlight it
            self.select_note(note_data["obj_name"])
        else:
            # Background creation for folders
            self.refresh_tree()
            self.select_note(note_data["obj_name"])

    def add_new_folder(self):
        """Prompts user for folder name and creates a placeholder note in it."""
        folder_name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
        if ok and folder_name.strip():
            # 1. Create a hidden placeholder to ensure folder existence
            self.add_new_note(folder=folder_name.strip(), is_open=0, is_placeholder=1)
            # 2. Automatically create and open a default visible note for the user
            self.add_new_note(folder=folder_name.strip(), is_open=1, is_placeholder=0)
    def show_context_menu(self, position):
        items = self.tree.selectedItems()
        menu = QMenu()
        
        if len(items) > 1:
            # Batch Actions
            icon_path = os.path.join(self._get_base_icon_path(), "trash.svg")
            delete_act = QAction(QIcon(icon_path), f"Delete Selected ({len(items)})", self)
            delete_act.triggered.connect(self.delete_selected_items)
            menu.addAction(delete_act)
            
        elif len(items) == 1:
            item = items[0]
            self.tree.setCurrentItem(item)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            item_type = data.get("type")
            
            base_icon_path = self._get_base_icon_path()
            
            if item_type == "pinned_folder":
                unpin_all_act = QAction(QIcon(os.path.join(base_icon_path, "pin.svg")), "Unpin All Notes", self)
                unpin_all_act.triggered.connect(self._unpin_all_notes)
                menu.addAction(unpin_all_act)
            
            elif item_type == "folder":
                folder_name = data.get("name")
                is_folder_locked = self.note_service.is_folder_locked(folder_name)
                
                icon_path = os.path.join(base_icon_path, "note-add.svg")
                add_note_act = QAction(QIcon(icon_path), "New Note Here", self)
                add_note_act.triggered.connect(lambda: self.add_new_note(folder=folder_name))
                if is_folder_locked:
                    add_note_act.setEnabled(False) # Prevent creating unprotected notes in locked folder
                menu.addAction(add_note_act)
                
                menu.addSeparator()
                
                # Lock/Unlock Folder Action
                lock_text = "Unlock Folder" if is_folder_locked else "Lock Folder"
                lock_icon_name = "unlock.svg" if is_folder_locked else "lock.svg"
                lock_icon = QIcon(os.path.join(base_icon_path, lock_icon_name))
                lock_folder_act = QAction(lock_icon, lock_text, self)
                lock_folder_act.triggered.connect(lambda: self.toggle_folder_lock(folder_name, is_folder_locked))
                menu.addAction(lock_folder_act)
                
                menu.addSeparator()
                
                if data.get("name") != "General":
                    icon_path = os.path.join(base_icon_path, "rename.svg")
                    rename_act = QAction(QIcon(icon_path), "Rename Folder", self)
                    rename_act.triggered.connect(lambda: self.tree.editItem(item, 0))
                    menu.addAction(rename_act)
                    
                    icon_path = os.path.join(base_icon_path, "trash.svg")
                    delete_act = QAction(QIcon(icon_path), "Delete Folder", self)
                    delete_act.triggered.connect(self.delete_selected_folder)
                    menu.addAction(delete_act)
                    
                    delete_notes_act = QAction(QIcon(icon_path), "Delete All Notes in Folder", self)
                    delete_notes_act.triggered.connect(lambda: self.delete_all_notes_in_folder(data.get("name")))
                    menu.addAction(delete_notes_act)
            
            elif item_type == "note":
                icon_path = os.path.join(base_icon_path, "note.svg")
                open_act = QAction(QIcon(icon_path), "Open", self)
                open_act.triggered.connect(lambda: self.note_selected.emit(data["obj_name"]))
                menu.addAction(open_act)
                
                icon_path = os.path.join(base_icon_path, "rename.svg")
                rename_act = QAction(QIcon(icon_path), "Rename", self)
                rename_act.triggered.connect(lambda: self.tree.editItem(item, 0))
                menu.addAction(rename_act)
                
                menu.addSeparator()
                
                # Pin/Unpin Action
                obj_name = data["obj_name"]
                note = self.note_service.get_note_by_id(obj_name)
                
                # Pin logic
                is_pinned = note.get("pinned", 0) if note else False
                pin_text = "Unpin Note" if is_pinned else "Pin Note"
                pin_icon = QIcon(os.path.join(base_icon_path, "pin.svg"))
                pin_act = QAction(pin_icon, pin_text, self)
                pin_act.triggered.connect(lambda: self.toggle_note_pin(obj_name))
                menu.addAction(pin_act)
                
                # Lock/Unlock Action
                is_locked = note.get("is_locked", 0) if note else False
                lock_text = "Unlock Note" if is_locked else "Lock Note"
                lock_icon_name = "unlock.svg" if is_locked else "lock.svg"
                lock_icon = QIcon(os.path.join(base_icon_path, lock_icon_name))
                lock_act = QAction(lock_icon, lock_text, self)
                lock_act.triggered.connect(lambda: self.toggle_note_lock(obj_name))
                menu.addAction(lock_act)
                
                menu.addSeparator()
                        
                icon_path = os.path.join(base_icon_path, "trash.svg")
                delete_act = QAction(QIcon(icon_path), "Delete Note", self)
                delete_act.triggered.connect(self.delete_selected_items)
                menu.addAction(delete_act)

                menu.addSeparator()
                
                # Move to Folder Sub-menu
                move_menu = menu.addMenu(QIcon(os.path.join(base_icon_path, "folder-open.svg")), "Move to Folder")
                folders = self.note_service.get_folders()
                current_folder = note.get("folder", "General") if note else "General"
                
                for f_name in folders:
                    if f_name == current_folder: continue
                    move_act = QAction(f_name, self)
                    move_act.triggered.connect(lambda checked, fn=f_name: self.on_move_note_requested(obj_name, fn))
                    move_menu.addAction(move_act)

            elif item_type == "browser":
                icon_path = os.path.join(base_icon_path, "browser.svg")
                open_act = QAction(QIcon(icon_path), "Open", self)
                open_act.triggered.connect(lambda: self._focus_browser_dock(data["obj_name"]))
                menu.addAction(open_act)

                icon_path = os.path.join(base_icon_path, "rename.svg")
                rename_act = QAction(QIcon(icon_path), "Rename", self)
                rename_act.triggered.connect(lambda: self._rename_browser_dock(data["obj_name"]))
                menu.addAction(rename_act)

                menu.addSeparator()

                icon_path = os.path.join(base_icon_path, "trash.svg")
                close_act = QAction(QIcon(icon_path), "Close Browser", self)
                close_act.triggered.connect(lambda: self._close_browser_dock(data["obj_name"]))
                menu.addAction(close_act)
        
        else:
            # Empty space
            icon_path = os.path.join(self._get_base_icon_path(), "folder-add.svg")
            new_folder_act = QAction(QIcon(icon_path), "New Folder", self)
            new_folder_act.triggered.connect(self.add_new_folder)
            menu.addAction(new_folder_act)
            
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _unpin_all_notes(self):
        """Unpins all notes currently in the Pinned folder."""
        pinned = self.note_service.get_pinned_notes()
        if not pinned: return
        
        for note in pinned:
            # Note objects can be dicts or dataclasses
            obj_name = note.obj_name if hasattr(note, 'obj_name') else note.get("obj_name")
            self.note_service.toggle_pin(obj_name)
        
        self.note_service.save_to_disk()
        self.refresh_tree()

    def on_move_note_requested(self, note_obj_name, new_folder):
        if self.note_service.move_note(note_obj_name, new_folder):
            self.note_service.save_to_disk()
            self.refresh_tree() # Menu move logic requires refresh as we don't know item location easily

    def toggle_note_pin(self, obj_name):
        """Helper to toggle pin status and refresh UI."""
        self.note_service.toggle_pin(obj_name)
        self.note_service.save_to_disk()
        self.refresh_tree()

    def toggle_note_lock(self, obj_name):
        """Handles locking/unlocking a note with UI dialogs."""
        note = self.note_service.get_note_by_id(obj_name)
        if not note: return
        
        is_locked = note.get("is_locked", 0)
        
        if is_locked:
            # Unlock logic
            is_dark = getattr(self.main_window.theme_manager, "is_dark_mode", True) if self.main_window else True
            pwd, ok = PasswordDialog.get_input(self, "Unlock Note", "Enter password:", is_dark=is_dark)
            if ok:
                if self.note_service.unlock_note(obj_name, pwd):
                    self.note_service.save_to_disk()
                    self.refresh_tree()
                    self.statusBar_msg(f"Note '{note['title']}' unlocked.")
                else:
                    QMessageBox.warning(self, "Error", "Incorrect password.")
        else:
            # Lock logic
            is_dark = getattr(self.main_window.theme_manager, "is_dark_mode", True) if self.main_window else True
            pwd, ok = PasswordDialog.get_input(self, "Lock Note", "Set password for this note:", is_dark=is_dark)
            if ok and pwd:
                confirm_pwd, ok2 = PasswordDialog.get_input(self, "Lock Note", "Confirm password:", is_dark=is_dark)
                if ok2:
                    if pwd == confirm_pwd:
                        self.note_service.lock_note(obj_name, pwd)
                        self.note_service.save_to_disk()
                        self.refresh_tree()
                        self.statusBar_msg(f"Note '{note['title']}' locked.")

    def toggle_folder_lock(self, folder_name, is_locked):
        """Handles locking/unlocking all notes in a folder with UI dialogs."""
        is_dark = getattr(self.main_window.theme_manager, "is_dark_mode", True) if getattr(self, "main_window", None) else True
        
        if is_locked:
            pwd, ok = PasswordDialog.get_input(self, "Unlock Folder", f"Enter password to unlock '{folder_name}':", is_dark=is_dark)
            if ok:
                if self.note_service.unlock_folder(folder_name, pwd):
                    self.note_service.save_to_disk()
                    self.refresh_tree()
                    self.statusBar_msg(f"Folder '{folder_name}' unlocked.")
                else:
                    QMessageBox.warning(self, "Error", "Incorrect password or partial unlock failure.")
        else:
            pwd, ok = PasswordDialog.get_input(self, "Lock Folder", f"Set password to lock ALL notes in '{folder_name}':", is_dark=is_dark)
            if ok and pwd:
                confirm_pwd, ok2 = PasswordDialog.get_input(self, "Lock Folder", "Confirm password:", is_dark=is_dark)
                if ok2:
                    if pwd == confirm_pwd:
                        if self.note_service.lock_folder(folder_name, pwd):
                            self.note_service.save_to_disk()
                            self.refresh_tree()
                            self.statusBar_msg(f"Folder '{folder_name}' locked.")
                        else:
                            QMessageBox.information(self, "Info", "Folder is empty, nothing to lock.")
                    else:
                        QMessageBox.warning(self, "Error", "Passwords do not match.")

    def statusBar_msg(self, msg):
        """Sends a message to the main status bar if available."""
        if self.main_window and hasattr(self.main_window, 'status_bar_manager'):
            self.main_window.statusBar().showMessage(msg, 3000)
