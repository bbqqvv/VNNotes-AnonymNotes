from PyQt6.QtCore import QObject, pyqtSignal, QMimeData
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage

class ClipboardManager(QObject):
    history_updated = pyqtSignal(list)

    def __init__(self, max_items=20):
        super().__init__()
        self.max_items = max_items
        self.history = []
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)

    def on_clipboard_change(self):
        mime_data = self.clipboard.mimeData()
        
        item = {}
        if mime_data.hasImage():
            image = self.clipboard.image()
            if not image.isNull():
                item = {
                    "type": "image",
                    "data": image,
                    "preview": "Image Content"
                }
        elif mime_data.hasHtml():
            html = mime_data.html()
            text = mime_data.text()
            item = {
                "type": "html",
                "data": html,
                "text_fallback": text,
                "preview": text[:100].strip().replace("\n", " ") if text else "Rich Content"
            }
        elif mime_data.hasText():
            text = mime_data.text()
            if not text.strip():
                return
            item = {
                "type": "text",
                "data": text,
                "preview": text[:100].strip().replace("\n", " ")
            }
        else:
            return

        # Avoid exact duplicates at the top (check data)
        if self.history and self.history[0].get("data") == item["data"]:
            return

        # Remove if exists elsewhere (simplistic check for strings, images always new for now)
        if item["type"] == "text":
            self.history = [h for h in self.history if h.get("data") != item["data"]]

        self.history.insert(0, item)
        
        if len(self.history) > self.max_items:
            self.history = self.history[:self.max_items]

        self.history_updated.emit(self.history)

    def get_history(self):
        return self.history

    def remove_item(self, index):
        """Removes item by index from history."""
        if 0 <= index < len(self.history):
            self.history.pop(index)
            self.history_updated.emit(self.history)

    def clear_history(self):
        self.history = []
        self.history_updated.emit(self.history)
