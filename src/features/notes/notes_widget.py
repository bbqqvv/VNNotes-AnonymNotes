import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QSplitter, 
                             QToolBar, QMessageBox)
from PyQt6.QtGui import QAction, QIcon, QFont, QTextListFormat
from PyQt6.QtCore import Qt

from src.core.config import ConfigManager

class NotesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.editors = [] # Keep track of editor instances
        self.init_ui()
        self.load_notes()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setStyleSheet("QToolBar { background: #222; border-bottom: 1px solid #444; spacing: 5px; }")
        layout.addWidget(self.toolbar)
        
        # Setup Actions
        self.setup_actions()
        
        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)
        
        # Autosave timer or signal connection happens when editors are added

    def setup_actions(self):
        # View Controls
        add_icon = QAction("+ View", self)
        add_icon.triggered.connect(self.add_view)
        self.toolbar.addAction(add_icon)
        
        remove_icon = QAction("- View", self)
        remove_icon.triggered.connect(self.remove_view)
        self.toolbar.addAction(remove_icon)
        
        self.toolbar.addSeparator()
        
        # Formatting
        bold_act = QAction("B", self)
        bold_act.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        bold_act.triggered.connect(lambda: self.apply_format("bold"))
        self.toolbar.addAction(bold_act)
        
        italic_act = QAction("I", self)
        italic_act.setFont(QFont("Segoe UI", 9, -1, True))
        italic_act.triggered.connect(lambda: self.apply_format("italic"))
        self.toolbar.addAction(italic_act)
        
        underline_act = QAction("U", self)
        underline_act.triggered.connect(lambda: self.apply_format("underline"))
        f = underline_act.font()
        f.setUnderline(True)
        underline_act.setFont(f)
        self.toolbar.addAction(underline_act)
        
        self.toolbar.addSeparator()
        
        list_act = QAction("List", self)
        list_act.triggered.connect(lambda: self.apply_format("list"))
        self.toolbar.addAction(list_act)

    def create_editor(self):
        editor = QTextEdit()
        editor.setPlaceholderText("Type notes here...")
        editor.setStyleSheet("""
            QTextEdit {
                background-color: #333;
                color: #eee;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                border: none;
                padding: 10px;
            }
            QTextEdit:focus {
                background-color: #383838;
            }
        """)
        editor.textChanged.connect(self.save_notes)
        return editor

    def add_view(self, content=""):
        if len(self.editors) >= 4:
            return # Max 4 panes
            
        editor = self.create_editor()
        if content:
            editor.setHtml(content)
            
        self.splitter.addWidget(editor)
        self.editors.append(editor)
        
        # Equalize sizes if adding fresh (optional, but nice)
        if hasattr(self, 'splitter') and self.splitter.count() > 1:
             sizes = [1 for _ in range(self.splitter.count())]
             self.splitter.setSizes(sizes)

    def remove_view(self):
        if len(self.editors) <= 1:
            return # Keep at least one
            
        # Remove the last one for simplicity, or focused one if possible
        # For now, remove last
        editor = self.editors.pop()
        editor.deleteLater() 
        self.save_notes()

    def get_focused_editor(self):
        for editor in self.editors:
            if editor.hasFocus():
                return editor
        # If none focused, default to first or last? 
        return self.editors[-1] if self.editors else None

    def apply_format(self, fmt_type):
        editor = self.get_focused_editor()
        if not editor:
            return
            
        cursor = editor.textCursor()
        fmt = cursor.charFormat()
        
        if fmt_type == "bold":
            fmt.setFontWeight(QFont.Weight.Bold if fmt.fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal)
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "italic":
            fmt.setFontItalic(not fmt.fontItalic())
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "underline":
            fmt.setFontUnderline(not fmt.fontUnderline())
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "list":
            cursor.createList(QTextListFormat.Style.ListDisc)
            
        editor.setFocus()

    def save_notes(self):
        data = {
            "count": len(self.editors),
            "panes": [editor.toHtml() for editor in self.editors],
            "splitter_state": list(self.splitter.sizes()) # QSettings handles lists weirdly usually, careful
        }
        # Serialize to JSON string for safety in QSettings
        self.config.set_value("notes/data", json.dumps(data))

    def load_notes(self):
        json_data = self.config.get_value("notes/data")
        try:
            if json_data:
                data = json.loads(json_data)
                panes = data.get("panes", [])
                
                # Create editors
                for content in panes:
                    self.add_view(content)
                    
                # If no panes loaded (e.g. first run or reset), add one
                if not self.editors:
                    self.add_view()
                    
                # Restore splitter sizes
                sizes = data.get("splitter_state")
                if sizes:
                     # Convert to int list
                     self.splitter.setSizes([int(x) for x in sizes])
            else:
                self.add_view() # Default
        except Exception as e:
            print(f"Error loading notes: {e}")
            self.add_view() # Fallback
