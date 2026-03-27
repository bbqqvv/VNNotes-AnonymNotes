import os
import sys
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QLineEdit, QMenu, QToolButton, QProgressBar)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QUrl, Qt, pyqtSignal, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings

class StealthWebView(QWebEngineView):
    def __init__(self, profile_name="default", parent=None):
        super().__init__(parent)
        
        # 1. Persistent Profile for Disk Caching (Senior Optimization)
        # Allows Chromium to reuse images/scripts across sessions
        storage_name = f"vnnotes_profile_{profile_name}"
        self._profile = QWebEngineProfile(storage_name, self)
        self._profile.setPersistentStoragePath(os.path.join(
            os.getenv('APPDATA', '.'), "VNNotes", "browser_cache", profile_name
        ))
        self._profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        
        # Create page with this profile
        self.setPage(QWebEnginePage(self._profile, self))

        # 2. Performance Settings
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.DnsPrefetchEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True) # Smooth scrolling
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        # 3. Memory Savings (Chromium 108+)
        # Automatically suspends background tabs to save RAM
        if hasattr(QWebEngineSettings.WebAttribute, 'MemorySavingsModeEnabled'):
            settings.setAttribute(QWebEngineSettings.WebAttribute.MemorySavingsModeEnabled, True)

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
        # Determine icon folder based on theme brightness
        is_dark = True
        if hasattr(main_window, 'theme_manager'):
            is_dark = main_window.theme_manager.is_dark_mode
        
        icon_folder = "dark_theme" if is_dark else "light_theme"
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        icon_dir = os.path.join(base_path, "assets", "icons", icon_folder)
        
        # 1. Ask AI Action (Perplexity)
        ai_act = QAction(f"âœ¨ Ask AI '{display_text}'", self)
        ai_icon_path = os.path.join(icon_dir, "ai.svg")
        if os.path.exists(ai_icon_path):
             ai_act.setIcon(QIcon(ai_icon_path))
             
        if not selected_text:
             ai_act.setEnabled(False)
             ai_act.setText("âœ¨ Select text to Ask AI")
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

        # --- Standard Actions Refinement ---
        
        # 1. Remove "View Page Source" and "Save Page" using robust attribute checking
        # Different versions of QtWebEngine have different names for these actions.
        for attr_name in ["ViewSource", "DownloadPage", "SavePage", "SavePageAs"]:
            if hasattr(QWebEnginePage.WebAction, attr_name):
                web_act_type = getattr(QWebEnginePage.WebAction, attr_name)
                act = self.page().action(web_act_type)
                if act in menu.actions():
                    menu.removeAction(act)

        # 2. Iconify Standard Navigation
        nav_icons = {
            "Back": "undo.svg",
            "Forward": "redo.svg",
            "Reload": "refresh.svg"
        }
        
        for attr_name, icon_name in nav_icons.items():
            if hasattr(QWebEnginePage.WebAction, attr_name):
                web_act_type = getattr(QWebEnginePage.WebAction, attr_name)
                act = self.page().action(web_act_type)
                if act in menu.actions():
                    path = os.path.join(icon_dir, icon_name)
                    if os.path.exists(path):
                        act.setIcon(QIcon(path))

        # Layout: [Ask AI] [Search] [Translate]
        if first_action:
            menu.insertAction(first_action, translate_act)
            menu.insertAction(translate_act, search_act)
            menu.insertAction(search_act, ai_act) # AI at the very top
        else:
            menu.addAction(ai_act)
            menu.addAction(search_act)
            menu.addAction(translate_act)
                  
        # Separator after custom actions
        if first_action:
            menu.insertSeparator(first_action)
            
        menu.exec(event.globalPos())

class BrowserPane(QWidget):
    title_changed = pyqtSignal(str)

    def __init__(self, url=None, parent=None):
        super().__init__(parent)
        self._pending_url = url
        self._loaded = False
        self._suspended = False
        
        # 4. Inactivity Watchdog (Memory Optimizer)
        self._suspension_timer = QTimer(self)
        self._suspension_timer.setInterval(600000) # 10 Minutes
        self._suspension_timer.timeout.connect(self._check_suspension)
        self._suspension_timer.start()
        
        self.init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if self._suspended:
            # Wake up from suspension
            self.browser.setUrl(QUrl(self._pending_url))
            self._suspended = False
            self._loaded = True
        elif self._pending_url and not self._loaded:
            # Senior Optimization: Only load network content when seen
            self.browser.setUrl(QUrl(self._pending_url))
            self._loaded = True

    def _check_suspension(self):
        """Releases heavy Chromium resources if tab is hidden for a long time."""
        if not self.isVisible() and self._loaded and not self._suspended:
            if self.browser.url().isValid() and self.browser.url().toString() != "about:blank":
                self._pending_url = self.browser.url().toString()
                self.browser.setUrl(QUrl("about:blank")) # Release resources
                self._suspended = True
                self._loaded = False
                logging.info(f"Tab suspended to save memory: {self._pending_url}")


    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar Container (QWidget instead of QToolBar to prevent floating issues)
        self.toolbar_container = QWidget()
        self.toolbar_container.setObjectName("BrowserToolbar")
        self.toolbar_container.setFixedHeight(36)
        self.toolbar_layout = QHBoxLayout(self.toolbar_container)
        self.toolbar_layout.setContentsMargins(5, 2, 5, 2)
        self.toolbar_layout.setSpacing(5)
        self.layout.addWidget(self.toolbar_container)

        # Progress Bar (Senior UX)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: none; background-color: transparent; }
            QProgressBar::chunk { background-color: #3b82f6; }
        """)
        self.progress_bar.hide()
        self.layout.addWidget(self.progress_bar)

        # Web View with distinct profile for main browser
        self.browser = StealthWebView(profile_name="main")
        # Do not load immediately in init_ui; let showEvent handle it for performance
        # self.browser.setUrl(QUrl("https://www.google.com")) 
        self.browser.urlChanged.connect(self.update_url_bar)
        self.browser.titleChanged.connect(self.title_changed.emit)
        self.browser.loadStarted.connect(lambda: self.progress_bar.show())
        self.browser.loadProgress.connect(self.progress_bar.setValue)
        self.browser.loadFinished.connect(lambda: self.progress_bar.hide())
        
        # Helper to create buttons
        from PyQt6.QtWidgets import QToolButton
        def create_btn(text, slot):
            btn = QToolButton()
            btn.setText(text)
            btn.clicked.connect(slot)
            return btn
        
        # Actions -> Buttons
        self.btn_back = create_btn("<", self.browser.back)
        self.toolbar_layout.addWidget(self.btn_back)
        
        self.btn_fwd = create_btn(">", self.browser.forward)
        self.toolbar_layout.addWidget(self.btn_fwd)
        
        self.btn_reload = create_btn("R", self.browser.reload)
        self.toolbar_layout.addWidget(self.btn_reload)
        
        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("BrowserUrlBar")
        self.url_bar.setPlaceholderText("Enter URL or Search...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.toolbar_layout.addWidget(self.url_bar, 1) # Stretch factor 1 to fill width
        
        self.layout.addWidget(self.browser)

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
        self._loaded = True # Mark as loaded if user manually navigated
        self._pending_url = None

    def load_url(self, url_str):
        self._pending_url = url_str
        if self.isVisible():
            self.browser.setUrl(QUrl(url_str))
            self._loaded = True
        else:
            self._loaded = False # Defer until next showEvent
