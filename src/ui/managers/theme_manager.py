import os
from PyQt6.QtGui import QIcon, QPalette, QColor
from PyQt6.QtWidgets import QMainWindow, QDockWidget, QApplication

class ThemeManager:
    """
    Manages application theme, stylesheets, and icons.
    Separates UI styling logic from MainWindow.
    """
    
    THEME_CONFIG = {
        "zinc": {  # Premium Dark
            "bg": "#09090b", "surface": "#18181b", "border": "#27272a", 
            "text": "#f4f4f5", "text_muted": "#a1a1aa", "accent": "#3b82f6",
            "selection": "#27272a", "hover": "#2a2a2e", "is_dark": True
        },
        "nord": { # Arctic Blue
            "bg": "#2e3440", "surface": "#3b4252", "border": "#434c5e",
            "text": "#eceff4", "text_muted": "#d8dee9", "accent": "#88c0d0",
            "selection": "#4c566a", "hover": "#434c5e", "is_dark": True
        },
        "midnight": { # Deep Navy
            "bg": "#020617", "surface": "#0f172a", "border": "#1e293b",
            "text": "#f1f5f9", "text_muted": "#94a3b8", "accent": "#38bdf8",
            "selection": "#1e293b", "hover": "#1e293b", "is_dark": True
        },
        "solarized": { # Classic Solarized Dark
            "bg": "#002b36", "surface": "#073642", "border": "#586e75",
            "text": "#839496", "text_muted": "#586e75", "accent": "#268bd2",
            "selection": "#073642", "hover": "#0c4452", "is_dark": True
        },
        "slate": { # Premium Light
            "bg": "#f8fafc", "surface": "#ffffff", "border": "#e2e8f0",
            "text": "#0f172a", "text_muted": "#64748b", "accent": "#2563eb",
            "selection": "#eff6ff", "hover": "#f1f5f9", "is_dark": False
        },
        "sepia": { # Reading Mode
            "bg": "#fdf6e3", "surface": "#eee8d5", "border": "#d33682",
            "text": "#586e75", "text_muted": "#93a1a1", "accent": "#b58900",
            "selection": "#eee8d5", "hover": "#d8d1bc", "is_dark": False
        },
        "dracula": { # Iconic Purple
            "bg": "#282a36", "surface": "#44475a", "border": "#6272a4",
            "text": "#f8f8f2", "text_muted": "#6272a4", "accent": "#bd93f9",
            "selection": "#44475a", "hover": "#4d5166", "is_dark": True
        },
        "everforest": { # Organic Green
            "bg": "#2d353b", "surface": "#3d484d", "border": "#475258",
            "text": "#d3c6aa", "text_muted": "#859289", "accent": "#a7c080",
            "selection": "#3d484d", "hover": "#445055", "is_dark": True
        },
        "rose_pine": { # Elegant Serene
            "bg": "#191724", "surface": "#1f1d2e", "border": "#26233a",
            "text": "#e0def4", "text_muted": "#908caa", "accent": "#ebbcba",
            "selection": "#2a2837", "hover": "#252235", "is_dark": True
        },
        "gruvbox": { # Retro Comfort
            "bg": "#282828", "surface": "#3c3836", "border": "#504945",
            "text": "#ebdbb2", "text_muted": "#928374", "accent": "#fabd2f",
            "selection": "#3c3836", "hover": "#45403d", "is_dark": True
        }
    }

    def __init__(self, main_window, config_manager, base_path):
        self.main_window = main_window
        self.config = config_manager
        self.base_path = base_path
        
        # Initial theme selection
        saved_theme = self.config.get_value("app/theme")
        if not saved_theme:
            # First run: Detect system theme
            self.current_theme = "zinc" if self._is_system_dark() else "slate"
        else:
            self.current_theme = saved_theme
            
        # Legacy migration
        if self.current_theme == "dark": self.current_theme = "zinc"
        if self.current_theme == "light": self.current_theme = "slate"

    @property
    def is_dark_mode(self):
        """Returns True if current theme is a dark theme."""
        return self.THEME_CONFIG.get(self.current_theme, {}).get("is_dark", True)

    def get_theme_palette(self):
        """Returns the color config dictionary for the current theme."""
        return self.THEME_CONFIG.get(self.current_theme, self.THEME_CONFIG["zinc"])

    def apply_theme(self, mode=None):
        """Applies the specified theme mode ('dark' or 'light')."""
        if mode:
            self.current_theme = mode
            
        self.config.set_value("app/theme", self.current_theme)
        
        # Update Branding if available
        if hasattr(self.main_window, 'branding'):
            self.main_window.branding.update()
            
        # Get path for close icon to use in CSS
        # Map current theme to dark/light icons
        is_dark = self.THEME_CONFIG.get(self.current_theme, {}).get("is_dark", True)
        folder = "dark_theme" if is_dark else "light_theme"
        close_icon_url = os.path.join(self.base_path, "assets", "icons", folder, "close.svg").replace("\\", "/")
        top_icon_url = os.path.join(self.base_path, "assets", "icons", folder, "top.svg").replace("\\", "/")
        right_icon_url = os.path.join(self.base_path, "assets", "icons", folder, "chevron-right.svg").replace("\\", "/")

        try:
            style = self._generate_stylesheet(self.current_theme, close_icon_url, top_icon_url, right_icon_url)
        except Exception:
            # Emergency fallback: apply zinc (Dark) if generation fails
            self.current_theme = "zinc"
            style = self._generate_stylesheet("zinc", close_icon_url, top_icon_url, right_icon_url)
            
        self.main_window.setStyleSheet(style)
        
        # Apply globally to ensure all dialogs and popups are themed
        app = QApplication.instance()
        if app:
            app.setStyleSheet(style)
        
        # Update Sidebar Icons
        if hasattr(self.main_window, 'sidebar'):
             self.main_window.sidebar.update_toolbar_icons()
             self.main_window.sidebar.refresh_tree()
        
        if hasattr(self.main_window, 'menu_manager'):
             self.main_window.menu_manager.update_icons()

        if hasattr(self.main_window, 'find_manager'):
             self.main_window.find_manager._apply_theme()

        theme_config = self.THEME_CONFIG.get(self.current_theme, self.THEME_CONFIG["zinc"])
        self._sync_application_palette(theme_config)


    def _sync_application_palette(self, c):
        """Synchronizes the application's global palette with the theme for native contrast."""
        app = QApplication.instance()
        if not app: return
        
        p = app.palette()
        bg = QColor(c['bg'])
        text = QColor(c['text'])
        surface = QColor(c['surface'])
        
        p.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Window, bg)
        p.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.WindowText, text)
        p.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Base, bg)
        p.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Text, text)
        p.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Button, surface)
        p.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.ButtonText, text)
        p.setColor(QPalette.ColorGroup.All, QPalette.ColorRole.Highlight, QColor(c['accent']))
        
        app.setPalette(p)

    def toggle_theme(self):
        """Cycles through all available themes in THEME_CONFIG sequentially."""
        keys = list(self.THEME_CONFIG.keys())
        try:
            current_index = keys.index(self.current_theme)
            next_index = (current_index + 1) % len(keys)
        except ValueError:
            next_index = 0
            
        new_theme = keys[next_index]
        self.apply_theme(new_theme)
        return new_theme

    def _is_system_dark(self):
        """Detects if Windows is in dark mode (Registry check)."""
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return value == 0 # 0 means Dark, 1 means Light
        except Exception:
            return True # Default to Dark if detection fails or not on Windows

    def get_icon(self, filename):
        """Retrieves a QIcon based on theme brightness, with fallback to root icons."""
        is_dark = self.THEME_CONFIG.get(self.current_theme, {}).get("is_dark", True)
        folder = "dark_theme" if is_dark else "light_theme"
        
        # 1. Try themed folder
        path = os.path.join(self.base_path, "assets", "icons", folder, filename)
        if os.path.exists(path):
            return QIcon(path)
            
        # 2. Fallback to root icons folder
        root_path = os.path.join(self.base_path, "assets", "icons", filename)
        return QIcon(root_path) if os.path.exists(root_path) else QIcon()

    def _generate_stylesheet(self, theme_name, close_icon_url, top_icon_url, right_icon_url):
        """Generates simpler dynamic CSS from THEME_CONFIG."""
        c = self.THEME_CONFIG.get(theme_name, self.THEME_CONFIG["zinc"])
        
        # Determine Menu Selection Colors (High Contrast Logic)
        if c.get("is_dark", True):
            # Dark: Solid blue background, white text/icons
            menu_sel_bg = c['accent']
            menu_sel_text = "#ffffff"
        else:
            # Light: Pale blue/grey background, keeps dark icons visible
            # We use 'selection' color or a fallback soft blue
            menu_sel_bg = c.get('selection', '#eff6ff')
            menu_sel_text = c['accent'] # Accent color for text contrast
        
        return f"""
            QMainWindow {{
                background-color: {c['bg']};
                color: {c['text']};
                font-family: 'Segoe UI', 'Inter', sans-serif;
            }}
            
            QDockWidget {{
                background-color: {c['bg']};
                color: {c['text']};
                border: none;
            }}
            
            /* Central Widget Container */
            #CentralWidget, BrandingOverlay {{
                background-color: {c['bg']};
            }}
            
            QMainWindow::separator {{
                background-color: {c['border']};
                width: 1px;
                height: 1px;
            }}

            
            QLineEdit {{ 
                background: {c['bg']}; 
                color: {c['text']}; 
                border: 1px solid {c['border']}; 
                padding: 4px 8px;
                border-radius: 6px; 
                selection-background-color: {c['accent']};
            }}
            
            QLineEdit:focus {{
                border-color: {c['accent']};
            }}
            
            QLineEdit#SidebarSearch {{
                margin: 2px 4px;
            }}
            
            /* Plan v10.1: Specialized Compact Editor for Rename/Item editing */
            QAbstractItemView QLineEdit {{
                padding: 0px 2px;
                margin: 0px;
                border: 1px solid {c['accent']};
                border-radius: 2px;
                background: {c['surface']};
                color: {c['text']};
                selection-background-color: {c['accent']};
            }}
            
            QTextEdit, NotePane {{ 
                background: {c['bg']}; 
                color: {c['text']}; 
                border: 1px solid {c['border']}; 
                border-radius: 4px;
                font-family: 'Segoe UI', 'Inter', sans-serif; 
                padding: 4px;
                selection-background-color: {c['accent']};
            }}

            QToolBar {{ 
                background: {c['surface']}; 
                border-bottom: 1px solid {c['border']}; 
                padding: 4px;
                spacing: 0px;
            }}
            QToolBar QToolButton, QToolBar QPushButton {{ 
                background: transparent; 
                border: none;
                border-radius: 4px; 
                padding: 3px; 
                margin: 3px 1px;
                min-width: 24px;
                min-height: 24px;
            }}
            QToolBar QToolButton:hover, QToolBar QPushButton:hover, QToolButton#FormattingButton:hover {{
                background: {c['hover']};
            }}
            
            QMenuBar::item {{ 
                padding: 4px 10px; 
                background: transparent; 
                border-radius: 4px;
                margin: 2px 2px;
            }}
            QMenuBar::item:selected {{ 
                background: {c['hover']}; 
            }}
            
            QMenu {{ 
                background: {c['surface']}; 
                color: {c['text']}; 
                border: 1px solid {c['border']}; 
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 32px 6px 32px; /* Extra room for icons/arrows */
                border-radius: 5px;
                margin: 1px 4px;
            }}
            QMenu::item:selected {{ 
                background: {menu_sel_bg}; 
                color: {menu_sel_text}; 
            }}
            QMenu::icon {{
                padding-left: 10px;
            }}
            QMenu::right-arrow {{
                image: url("{right_icon_url}");
                padding-right: 8px;
                width: 14px;
                height: 14px;
            }}
            QMenu::separator {{
                height: 1px;
                background: {c['border']};
                margin: 4px 10px;
            }}
            
            QStatusBar {{ 
                background: {c['surface']}; 
                color: {c['text_muted']}; 
                border-top: 1px solid {c['border']}; 
            }}
            QStatusBar QLabel {{ 
                color: {c['text_muted']}; 
            }}
            
            QTreeWidget {{ 
                background: {c['bg']}; 
                color: {c['text_muted']}; 
                border: none;
                font-size: 9pt;
            }}
            QTreeWidget::item {{
                padding: 5px 6px;
                border-radius: 4px;
                margin: 1px 0px;
            }}
            QTreeWidget::item:hover {{ 
                background: {c['hover']}; 
            }}
            QTreeWidget::item:selected {{ 
                background: {menu_sel_bg}; 
                color: {menu_sel_text}; 
            }}
            
            /* High Contrast Dialog Inputs */
            QInputDialog, QDialog {{
                background: {c['bg']};
                color: {c['text']};
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox {{
                background: {c['surface']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QComboBox {{
                background: {c['surface']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 2px 4px;
            }}
            QToolBar QComboBox {{
                background: transparent;
                border: 1px solid transparent;
            }}
            QToolBar QComboBox:hover {{
                background: {c['hover']};
                border: 1px solid {c['border']};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 14px;
                border-left-width: 0px;
            }}
            QComboBox QAbstractItemView {{
                background: {c['surface']};
                color: {c['text']};
                selection-background-color: {c['accent']};
                border: 1px solid {c['border']};
                border-radius: 4px;
            }}
            QComboBox QLineEdit {{
                color: {c['text']};
                background: transparent;
                padding-left: 4px;
            }}
            QLabel {{
                color: {c['text']};
            }}
            
            #SidebarHeader {{ 
                background: {c['surface']}; 
                border-bottom: 1px solid {c['border']}; 
                padding: 6px 0;
            }}
            
            /* Tabs */
            QTabBar::tab {{
                background-color: {c['bg']}; 
                color: {c['text_muted']}; 
                padding: 2px 10px; 
                border: 1px solid {c['border']};
                border-bottom: none;
                border-top-left-radius: 2px;
                border-top-right-radius: 2px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {c['surface']};
                color: {c['text']};
            }}
            
            /* Tab bar overflow scroll buttons */
            QTabBar QToolButton {{
                background: {c['surface']};
                border: 1px solid {c['border']};
                border-radius: 2px;
                padding: 2px;
                margin: 1px;
            }}
            QTabBar QToolButton:hover {{
                background: {c['hover']};
            }}
            
            QTabWidget::pane {{
                border: none;
                background-color: {c['bg']};
            }}
            
            QTabBar::close-button {{
                image: url("{close_icon_url}");
                subcontrol-position: right;
                border-radius: 4px;
                padding: 1px;
            }}
            QTabBar::close-button:hover {{
                background-color: {c['hover']};
            }}
            
            QScrollBar:vertical {{
                background: {c['bg']};
                width: 12px;
            }}
            QScrollBar::handle:vertical {{
                background: {c['border']};
                min-height: 20px;
                border: 1px solid {c['border']};
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {c['text_muted']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QScrollBar:horizontal {{
                background: {c['bg']};
                height: 12px;
            }}
            QScrollBar::handle:horizontal {{
                background: {c['border']};
                min-width: 20px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {c['text_muted']};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QToolTip {{
                background-color: {c['surface']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 4px;
            }}
        """

