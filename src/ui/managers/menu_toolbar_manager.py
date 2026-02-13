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

        self.create_action("open", "Open File", "Open File (Ctrl+O)", "Ctrl+O",
                          self.main_window.open_file_dialog, icon="folder-open.svg")
                          
        self.create_action("clipboard", "Clipboard", "Clipboard History (Ctrl+Shift+V)", "Ctrl+Shift+V",
                          self.main_window.add_clipboard_dock)

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
        self.create_action("image", "Image", "Insert Image (Ctrl+Shift+I)", "Ctrl+Shift+I",
                          lambda: self.main_window.insert_image_to_active_note())
        self.create_action("search", "Find", "Find in Note (Ctrl+F)", "Ctrl+F",
                          self.main_window.show_find_dialog)

        # --- Special Actions (Toggleable) ---
        # Ghost Actions
        self.ghost_act = QAction("Toggle Ghost Mode", self.main_window)
        self.ghost_act.setCheckable(True)
        self.ghost_act.setShortcut("Ctrl+Shift+G")
        self.ghost_act.triggered.connect(lambda checked: self.main_window.change_window_opacity(20 if checked else 100))
        self.actions["ghost_toggle"] = self.ghost_act

        self.ghost_click_act = QAction("Ghost Click (Click-Through)", self.main_window)
        self.ghost_click_act.setCheckable(True)
        self.ghost_click_act.setShortcut("Ctrl+Shift+F9")
        self.ghost_click_act.setToolTip("Makes window transparent to mouse clicks. Use Hotkey to disable!")
        self.ghost_click_act.triggered.connect(self.main_window.toggle_ghost_click)
        self.actions["ghost_click"] = self.ghost_click_act
        
        # Stealth & Top
        self.stealth_act = QAction("Super Stealth (Anti-Capture)", self.main_window)
        self.stealth_act.setCheckable(True)
        self.stealth_act.setChecked(True)
        self.stealth_act.setToolTip("Hides window from Screen Share/Recording (You can still see it)")
        self.stealth_act.setShortcut("Ctrl+Shift+S")
        self.stealth_act.triggered.connect(self.main_window.toggle_stealth)
        self.actions["stealth"] = self.stealth_act
        
        self.top_act = QAction("Always on Top", self.main_window)
        self.top_act.setCheckable(True)
        self.top_act.setChecked(True)
        self.top_act.triggered.connect(self.main_window.toggle_always_on_top)
        self.actions["always_on_top"] = self.top_act
        
        # Help/Misc
        self.shortcuts_act = QAction("Keyboard Shortcuts", self.main_window)
        self.shortcuts_act.setShortcut("F1")
        self.shortcuts_act.triggered.connect(self.main_window.show_shortcuts_dialog)
        self.actions["shortcuts"] = self.shortcuts_act
        
        self.update_act = QAction("Check for Updates", self.main_window)
        self.update_act.triggered.connect(self.main_window.check_for_updates)
        self.actions["update"] = self.update_act

    def create_action(self, key, text, tooltip, shortcut, callback, icon=None):
        icon_name = icon if icon else f"{key}.svg"
        action = QAction(self._icon(icon_name), text, self.main_window)
        action.setToolTip(tooltip)
        action.setShortcut(shortcut)
        action.triggered.connect(callback)
        self.actions[key] = action
        return action

    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.main_window.addToolBar(toolbar)
        
        # Add Actions
        toolbar.addAction(self.actions["note"])
        toolbar.addAction(self.actions["browser"])
        toolbar.addAction(self.actions["prompter"])
        toolbar.addAction(self.actions["open"])
        toolbar.addAction(self.actions["clipboard"])
        toolbar.addSeparator()
        
        # Formatting (subset)
        toolbar.addAction(self.actions["image"])
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        # Search
        toolbar.addAction(self.actions["search"])
        
        toolbar.addSeparator()
        
        # Opacity Slider
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(80)
        self.opacity_slider.setToolTip("Ghost Mode (Opacity) [Ctrl+Shift+G]")
        self.opacity_slider.valueChanged.connect(self.main_window.change_window_opacity)
        toolbar.addWidget(self.opacity_slider)
        
        # Ghost Label
        self.label_ghost = QLabel()
        self.label_ghost.setPixmap(self._icon("ghost.svg").pixmap(16, 16))
        self.label_ghost.setToolTip("Ghost Mode")
        toolbar.addWidget(self.label_ghost)

    def setup_menu(self):
        menubar = self.main_window.menuBar()
        menubar.clear() # Clear existing if re-initializing
        
        # File
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self.actions["open"])
        file_menu.addSeparator()
        exit_act = QAction("Exit", self.main_window)
        exit_act.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_act)
        
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
        
        # Tools
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction(self.actions["prompter"])
        tools_menu.addAction(self.actions["clipboard"])
        tools_menu.addAction(self.actions["image"])
        
        # Help
        help_menu = menubar.addMenu("Help")
        shortcuts_act = QAction("Keyboard Shortcuts", self.main_window)
        shortcuts_act.setShortcut("F1")
        shortcuts_act.triggered.connect(self.main_window.show_shortcuts_dialog)
        help_menu.addAction(shortcuts_act)
        
    def _icon(self, filename):
        # ... logic to get icon ...
        # Since this logic is duplicated, maybe move to a util or pass from main window
        # For now, replicate or call main_window._icon if public
        return self.main_window._icon(filename)

    def update_icons(self):
        # Update all actions
        for key, action in self.actions.items():
            icon_name = f"{key}.svg"
            # specific mapping if needed
            if key == "open": icon_name = "folder-open.svg"
            if key == "prompter": icon_name = "teleprompter.svg"
            
            action.setIcon(self._icon(icon_name))
            
        if hasattr(self, 'label_ghost'):
             self.label_ghost.setPixmap(self._icon("ghost.svg").pixmap(16, 16))
