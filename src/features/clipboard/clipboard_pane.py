from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QFont, QIcon, QImage

class ClipboardPane(QWidget):
    item_clicked = pyqtSignal(object) # Signal when user selects an item (passes the item dict)
    item_remove_requested = pyqtSignal(int)
    clear_all_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ClipboardList")
        self.list_widget.setFrameShape(QListWidget.Shape.NoFrame)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.on_context_menu)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.layout.addWidget(self.list_widget)

    def update_history(self, history):
        self.list_widget.clear()
        
        main_window = self.window()
        def get_icon(name):
             if hasattr(main_window, "_get_icon"):
                 return main_window._get_icon(name)
             return QIcon()

        for i, item_dict in enumerate(history):
            preview = item_dict.get("preview", "Content")
            list_item = QListWidgetItem(preview)
            
            # Set icons based on type
            if item_dict["type"] == "image":
                list_item.setIcon(get_icon("image.svg"))
                list_item.setText(f" [Image] {preview}")
            elif item_dict["type"] == "html":
                list_item.setIcon(get_icon("code.svg"))
            
            list_item.setData(Qt.ItemDataRole.UserRole, i) # Store index
            self.list_widget.addItem(list_item)

    def on_item_clicked(self, list_item):
        idx = list_item.data(Qt.ItemDataRole.UserRole)
        # Re-inject data into system clipboard for immediate paste
        main_window = self.window()
        if main_window and hasattr(main_window, "clipboard_manager"):
            history = main_window.clipboard_manager.get_history()
            if 0 <= idx < len(history):
                item_dict = history[idx]
                
                mime = QMimeData()
                if item_dict["type"] == "image":
                    mime.setImageData(item_dict["data"])
                elif item_dict["type"] == "html":
                    mime.setHtml(item_dict["data"])
                    if "text_fallback" in item_dict:
                        mime.setText(item_dict["text_fallback"])
                else:
                    mime.setText(item_dict["data"])
                
                QApplication.clipboard().setMimeData(mime)
                # Also emit for any internal handlers
                self.item_clicked.emit(item_dict)

    def on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        main_window = self.window()
        def get_icon(name):
             if hasattr(main_window, "_get_icon"):
                 return main_window._get_icon(name)
             return QIcon()

        menu = QMenu(self)
        if item:
            idx = item.data(Qt.ItemDataRole.UserRole)
            remove_act = QAction(get_icon("close.svg"), "Remove Item", self)
            remove_act.triggered.connect(lambda: self.item_remove_requested.emit(idx))
            menu.addAction(remove_act)
            menu.addSeparator()

        clear_act = QAction(get_icon("trash.svg"), "Clear All History", self)
        clear_act.triggered.connect(lambda: self.clear_all_requested.emit())
        menu.addAction(clear_act)
        
        menu.exec(self.list_widget.mapToGlobal(pos))
