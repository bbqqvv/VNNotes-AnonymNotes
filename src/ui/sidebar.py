import logging
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QMenu, QMessageBox, QLabel, QHBoxLayout, QFrame, QInputDialog, QToolBar, QLineEdit,
                             QDockWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QAction

class SidebarWidget(QWidget):
    """
    Sidebar for managing folders and tags.
    Acts as a 'Note Explorer'.
    """
    note_selected = pyqtSignal(str) # Emits note obj_name
    folder_selected = pyqtSignal(str) # Emits folder name
    note_renamed = pyqtSignal(str, str) # obj_name, new_title
    note_deleted = pyqtSignal(str) # obj_name
    
    def __init__(self, note_service, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.note_service = note_service
        self.setup_ui()
        self.refresh_tree()
        
    def setup_ui(self):
        # 1. Initialize Tree FIRST
        self.tree = QTreeWidget()
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

        # 2. Setup Layouts
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 3. Header & Toolbar
        header_frame = QFrame()
        header_frame.setObjectName("SidebarHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        title_label = QLabel("EXPLORER")
        title_label.setObjectName("SidebarTitle")
        title_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(14, 14)) # Compact size
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly) # FORCE ICONS
        self.toolbar.setStyleSheet("QToolBar { background: transparent; border: none; } QToolButton { padding: 2px; border-radius: 4px; } QToolButton:hover { background-color: rgba(255, 255, 255, 0.1); }")
        
        # Icons
        base_icon_path = "assets/icons/dark_theme" 
        import os
        if not os.path.exists(base_icon_path):
             base_icon_path = r"d:\Workspace\Tool\TH\VNNotes\assets\icons\dark_theme"

        # Actions
        self.update_toolbar_icons()
        
        header_layout.addWidget(self.toolbar)
        
        layout.addWidget(header_frame)
        
        # 4. Search Bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search notes (Ctrl+Shift+F)...")
        self.search_bar.setObjectName("SidebarSearch")
        self.search_bar.textChanged.connect(self.filter_notes)
        self.search_bar.hide() # Hidden by default
        layout.addWidget(self.search_bar)
        
        layout.addWidget(self.tree)
        
    def _get_base_icon_path(self):
        """Helper to get icon path based on current theme."""
        theme = "dark"
        if hasattr(self.main_window, 'theme_manager'):
            theme = self.main_window.theme_manager.current_theme
        
        folder = "dark_theme" if theme == "dark" else "light_theme"
        base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "assets", "icons", folder)
        
        if not os.path.exists(base_path):
             # Fallback
             base_path = f"assets/icons/{folder}"
        return base_path

    def update_toolbar_icons(self):
        """Updates toolbar icons based on current theme."""
        self.toolbar.clear()
        base_path = self._get_base_icon_path()
        
        def get_icon(name):
            p = os.path.join(base_path, name)
            return QIcon(p) if os.path.exists(p) else QIcon()

        new_note_act = QAction(get_icon("note-add.svg"), "New Note", self)
        new_note_act.setToolTip("New Note")
        new_note_act.triggered.connect(lambda: self.add_new_note())
        self.toolbar.addAction(new_note_act)
        
        new_folder_act = QAction(get_icon("folder-add.svg"), "New Folder", self)
        new_folder_act.setToolTip("New Folder")
        new_folder_act.triggered.connect(self.add_new_folder)
        self.toolbar.addAction(new_folder_act)
        
        refresh_act = QAction(get_icon("refresh.svg"), "Refresh", self)
        refresh_act.setToolTip("Refresh List")
        refresh_act.triggered.connect(self.refresh_tree)
        self.toolbar.addAction(refresh_act)
        
        collapse_act = QAction(get_icon("collapse-all.svg"), "Collapse All", self)
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
            self.tree.setFocus()
        
    def refresh_tree(self):
        """Rebuilds the tree structure from NoteService data."""
        self.tree.clear()
        
        base_icon_path = self._get_base_icon_path()
        folder_icon = QIcon(os.path.join(base_icon_path, "folder-open.svg"))
        note_icon = QIcon(os.path.join(base_icon_path, "note.svg"))
        
        notes = self.note_service.get_notes()
        config_structure = self._group_notes_by_folder(notes)
        
        # Sort folders (General first, then alphabetical)
        sorted_folders = sorted(config_structure.keys())
        if "General" in sorted_folders:
             sorted_folders.remove("General")
             sorted_folders.insert(0, "General")
             
        for folder in sorted_folders:
            folder_item = QTreeWidgetItem(self.tree)
            folder_item.setText(0, f"{folder}") 
            folder_item.setIcon(0, folder_icon)
            folder_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": folder})
            folder_item.setExpanded(True)
            folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable)
            folder_item.setFlags(folder_item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled) 
            
            # Use a slightly bolder font for folders
            font = folder_item.font(0)
            font.setBold(True)
            folder_item.setFont(0, font)
            
            folder_notes = config_structure[folder]
            for note in folder_notes:
                note_item = QTreeWidgetItem(folder_item)
                note_title = note.get("title", "Untitled")
                note_item.setText(0, note_title) # No emoji
                note_item.setIcon(0, note_icon)
                note_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "note", "obj_name": note.get("obj_name")})
                note_item.setToolTip(0, note.get("content", "")[:100])
                
                # Enable Drag & EDITING
                note_item.setFlags(note_item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsEditable)
                note_item.setFlags(note_item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)

        # ── Browser docks section ──────────────────────────────────────
        self._add_browser_section(base_icon_path)

    def _add_browser_section(self, base_icon_path):
        """Add a 'Browsers' folder showing all open BrowserPane docks."""
        if not self.main_window:
            return
        browser_docks = []
        all_docks = self.main_window.findChildren(QDockWidget)
        logging.debug(f"[Sidebar] _add_browser_section: found {len(all_docks)} total docks")
        for dock in all_docks:
            obj = dock.objectName()
            logging.debug(f"[Sidebar]   dock: {obj}")
            if obj == "SidebarDock" or not obj.startswith("BrowserDock_"):
                continue
            browser_docks.append(dock)

        logging.debug(f"[Sidebar] browser_docks count: {len(browser_docks)}")
        if not browser_docks:
            return

        browser_icon = QIcon(os.path.join(base_icon_path, "browser.svg"))
        folder_icon = QIcon(os.path.join(base_icon_path, "browser.svg"))

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
            if dock.objectName() == obj_name:
                dock.show()
                dock.raise_()
                dock.setFocus()
                return

    def _rename_browser_dock(self, obj_name):
        """Show input dialog to rename a browser dock."""
        if not self.main_window:
            return
        for dock in self.main_window.findChildren(QDockWidget):
            if dock.objectName() == obj_name:
                current_title = dock.windowTitle()
                new_title, ok = QInputDialog.getText(
                    self, "Rename Browser", "New name:", text=current_title)
                if ok and new_title.strip():
                    dock.setWindowTitle(new_title.strip())
                    dock.setToolTip(new_title.strip())
                    self.refresh_tree()
                return

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
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(50, self.refresh_tree)

    def filter_notes(self, query):
        """Filters the tree based on search query."""
        query = query.strip().lower()
        
        # If query is empty, refresh tree to show standard structure
        if not query:
            self.refresh_tree()
            return
            
        # Clear tree to build search results
        self.tree.clear()
        
        # Get matches from backend
        # Expected structure: [{"note": note, "matches": [{"type": "content", "line": 1, "text": "..."}]}]
        results = self.note_service.search_notes(query)
        
        # Re-use icons
        base_icon_path = "assets/icons/dark_theme" 
        import os
        if not os.path.exists(base_icon_path):
             base_icon_path = r"d:\Workspace\Tool\TH\VNNotes\assets\icons\dark_theme"

        note_icon = QIcon(f"{base_icon_path}/note.svg")
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
            folder_item.setIcon(0, QIcon(f"{base_icon_path}/folder-open.svg"))
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
                
                # Add Snippets as children
                for m in matches:
                    if m["type"] == "content":
                        snippet_item = QTreeWidgetItem(note_item)
                        # Format: Line X: ... text ...
                        text = f"Line {m['line']}: {m['text']}"
                        snippet_item.setText(0, text)
                        # Use a different font/color for snippet
                        font = snippet_item.font(0)
                        font.setItalic(True)
                        font.setPointSize(9)
                        snippet_item.setFont(0, font)
                        # Store data to jump to line?
                        snippet_item.setData(0, Qt.ItemDataRole.UserRole, {
                            "type": "snippet", 
                            "obj_name": note.get("obj_name"),
                            "line": m["line"]
                        })
                        snippet_item.setToolTip(0, m["text"])

    def on_item_changed(self, item, column):
        """Handle item renaming."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data: return
        
        new_text = item.text(0)
        
        if data["type"] == "note":
            obj_name = data["obj_name"]
            if self.note_service.rename_note(obj_name, new_text):
                 # Sync to storage (Async)
                 self.note_service.save_to_disk()
                 # Emit signal so MainWindow can update Dock Title
                 self.note_renamed.emit(obj_name, new_text)
                 
        elif data["type"] == "folder":
            old_name = data["name"]
            if new_text != old_name:
                if self.note_service.rename_folder(old_name, new_text):
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
        """Deletes/Removes a folder (moves notes to General)."""
        item = self.tree.currentItem()
        if not item: return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "folder": return
        
        folder_name = data.get("name")
        if folder_name == "General":
            QMessageBox.warning(self, "Warning", "Cannot delete 'General' folder.")
            return

        confirm = QMessageBox.question(self, "Delete Folder", 
                                       f"Delete folder '{folder_name}'?\nNotes will be moved to 'General'.",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            # Logic: Update all notes in this folder to "General"
            # Since NoteService doesn't have delete_folder, we do it manually or add it.
            # We implemented rename_folder, let's use rename_folder to move to General?
            # Actually, renaming to General merges them.
            if self.note_service.rename_folder(folder_name, "General"):
                self.note_service.save_to_disk()
                self.refresh_tree() # Moving to General is complex to animate, easiest to refresh

    def dropEvent(self, event):
        """Handle drop event to update data model."""
        # Get source item
        source_item = self.tree.currentItem()
        if not source_item: return
        
        # Get target item
        target_item = self.tree.itemAt(event.position().toPoint())
        if not target_item: return
        
        source_data = source_item.data(0, Qt.ItemDataRole.UserRole)
        target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
        
        if source_data["type"] == "note" and target_data["type"] == "folder":
            # Move note to new folder
            note_obj_name = source_data["obj_name"]
            new_folder = target_data["name"]
            
            if self.note_service.move_note(note_obj_name, new_folder):
                self.note_service.save_to_disk()
                # self.refresh_tree() -> handled by drag drop visual? 
                # QTreeWidget InternalMove handles the visual move.
                # We just needed to update backend.
                pass
            
        event.accept()

                
    def _group_notes_by_folder(self, notes):
        groups = {}
        for note in notes:
            folder = note.get("folder", "General")
            if folder not in groups:
                groups[folder] = []
            groups[folder].append(note)
        return groups

    def on_item_clicked(self, item, column):
        """Handle single click to open note or browser."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data: return
        
        if data.get("type") == "note":
            self.note_selected.emit(data["obj_name"])
        elif data.get("type") == "snippet":
            self.note_selected.emit(data["obj_name"])
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

    def add_new_note(self, folder=None):
        """Adds a new note. If folder is None, uses currently selected item's folder."""
        target_folder = folder
        
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
                            target_folder = parent.text(0)
        
        if not target_folder:
            target_folder = "General"

        # Create new note via service
        note_data = self.note_service.add_note(title="New Note", content="", folder=target_folder)
        self.note_service.save_to_disk()
        
        # self.refresh_tree() -> Replace with Smart Insert
        # Find the folder item
        folder_item = None
        
        # 1. Search top level items
        for i in range(self.tree.topLevelItemCount()):
            tl_item = self.tree.topLevelItem(i)
            tl_data = tl_item.data(0, Qt.ItemDataRole.UserRole)
            if tl_data and tl_data.get("type") == "folder" and tl_data.get("name") == target_folder:
                folder_item = tl_item
                break
        
        # 2. If not found (e.g. new folder created implicitly, causing refresh anyway), refresh
        if not folder_item:
             self.refresh_tree()
             return

        # 3. Add child item
        base_icon_path = self._get_base_icon_path()
        note_icon = QIcon(os.path.join(base_icon_path, "note.svg"))
        
        note_item = QTreeWidgetItem(folder_item)
        note_item.setText(0, note_data["title"])
        note_item.setIcon(0, note_icon)
        note_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "note", "obj_name": note_data["obj_name"]})
        note_item.setToolTip(0, "")
        note_item.setFlags(note_item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsEditable)
        note_item.setFlags(note_item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
        
        folder_item.setExpanded(True)
        self.tree.setCurrentItem(note_item)
        self.note_selected.emit(note_data["obj_name"]) # Open it

    def add_new_folder(self):
        """Prompts user for folder name and creates a placeholder note in it."""
        folder_name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
        if ok and folder_name:
            # Create a placeholder note to "persist" the folder
            self.add_new_note(folder=folder_name)

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
            
            if item_type == "folder":
                icon_path = os.path.join(base_icon_path, "note-add.svg")
                add_note_act = QAction(QIcon(icon_path), "New Note Here", self)
                add_note_act.triggered.connect(lambda: self.add_new_note(folder=data.get("name")))
                menu.addAction(add_note_act)
                
                if data.get("name") != "General":
                    icon_path = os.path.join(base_icon_path, "theme.svg") # Reuse theme for rename or a text icon
                    rename_act = QAction(QIcon(icon_path), "Rename Folder", self)
                    rename_act.triggered.connect(lambda: self.tree.editItem(item, 0))
                    menu.addAction(rename_act)
                    
                    icon_path = os.path.join(base_icon_path, "trash.svg")
                    delete_act = QAction(QIcon(icon_path), "Delete Folder", self)
                    delete_act.triggered.connect(self.delete_selected_folder)
                    menu.addAction(delete_act)
            
            elif item_type == "note":
                icon_path = os.path.join(base_icon_path, "note.svg")
                open_act = QAction(QIcon(icon_path), "Open", self)
                open_act.triggered.connect(lambda: self.note_selected.emit(data["obj_name"]))
                menu.addAction(open_act)
                
                icon_path = os.path.join(base_icon_path, "theme.svg")
                rename_act = QAction(QIcon(icon_path), "Rename", self)
                rename_act.triggered.connect(lambda: self.tree.editItem(item, 0))
                menu.addAction(rename_act)
                
                # Removed 'Move to...' menu per user request
                        
                icon_path = os.path.join(base_icon_path, "trash.svg")
                delete_act = QAction(QIcon(icon_path), "Delete Note", self)
                delete_act.triggered.connect(self.delete_selected_items)
                menu.addAction(delete_act)

            elif item_type == "browser":
                icon_path = os.path.join(base_icon_path, "browser.svg")
                open_act = QAction(QIcon(icon_path), "Open", self)
                open_act.triggered.connect(lambda: self._focus_browser_dock(data["obj_name"]))
                menu.addAction(open_act)

                icon_path = os.path.join(base_icon_path, "theme.svg")
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

    def on_move_note_requested(self, note_obj_name, new_folder):
        if self.note_service.move_note(note_obj_name, new_folder):
            self.note_service.save_to_disk()
            self.refresh_tree() # Menu move logic requires refresh as we don't know item location easily
