from PyQt6.QtWidgets import QToolBar, QMenu, QLabel, QWidget, QSizePolicy, QSlider
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction
import os
import sys

class MenuToolbarManager:
    """
    Manages the application's Toolbar and Menu Bar.
    Handles Action creation, layout, and icon updates.
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self.actions = {} # Store actions by name
        
    def setup_actions(self):
        """Creates all QActions and stores them."""
        # --- Core Actions ---
        self.create_action("note", "Note", "Add Note Dock (Ctrl+N)", "Ctrl+N", 
                          lambda: self.main_window.add_note_dock())
        
        self.create_action("browser", "Browser", "Add Mini Browser (Ctrl+Shift+B)", "Ctrl+Shift+B",
                          lambda: self.main_window.add_browser_dock())
                          
        self.create_action("prompter", "Prompter", "Open Teleprompter (Ctrl+Shift+P)", "Ctrl+Shift+P",
                          self.main_window.open_teleprompter, icon="teleprompter.svg")

        self.create_action("open", "Open File", "Open File / Word Document (Ctrl+O)", "Ctrl+O",
                          self.main_window.open_file_dialog, icon="folder-open.svg")

        self.create_action("save", "Save", "Save current note (Ctrl+S)", "Ctrl+S", 
                          self.main_window.save_file, icon="folder-add.svg")

        self.create_action("save_as", "Save As...", "Export note to a different file", "Ctrl+Alt+S",
                          self.main_window.save_file_as, icon="folder-add.svg")
                          
        self.create_action("clipboard", "Clipboard", "Clipboard History (Ctrl+Shift+V)", "Ctrl+Shift+V",
                          self.main_window.add_clipboard_dock)
                          
        self.create_action("sidebar", "Page Bar", "Toggle Sidebar (Ctrl+Shift+E)", "Ctrl+Shift+E",
                          lambda: self.main_window.toggle_sidebar(), icon="sidebar.svg")

        # --- Formatting ---
        self.create_action("bold", "Bold", "Bold (Ctrl+B)", "Ctrl+B",
                          lambda: self.main_window.apply_format("bold"))
        self.create_action("italic", "Italic", "Italic (Ctrl+I)", "Ctrl+I",
                          lambda: self.main_window.apply_format("italic"))
        self.create_action("underline", "Underline", "Underline (Ctrl+U)", "Ctrl+U",
                          lambda: self.main_window.apply_format("underline"))
        self.create_action("list", "List", "Bullet List (Ctrl+Shift+L)", "Ctrl+Shift+L",
                          lambda: self.main_window.apply_format("list"))
        self.create_action("check", "Task", "Checkbox / Todo (Ctrl+Shift+C)", "Ctrl+Shift+C",
                          lambda: self.main_window.apply_format("checkbox"))
        self.create_action("code", "Code", "Code Block (Ctrl+Shift+K)", "Ctrl+Shift+K",
                          lambda: self.main_window.apply_format("code"))
        self.create_action("highlight", "Highlight", "Highlight Text (Ctrl+H)", "Ctrl+H",
                          lambda: self.main_window.apply_format("highlight"))
        
        # Alignment
        self.create_action("align-left", "Align Left", "Align Left (Ctrl+L)", "Ctrl+L",
                          lambda: self.main_window.apply_format("align-left"), icon="align-left.svg")
        self.create_action("align-center", "Align Center", "Align Center (Ctrl+E)", "Ctrl+E",
                          lambda: self.main_window.apply_format("align-center"), icon="align-center.svg")
        self.create_action("align-right", "Align Right", "Align Right (Ctrl+R)", "Ctrl+R",
                          lambda: self.main_window.apply_format("align-right"), icon="align-right.svg")
        self.create_action("align-justify", "Justify", "Justify (Ctrl+J)", "Ctrl+J",
                          lambda: self.main_window.apply_format("align-justify"), icon="align-justify.svg")
        self.create_action("image", "Image", "Insert Image (Ctrl+Shift+I)", "Ctrl+Shift+I",
                          lambda: self.main_window.insert_image_to_active_note())
        self.create_action("search", "Find", "Find in Note (Ctrl+F)", "Ctrl+F",
                          self.main_window.show_find_dialog)

        self.create_action("close_tab", "Close Tab", "Close Active Tab (Ctrl+W)", "Ctrl+W",
                          self.main_window.close_active_tab)
        self.create_action("reopen_tab", "Reopen Closed Tab", "Reopen Last Closed Tab (Ctrl+Shift+T)", "Ctrl+Shift+T",
                          self.main_window.reopen_last_closed_tab)

        # --- Special Actions (Toggleable) ---
        # Ghost Actions
        ghost_act = QAction("Toggle Ghost Mode", self.main_window)
        ghost_act.setCheckable(True)
        ghost_act.setShortcut("Ctrl+Shift+G")
        ghost_act.triggered.connect(lambda checked: self.main_window.change_window_opacity(20 if checked else 100))
        self.actions["ghost_toggle"] = ghost_act

        ghost_click_act = QAction("Ghost Click (Click-Through)", self.main_window)
        ghost_click_act.setCheckable(True)
        ghost_click_act.setShortcut("Ctrl+Shift+F9")
        ghost_click_act.setToolTip("Makes window transparent to mouse clicks. Use Hotkey to disable!")
        ghost_click_act.triggered.connect(self.main_window.toggle_ghost_click)
        self.actions["ghost_click"] = ghost_click_act
        
        # Stealth & Top
        stealth_act = QAction(self._icon("lock.svg"), "Super Stealth (Anti-Capture)", self.main_window)
        stealth_act.setCheckable(True)
        stealth_act.setChecked(True)
        stealth_act.setToolTip("Hides window from Screen Share/Recording (You can still see it)")
        stealth_act.setShortcut("Ctrl+Shift+S")
        stealth_act.triggered.connect(self.main_window.toggle_stealth)
        self.actions["stealth"] = stealth_act
        
        top_act = QAction(self._icon("top.svg"), "Always on Top", self.main_window)
        top_act.setCheckable(True)
        top_act.setChecked(True)
        top_act.triggered.connect(self.main_window.toggle_always_on_top)
        self.actions["always_on_top"] = top_act
        
        # Help/Misc
        shortcuts_act = QAction("Keyboard Shortcuts", self.main_window)
        shortcuts_act.setShortcut("F1")
        shortcuts_act.triggered.connect(self.main_window.show_shortcuts_dialog)
        self.actions["shortcuts"] = shortcuts_act
        
        update_act = QAction("Check for Updates", self.main_window)
        update_act.triggered.connect(self.main_window.check_for_updates)
        self.actions["update"] = update_act
        
        about_act = QAction("About VNNotes", self.main_window)
        about_act.triggered.connect(self.main_window.show_about_dialog)
        self.actions["about"] = about_act

        # Auto-Save
        autosave_act = QAction("Auto-Save", self.main_window)
        autosave_act.setCheckable(True)
        autosave_act.setChecked(True) # Default on
        autosave_act.triggered.connect(self.main_window.toggle_autosave)
        self.actions["autosave"] = autosave_act

        # Theme Actions
        theme_dark_act = QAction("Dark Mode", self.main_window)
        theme_dark_act.triggered.connect(lambda: self.main_window.theme_manager.apply_theme("dark"))
        self.actions["theme_dark"] = theme_dark_act

        theme_light_act = QAction("Light Mode", self.main_window)
        theme_light_act.triggered.connect(lambda: self.main_window.theme_manager.apply_theme("light"))
        self.actions["theme_light"] = theme_light_act
        
        # General Toggle Action (for shortcut)
        self.create_action("theme", "Toggle Theme", "Switch between Light and Dark mode", "Ctrl+T", 
                          self.main_window.theme_manager.toggle_theme, icon="theme.svg")

    def create_action(self, key, text, tooltip, shortcut, callback, icon=None):
        icon_name = icon if icon else f"{key}.svg"
        action = QAction(self._icon(icon_name), text, self.main_window)
        action.setToolTip(tooltip)
        action.setShortcut(shortcut)
        action.triggered.connect(callback)
        self.actions[key] = action
        # Register on main window so keyboard shortcuts are globally active
        self.main_window.addAction(action)
        return action

    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.main_window.addToolBar(toolbar)
        
        # Core Group (Left)
        toolbar.addAction(self.actions["note"])
        toolbar.addAction(self.actions["browser"])
        toolbar.addAction(self.actions["prompter"])
        # Removed Open action from toolbar per user request
        toolbar.addAction(self.actions["clipboard"])
        toolbar.addAction(self.actions["image"])
        
        # Spacer Left
        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer_left)

        # Alignment Group (Center)
        toolbar.addAction(self.actions["align-left"])
        toolbar.addAction(self.actions["align-center"])
        toolbar.addAction(self.actions["align-right"])
        
        # Spacer Right
        spacer_right = QWidget()
        spacer_right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer_right)

        # Search
        toolbar.addAction(self.actions["search"])
        
        toolbar.addSeparator()
        
        # Opacity Slider
        opacity_slider = QSlider(Qt.Orientation.Horizontal)
        opacity_slider.setRange(20, 100)
        opacity_slider.setValue(100)
        opacity_slider.setFixedWidth(80)
        opacity_slider.setToolTip("Ghost Mode (Opacity) [Ctrl+Shift+G]")
        opacity_slider.valueChanged.connect(self.main_window.change_window_opacity)
        toolbar.addWidget(opacity_slider)
        
        # Ghost Label
        label_ghost = QLabel()
        label_ghost.setPixmap(self._icon("ghost.svg").pixmap(16, 16))
        label_ghost.setToolTip("Ghost Mode")
        toolbar.addWidget(label_ghost)

    def setup_menu(self):
        menubar = self.main_window.menuBar()
        menubar.clear() # Clear existing if re-initializing
        
        # File
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self.actions["open"])
        file_menu.addAction(self.actions["save"])
        file_menu.addAction(self.actions["save_as"])
        file_menu.addSeparator()
        file_menu.addAction(self.actions["close_tab"])
        file_menu.addAction(self.actions["reopen_tab"])
        file_menu.addSeparator()
        if "autosave" in self.actions:
            file_menu.addAction(self.actions["autosave"])
        file_menu.addSeparator()
        exit_act = QAction("Exit", self.main_window)
        exit_act.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_act)

        # View
        view_menu = menubar.addMenu("View")
        # Add dock management toggles automatically
        dock_menu = self.main_window.createPopupMenu()
        if dock_menu:
            for action in dock_menu.actions():
                view_menu.addAction(action)
            view_menu.addSeparator()
        
        if "sidebar" in self.actions:
            view_menu.addAction(self.actions["sidebar"])
            
        view_menu.addAction(self.actions["stealth"])
        view_menu.addAction(self.actions["always_on_top"])
        view_menu.addAction(self.actions["ghost_toggle"])
        view_menu.addAction(self.actions["ghost_click"])
        
        view_menu.addSeparator()
        theme_menu = view_menu.addMenu(self._icon("theme.svg"), "Appearance")
        theme_menu.addAction(self.actions["theme_dark"])
        theme_menu.addAction(self.actions["theme_light"])
        theme_menu.addSeparator()
        theme_menu.addAction(self.actions["theme"])
        
        # Format
        format_menu = menubar.addMenu("Format")
        format_menu.addAction(self.actions["bold"])
        format_menu.addAction(self.actions["italic"])
        format_menu.addAction(self.actions["underline"])
        format_menu.addSeparator()
        format_menu.addAction(self.actions["list"])
        format_menu.addAction(self.actions["check"])
        format_menu.addAction(self.actions["code"])
        format_menu.addAction(self.actions["highlight"])
        format_menu.addSeparator()
        format_menu.addAction(self.actions["align-left"])
        format_menu.addAction(self.actions["align-center"])
        format_menu.addAction(self.actions["align-right"])
        format_menu.addAction(self.actions["align-justify"])
        
        # Tools
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction(self.actions["prompter"])
        tools_menu.addAction(self.actions["clipboard"])
        tools_menu.addAction(self.actions["image"])
        
        # Help
        help_menu = menubar.addMenu("Help")
        help_menu.addAction(self.actions["about"])
        help_menu.addSeparator()
        help_menu.addAction(self.actions["update"])
        
    def _icon(self, filename):
        return self.main_window.theme_manager.get_icon(filename)

    def update_icons(self):
        # Update all actions
        for key, action in self.actions.items():
            icon_name = f"{key}.svg"
            # specific mapping
            if key == "open": icon_name = "folder-open.svg"
            if key == "prompter": icon_name = "teleprompter.svg"
            if key == "stealth": icon_name = "lock.svg"
            if key == "always_on_top": icon_name = "top.svg"
            if key == "ghost_toggle": icon_name = "ghost.svg"
            if key == "ghost_click": icon_name = "ghost.svg" # Reuse same icon or different?
            if key == "theme": icon_name = "theme.svg"
            
            action.setIcon(self._icon(icon_name))
