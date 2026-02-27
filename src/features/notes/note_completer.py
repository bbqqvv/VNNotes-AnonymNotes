from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

class NoteCompleter(QListWidget):
    """
    A lightweight, searchable popup for @mentions.
    """
    note_selected = pyqtSignal(dict) # Emits the note dict (obj_name, title)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Use Qt.WindowType.ToolTip to ensure it floats above everything without formal window focus
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus) 
        self.setMouseTracking(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.itemClicked.connect(self._on_item_clicked)
        
        # Styles
        self.setFixedSize(250, 180)
        self.setObjectName("NoteCompleter")
        
        # Initial hiding
        self.hide()

    def show_completions(self, pos: QPoint, notes: list, filter_text: str = ""):
        """Positions and populates the completer."""
        self.clear()
        
        # Filter and sort
        filtered = []
        for n in notes:
            title = n.get("title", "Untitled")
            if filter_text.lower() in title.lower():
                filtered.append(n)
        
        # Sort by title
        filtered.sort(key=lambda x: x.get("title", "").lower())
        
        if not filtered:
            self.hide()
            return
            
        for n in filtered:
            item = QListWidgetItem(n.get("title", "Untitled"))
            item.setData(Qt.ItemDataRole.UserRole, n)
            self.addItem(item)
            
        self.setCurrentRow(0)
        self.move(pos)
        self.show()

    def _on_item_clicked(self, item):
        note = item.data(Qt.ItemDataRole.UserRole)
        self.note_selected.emit(note)
        self.hide()

    def handle_navigation(self, event):
        """Allow arrow key navigation called from NotePane's keyPressEvent."""
        if event.key() == Qt.Key.Key_Up:
            self.setCurrentRow(max(0, self.currentRow() - 1))
            return True
        elif event.key() == Qt.Key.Key_Down:
            self.setCurrentRow(min(self.count() - 1, self.currentRow() + 1))
            return True
        elif event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            item = self.currentItem()
            if item:
                self._on_item_clicked(item)
                return True
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
            return True
        return False

    def apply_theme(self, is_dark):
        """Styles the completer based on the current theme."""
        bg = "#2d2d2d" if is_dark else "#ffffff"
        fg = "#ffffff" if is_dark else "#000000"
        border = "#444444" if is_dark else "#cccccc"
        selection_bg = "#3498db"
        
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 8px;
                outline: none;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 6px 10px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {selection_bg};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {selection_bg}33;
            }}
        """)
