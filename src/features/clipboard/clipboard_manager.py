from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

class ClipboardManager(QObject):
    history_updated = pyqtSignal(list)

    def __init__(self, max_items=20):
        super().__init__()
        self.max_items = max_items
        self.history = []
        self.clipboard = QApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_change)

    def on_clipboard_change(self):
        text = self.clipboard.text()
        if not text or not text.strip():
            return
            
        # Avoid duplicates at the top
        if self.history and self.history[0] == text:
            return

        # Remove if exists elsewhere to move to top
        if text in self.history:
            self.history.remove(text)

        self.history.insert(0, text)
        
        # Trim size
        if len(self.history) > self.max_items:
            self.history = self.history[:self.max_items]

        self.history_updated.emit(self.history)

    def get_history(self):
        return self.history
