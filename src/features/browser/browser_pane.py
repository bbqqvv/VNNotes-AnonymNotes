from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QToolBar, QLineEdit)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView

class BrowserPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setStyleSheet("QToolBar { background: #222; border-bottom: 1px solid #444; spacing: 5px; }")
        layout.addWidget(self.toolbar)
        
        # Web View
        self.browser = QWebEngineView()
        # Default to Google
        self.browser.setUrl(QUrl("https://www.google.com"))
        self.browser.urlChanged.connect(self.update_url_bar)
        
        # Actions
        back_act = QAction("<", self)
        back_act.triggered.connect(self.browser.back)
        self.toolbar.addAction(back_act)
        
        fwd_act = QAction(">", self)
        fwd_act.triggered.connect(self.browser.forward)
        self.toolbar.addAction(fwd_act)
        
        reload_act = QAction("R", self)
        reload_act.triggered.connect(self.browser.reload)
        self.toolbar.addAction(reload_act)
        
        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or Search...")
        self.url_bar.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar.addWidget(self.url_bar)
        
        layout.addWidget(self.browser)

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return
            
        # Basic heuristic for URL vs Search
        if "." in text and " " not in text:
            if not text.startswith("http"):
                text = "https://" + text
            url = QUrl(text)
        else:
            # Google Search
            url = QUrl(f"https://www.google.com/search?q={text}")
            
        self.browser.setUrl(url)

    def update_url_bar(self, q):
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)
