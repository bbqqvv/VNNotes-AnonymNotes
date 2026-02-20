import os
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QDockWidget

class ThemeManager:
    """
    Manages application theme, stylesheets, and icons.
    Separates UI styling logic from MainWindow.
    """
    def __init__(self, main_window, config_manager, base_path):
        self.main_window = main_window
        self.config = config_manager
        self.base_path = base_path
        self.current_theme = self.config.get_value("app/theme", "dark")

    def apply_theme(self, mode=None):
        """Applies the specified theme mode ('dark' or 'light')."""
        if mode:
            self.current_theme = mode
        
        self.config.set_value("app/theme", self.current_theme)
        
        # Update Branding if available
        if hasattr(self.main_window, 'branding'):
            self.main_window.branding.update()
            
        # Get path for close icon to use in CSS
        folder = "dark_theme" if self.current_theme == "dark" else "light_theme"
        close_icon_url = os.path.join(self.base_path, "assets", "icons", folder, "close.svg").replace("\\", "/")

        style = self._generate_stylesheet(self.current_theme, close_icon_url)
        self.main_window.setStyleSheet(style)
        
        # Update Sidebar Icons
        if hasattr(self.main_window, 'sidebar'):
             self.main_window.sidebar.update_toolbar_icons()
             self.main_window.sidebar.refresh_tree()
        
        # Update icons in other managers if needed
        if hasattr(self.main_window, 'menu_manager'):
             self.main_window.menu_manager.update_icons()

    def toggle_theme(self):
        """Switches between dark and light themes."""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(new_theme)
        return new_theme

    def get_icon(self, filename):
        """Retrieves a QIcon based on the current theme."""
        folder = "dark_theme" if self.current_theme == "dark" else "light_theme"
        path = os.path.join(self.base_path, "assets", "icons", folder, filename)
        return QIcon(path) if os.path.exists(path) else QIcon()

    def _generate_stylesheet(self, mode, close_icon_url):
        """Generates the CSS string."""
        if mode == "dark":
            return f"""
                QMainWindow, QDockWidget {{ background: #2b2b2b; color: #eeeeee; }}
                QTextEdit, NotePane {{ background: #333333; color: #eeeeee; border: none; font-family: 'Segoe UI', sans-serif; font-size: 13px; padding: 6px; }}
                QToolBar {{ background: #1e1e1e; border-bottom: 1px solid #333; spacing: 4px; padding: 2px; min-height: 26px; }}
                QToolButton {{ background: transparent; border-radius: 4px; padding: 2px; color: #eeeeee; }}
                QToolButton:hover {{ background: #3a3a3a; }}
                QMenuBar {{ background: #1e1e1e; color: #eeeeee; border-bottom: 1px solid #333; padding: 2px; }}
                QMenuBar::item {{ padding: 4px 8px; }}
                QMenuBar::item:selected {{ background: #3a3a3a; }}
                QMenu {{ background: #2b2b2b; color: #eeeeee; padding: 4px; border: 1px solid #444; }}
                QMenu::item:selected {{ background: #3c3c3c; }}
                QStatusBar {{ background: #2b2b2b; color: #eeeeee; border-top: 1px solid #444; min-height: 18px; }}
                QStatusBar QLabel {{ color: #eeeeee; font-size: 11px; padding: 0px 4px; }}
                
                /* Sidebar */
                QTreeWidget {{ background: #2b2b2b; color: #eeeeee; border: none; }}
                QTreeWidget::item {{ padding: 6px; border-radius: 4px; margin: 1px 4px; }}
                QTreeWidget::item:hover {{ background: #3a3a3a; }}
                QTreeWidget::item:selected {{ background: #444444; color: #ffffff; }}
                #SidebarHeader {{ background: #1e1e1e; border-bottom: 1px solid #333; }}
                #SidebarTitle {{ color: #bbbbbb; letter-spacing: 1px; }}
                
                #SidebarSearch {{ 
                    background: #2d2d2d; 
                    color: #ddd; 
                    border: 1px solid #333; 
                    border-radius: 4px; 
                    padding: 4px; 
                    margin: 5px; 
                }}
                #SidebarSearch:focus {{ border: 1px solid #555; }}
                
                /* Clipboard & Lists */
                #ClipboardList {{ background: transparent; border: none; }}
                #ClipboardList::item {{ 
                    padding: 8px; 
                    border-bottom: 1px solid #333; 
                    color: #ccc;
                }}
                #ClipboardList::item:hover {{ background: #3a3a3a; color: #fff; }}
                #ClipboardList::item:selected {{ background: #444444; color: #fff; }}
                
                QTabBar {{
                    background: #1e1e1e;
                    border-bottom: 1px solid #333;
                }}
                QTabBar::tab {{
                    background: #252525;
                    color: #888888;
                    padding: 2px 16px 2px 8px; /* Hyper-compact */
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    margin-right: 1px;
                    min-width: 50px;
                    font-size: 11px;
                    border: 1px solid transparent;
                }}
                QTabBar::tab:selected {{
                    background: #333333;
                    color: #eeeeee;
                    border-bottom: 2px solid #3498db;
                }}
                QTabBar::tab:hover {{
                    background: #2a2a2a;
                    color: #cccccc;
                }}
                
                QTabBar::close-button {{
                    image: url("{close_icon_url}");
                    subcontrol-position: right;
                    margin-right: 2px;
                    width: 12px;
                    height: 12px;
                    border-radius: 6px;
                    background: transparent;
                }}
                QTabBar::close-button:hover {{
                    background-color: #ff5f56;
                }}
            """
        else:
            return f"""
                QMainWindow, QDockWidget {{ background: #f9fafb; color: #1f2937; }}
                QTextEdit, NotePane {{ 
                    background: #ffffff; 
                    color: #1f2937; 
                    border: 1px solid #e2e8f0; 
                    border-radius: 4px;
                    font-family: 'Segoe UI', sans-serif; 
                    font-size: 13px; 
                    padding: 6px; 
                }}
                QToolBar {{ background: #ffffff; border-bottom: 1px solid #e2e8f0; spacing: 4px; padding: 2px; min-height: 26px; }}
                QToolButton {{ background: transparent; border-radius: 4px; padding: 2px; color: #4b5563; }}
                QToolButton:hover {{ background: #f3f4f6; color: #111827; }}
                
                QMenuBar {{ background: #ffffff; color: #1f2937; border-bottom: 1px solid #e2e8f0; padding: 2px; }}
                QMenuBar::item {{ padding: 4px 8px; border-radius: 4px; }}
                QMenuBar::item:selected {{ background: #f3f4f6; }}
                
                QMenu {{ background: #ffffff; color: #1f2937; padding: 4px; border: 1px solid #e2e8f0; border-radius: 6px; }}
                QMenu::item {{ padding: 6px 24px 6px 12px; border-radius: 4px; }}
                QMenu::item:selected {{ background: #eff6ff; color: #2563eb; }}
                
                QStatusBar {{ background: #ffffff; color: #6b7280; border-top: 1px solid #e2e8f0; min-height: 18px; }}
                QStatusBar QLabel {{ font-size: 11px; padding: 0px 4px; }}
                
                /* Sidebar - Compact Synchronization */
                QTreeWidget {{ background: #f9fafb; color: #374151; border: none; border-right: 1px solid #e2e8f0; }}
                QTreeWidget::item {{ padding: 6px; border-radius: 4px; margin: 1px 4px; }}
                QTreeWidget::item:hover {{ background: #f3f4f6; }}
                QTreeWidget::item:selected {{ background: #eff6ff; color: #1d4ed8; font-weight: bold; }}
                
                #SidebarHeader {{ background: #f9fafb; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; }}
                #SidebarTitle {{ color: #6b7280; font-weight: bold; letter-spacing: 0.5px; text-transform: uppercase; font-size: 10px; }}
                
                #SidebarSearch {{ 
                    background: #ffffff; 
                    color: #1f2937; 
                    border: 1px solid #e2e8f0; 
                    border-radius: 4px; 
                    padding: 4px; 
                    margin: 5px; 
                }}
                #SidebarSearch:focus {{ border: 1px solid #2563eb; }}
                
                /* Clipboard & Lists */
                #ClipboardList {{ background: transparent; border: none; }}
                #ClipboardList::item {{ 
                    padding: 8px; 
                    border-bottom: 1px solid #e2e8f0; 
                    color: #374151;
                }}
                #ClipboardList::item:hover {{ background: #f3f4f6; color: #111827; }}
                #ClipboardList::item:selected {{ background: #eff6ff; color: #1d4ed8; }}
                
                /* Modern Compact Tab Bar */
                QTabBar {{
                    background: #f1f5f9;
                    border-bottom: 1px solid #e2e8f0;
                }}
                QTabBar::tab {{
                    background: #e2e8f0;
                    color: #64748b;
                    padding: 2px 16px 2px 8px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    margin-right: 1px;
                    min-width: 50px;
                    font-size: 11px;
                    border: 1px solid #cbd5e1;
                    border-bottom: none;
                }}
                QTabBar::tab:selected {{
                    background: #ffffff;
                    color: #1e293b;
                    border: 1px solid #e2e8f0;
                    border-bottom: 2px solid #2563eb;
                }}
                QTabBar::tab:hover:!selected {{
                    background: #f8fafc;
                    color: #475569;
                }}
                
                QTabBar::close-button {{
                    image: url("{close_icon_url}");
                    subcontrol-position: right;
                    margin-right: 2px;
                    width: 12px;
                    height: 12px;
                    border-radius: 6px;
                    background: transparent;
                }}
                QTabBar::close-button:hover {{
                    background-color: #fee2e2;
                }}
            """
