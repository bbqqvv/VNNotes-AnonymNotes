from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QToolBar, QLineEdit, QMenu)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView

class StealthWebView(QWebEngineView):
    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        
        # Get selected text
        selected_text = self.selectedText().strip()
        
        # Find MainWindow to access DockManager
        main_window = self.window()
        dock_manager = getattr(main_window, 'dock_manager', None)
        
        # Determine display text
        display_text = (selected_text[:20] + '..') if len(selected_text) > 20 else selected_text
        if not display_text:
            display_text = "..."
            
        # Get the first action to insert before it
        first_action = menu.actions()[0] if menu.actions() else None
        
        # --- Add items to TOP of menu ---
        import os
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        icon_dir = os.path.join(base_path, "assets", "icons", "dark_theme") # Assuming dark theme for now or generic
        
        # 1. Ask AI Action (Perplexity)
        ai_act = QAction(f"✨ Ask AI '{display_text}'", self)
        ai_icon_path = os.path.join(icon_dir, "ai.svg")
        if os.path.exists(ai_icon_path):
             ai_act.setIcon(QIcon(ai_icon_path))
             
        if not selected_text:
             ai_act.setEnabled(False)
             ai_act.setText("✨ Select text to Ask AI")
        else:
             if dock_manager:
                # Using Perplexity for "Search with AI" experience
                # Changed from /search?q= to /?q= based on user feedback
                ai_url = f"https://www.perplexity.ai/?q={selected_text}"
                ai_act.triggered.connect(lambda: dock_manager.add_browser_dock(ai_url))
        
        # 2. Translate Action
        translate_act = QAction(f"Translate '{display_text}'", self)
        translate_icon_path = os.path.join(icon_dir, "browser.svg") # Use browser icon for translate
        if os.path.exists(translate_icon_path):
             translate_act.setIcon(QIcon(translate_icon_path))
             
        if not selected_text:
             translate_act.setEnabled(False)
             translate_act.setText("Select text to Translate")
        else:
             if dock_manager:
                trans_url = f"https://translate.google.com/?sl=auto&tl=vi&text={selected_text}&op=translate"
                translate_act.triggered.connect(lambda: dock_manager.add_browser_dock(trans_url))
        
        # 3. Search Action
        search_act = QAction(f"Search '{display_text}'", self)
        search_icon_path = os.path.join(icon_dir, "search.svg")
        if os.path.exists(search_icon_path):
             search_act.setIcon(QIcon(search_icon_path))

        if not selected_text:
            search_act.setEnabled(False)
            search_act.setText("Select text to Search")
        else:
            if dock_manager:
                search_url = f"https://www.google.com/search?q={selected_text}"
                search_act.triggered.connect(lambda: dock_manager.add_browser_dock(search_url))
            else:
                 search_act.triggered.connect(lambda: self.load(QUrl(f"https://www.google.com/search?q={selected_text}")))

        # Layout: [Ask AI] [Search] [Translate]
        if first_action:
            menu.insertAction(first_action, translate_act)
            menu.insertAction(translate_act, search_act)
            menu.insertAction(search_act, ai_act) # AI at the very top
        else:
            menu.addAction(ai_act)
            menu.addAction(search_act)
            menu.addAction(translate_act)
                 
        if first_action:
            # We want Search then Translate.
            # Currently menu is [FirstAction, ...]
            # We inserted Translate: [Translate, FirstAction, ...]
            # Now insert Search before Translate: [Search, Translate, FirstAction, ...]
            menu.insertAction(translate_act, search_act)
        else:
            menu.addAction(search_act)
            
        # Separator after custom actions
        if first_action:
            menu.insertSeparator(first_action)
            
        menu.exec(event.globalPos())
            
        menu.exec(event.globalPos())

from PyQt6.QtCore import QUrl, Qt, pyqtSignal

class BrowserPane(QWidget):
    title_changed = pyqtSignal(str)

    def __init__(self, url=None, parent=None):
        super().__init__(parent)
        self.init_ui()
        if url:
            self.load_url(url)


    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setStyleSheet("QToolBar { background: #222; border-bottom: 1px solid #444; spacing: 5px; }")
        layout.addWidget(self.toolbar)


        
        # Web View
        self.browser = StealthWebView()
        # Default to Google
        self.browser.setUrl(QUrl("https://www.google.com"))
        self.browser.urlChanged.connect(self.update_url_bar)
        self.browser.titleChanged.connect(self.title_changed.emit)
        
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

    def load_url(self, url_str):
        self.browser.setUrl(QUrl(url_str))

