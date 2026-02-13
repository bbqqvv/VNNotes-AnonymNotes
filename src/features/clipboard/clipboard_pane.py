from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class ClipboardPane(QWidget):
    item_clicked = pyqtSignal(str) # Signal when user selects an item
    item_remove_requested = pyqtSignal(str)
    clear_all_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QListWidget.Shape.NoFrame)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.on_context_menu)
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

    def on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction, QIcon
        import os
        
        # Icon helper
        main_window = self.window()
        def get_icon(name):
             if hasattr(main_window, "_get_icon"):
                 return main_window._get_icon(name)
             return QIcon()

        menu = QMenu(self)
        
        if item:
            remove_act = QAction(get_icon("close.svg"), "Remove Item", self)
            remove_act.triggered.connect(lambda: self.item_remove_requested.emit(item.data(Qt.ItemDataRole.UserRole)))
            menu.addAction(remove_act)
            menu.addSeparator()

        clear_act = QAction(get_icon("trash.svg"), "Clear All History", self)
        clear_act.triggered.connect(lambda: self.clear_all_requested.emit())
        menu.addAction(clear_act)
        
        menu.exec(self.list_widget.mapToGlobal(pos))
