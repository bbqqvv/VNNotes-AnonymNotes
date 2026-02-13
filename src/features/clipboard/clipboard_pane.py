from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class ClipboardPane(QWidget):
    item_clicked = pyqtSignal(str) # Signal when user selects an item

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Header (Optional, maybe just use Dock title)
        # self.header = QLabel("History (Click to Paste)")
        # self.header.setStyleSheet("color: #888; font-size: 10px; padding: 4px;")
        # self.layout.addWidget(self.header)
        
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.Shape.NoFrame)
        self.list_widget.setStyleSheet("""
            QListWidget { background: transparent; }
            QListWidget::item { 
                padding: 8px; 
                border-bottom: 1px solid #333; 
                color: #ccc;
            }
            QListWidget::item:hover { background: #333; color: #fff; }
            QListWidget::item:selected { background: #444; color: #fff; }
        """)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.layout.addWidget(self.list_widget)

    def update_history(self, history):
        self.list_widget.clear()
        for text in history:
            # Create preview (truncate)
            preview = text.strip().replace("\n", " ")
            if len(preview) > 50:
                preview = preview[:50] + "..."
            
            item = QListWidgetItem(preview)
            item.setData(Qt.ItemDataRole.UserRole, text) # Store full text
            item.setToolTip(text[:200]) # Tooltip shows more
            self.list_widget.addItem(item)

    def on_item_clicked(self, item):
        full_text = item.data(Qt.ItemDataRole.UserRole)
        self.item_clicked.emit(full_text)
