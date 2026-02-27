from PyQt6.QtWidgets import QToolBar, QMenu, QLabel, QWidget, QSizePolicy, QSlider, QComboBox, QPushButton, QHBoxLayout, QToolButton
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QAction
import os
import sys
import logging

class MenuToolbarManager:
    """
    Manages the application's Toolbar and Menu Bar.
    Handles Action creation, layout, and icon updates.
    """
    def __init__(self, main_window):
        self.main_window = main_window
        self.actions = {} # Store actions by name
        self.font_size_combo = None
        self.text_color_btn = None
        self.highlight_color_btn = None
        self.label_ghost = None
        self.opacity_label = None # To display percentage
        self.opacity_slider = None
        
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
                          lambda: self.main_window.toggle_sidebar(), icon="folder-open.svg")

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
        self.create_action("clear", "Clear Formatting", "Reset text to default (Ctrl+\\)", "Ctrl+\\",
                          lambda: self.main_window.apply_format("clear"), icon="refresh.svg")
        self.create_action("indent", "Increase Indent", "Increase indentation (Ctrl+])", "Ctrl+]",
                          lambda: self.main_window.active_pane.apply_indent(True) if self.main_window.active_pane else None, icon="redo.svg")
        self.create_action("outdent", "Decrease Indent", "Decrease indentation (Ctrl+[)", "Ctrl+[",
                          lambda: self.main_window.active_pane.apply_indent(False) if self.main_window.active_pane else None, icon="undo.svg")
        self.create_action("table", "Insert Table", "Insert Table at cursor (Ctrl+Alt+T)", "Ctrl+Alt+T",
                          lambda: self.main_window.apply_format("table"), icon="table.svg")
        
        # Alignment
        self.create_action("align-left", "Align Left", "Align Left (Ctrl+L)", "Ctrl+L",
                          lambda: self.main_window.apply_format("align-left"), icon="align-left.svg")
        self.create_action("align-center", "Align Center", "Align Center (Ctrl+E)", "Ctrl+E",
                          lambda: self.main_window.apply_format("align-center"), icon="align-center.svg")
        self.create_action("align-right", "Align Right", "Align Right (Ctrl+R)", "Ctrl+R",
                          lambda: self.main_window.apply_format("align-right"), icon="align-right.svg")
        self.create_action("align-justify", "Justify", "Justify (Ctrl+J)", "Ctrl+J",
                          lambda: self.main_window.apply_format("align-justify"), icon="align-justify.svg")
        self.create_action("insert-image", "Insert Image", "Insert Image (Ctrl+Alt+I)", "Ctrl+Alt+I",
                          self.main_window.insert_image_to_active_note, icon="image.svg")
        self.create_action("search", "Find", "Find in Note (Ctrl+F)", "Ctrl+F",
                          self.main_window.show_find_dialog)
        
        self.create_action("quick_switcher", "Quick Switcher", "Jump to any note (Ctrl+P)", "Ctrl+P",
                          self.main_window.show_quick_switcher, icon="search.svg")
        
        
        self.create_action("restore_grid", "Safe Grid Reset", "Tidy layout into Grid/Tabs (Respects tab stacks) (Ctrl+Alt+G)", "Ctrl+Alt+G",
                          self.main_window.restore_grid_layout, icon="table.svg")

        self.create_action("close_tab", "Close Tab", "Close Active Tab (Ctrl+W)", "Ctrl+W",
                          self.main_window.close_active_tab)
        self.create_action("close_all", "Close All Notes", "Close every open tab in the app", None,
                          self.main_window.tab_manager.close_all_tabs_app_wide)
        self.create_action("reopen_tab", "Reopen Closed Tab", "Reopen Last Closed Tab (Ctrl+Shift+T)", "Ctrl+Shift+T",
                          self.main_window.reopen_last_closed_tab)
        
        # Tab Navigation
        self.create_action("next_tab", "Next Tab", "Switch to Next Tab (Ctrl+Tab)", None,
                          self.main_window.tab_manager.switch_to_next_tab)
        self.create_action("prev_tab", "Previous Tab", "Switch to Previous Tab (Ctrl+Shift+Tab)", None,
                          self.main_window.tab_manager.switch_to_previous_tab)

        # --- Special Actions (Toggleable) ---
        # Ghost Actions
        ghost_act = QAction("Toggle Ghost Mode", self.main_window)
        ghost_act.setCheckable(True)
        ghost_act.setShortcut("Ctrl+Shift+G")
        ghost_act.triggered.connect(lambda checked: self.main_window.change_window_opacity(20 if checked else 100))
        self.actions["ghost_toggle"] = ghost_act

        ghost_click_act = QAction(self._icon("opacity.svg"), "Ghost Click (Click-Through)", self.main_window)
        ghost_click_act._icon_name = "opacity.svg"
        ghost_click_act.setCheckable(True)
        ghost_click_act.setShortcut("Ctrl+Shift+F9")
        ghost_click_act.setToolTip("Makes window transparent to mouse clicks. Use Hotkey to disable!")
        ghost_click_act.triggered.connect(self.main_window.toggle_ghost_click)
        self.actions["ghost_click"] = ghost_click_act
        
        # Stealth & Top
        stealth_act = QAction(self._icon("lock.svg"), "Super Stealth (Anti-Capture)", self.main_window)
        stealth_act._icon_name = "lock.svg"
        stealth_act.setCheckable(True)
        stealth_act.setChecked(False)
        stealth_act.setToolTip("Hides window from Screen Share/Recording (You can still see it)")
        stealth_act.setShortcut("Ctrl+Shift+S")
        stealth_act.triggered.connect(self.main_window.toggle_stealth)
        self.actions["stealth"] = stealth_act

        top_act = QAction(self._icon("top.svg"), "Always on Top", self.main_window)
        top_act._icon_name = "top.svg"
        top_act.setCheckable(True)
        top_act.setChecked(False)  # UX: Better to start off by default
        top_act.triggered.connect(self.main_window.toggle_always_on_top)
        self.actions["always_on_top"] = top_act
        
        # Help/Misc
        shortcuts_act = QAction("Keyboard Shortcuts", self.main_window)
        shortcuts_act.setShortcut("F1")
        shortcuts_act.triggered.connect(self.main_window.show_shortcuts_dialog)
        self.actions["shortcuts"] = shortcuts_act
        
        update_act = QAction(self._icon("refresh.svg"), "Check for Updates", self.main_window)
        update_act._icon_name = "refresh.svg"
        update_act.triggered.connect(self.main_window.check_for_updates)
        self.actions["update"] = update_act
        
        about_act = QAction(self._icon("note.svg"), "About VNNotes", self.main_window)
        about_act._icon_name = "note.svg"
        about_act.triggered.connect(self.main_window.show_about_dialog)
        self.actions["about"] = about_act

        # Auto-Save
        autosave_act = QAction("Auto-Save", self.main_window)
        autosave_act.setCheckable(True)
        autosave_act.setChecked(True) # Default on
        autosave_act.triggered.connect(self.main_window.toggle_autosave)
        self.actions["autosave"] = autosave_act

        # Editor View Features (Combined Dev Mode)
        devmode_act = QAction(self._icon("code.svg"), "Dev Mode", self.main_window)
        devmode_act.setToolTip("Enable Code Editor mode (Line Numbers, Minimap, No Text Wrap)")
        devmode_act.setCheckable(True)
        devmode_act.setChecked(self.main_window.config.get_value("editor/dev_mode", "false").lower() == "true")
        devmode_act.triggered.connect(self.main_window.toggle_dev_mode)
        self.actions["dev_mode"] = devmode_act

        # Theme Actions
        self.actions["themes"] = {} # Sub-dictionary for theme actions
        themes = self.main_window.theme_manager.THEME_CONFIG
        for theme_id in themes.keys():
            # Pretty name formatting (zinc -> Zinc)
            pretty_name = theme_id.replace("_", " ").title()
            theme_act = QAction(pretty_name, self.main_window)
            # Use closure to capture theme_id correctly
            theme_act.triggered.connect(lambda checked, t=theme_id: self.main_window.theme_manager.apply_theme(t))
            self.actions["themes"][theme_id] = theme_act
        
        # General Toggle Action (for shortcut) - Cycles through ALL available themes
        self.create_action("theme", "Cycle Themes", "Sequentially switch between all available color palettes", "Ctrl+T", 
                          self.main_window.theme_manager.toggle_theme, icon="theme.svg")

    def create_action(self, key, text, tooltip, shortcut, callback, icon=None):
        icon_name = icon if icon else f"{key}.svg"
        action = QAction(self._icon(icon_name), text, self.main_window)
        action._icon_name = icon_name # Store name for theme updates
        action.setToolTip(tooltip)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        self.actions[key] = action
        # Register on main window so keyboard shortcuts are globally active
        self.main_window.addAction(action)
        return action

    def setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setObjectName("MainToolBar") # Senior Fix: Required for QMainWindow.saveState()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        if toolbar.layout():
            toolbar.layout().setSpacing(4) # Prevent overlap
        self.main_window.addToolBar(toolbar)
        self.main_window.toolbar = toolbar
        
        # Core Group (Left): Clear and concise
        toolbar.addAction(self.actions["note"])
        toolbar.addAction(self.actions["browser"])
        toolbar.addAction(self.actions["prompter"])
        toolbar.addAction(self.actions["clipboard"])
        toolbar.addAction(self.actions["insert-image"])
        # Add Split Layout actions to toolbar for easy mouse access
        toolbar.addSeparator()
        toolbar.addAction(self.actions["restore_grid"])

        # Spacer Left
        spacer_left = QWidget()
        spacer_left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer_left)

        # â”€â”€ Font Size Combo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.font_size_combo = QComboBox()
        self.font_size_combo.setEditable(True)
        self.font_size_combo.setFixedSize(56, 24)
        self.font_size_combo.setToolTip("Font Size")
        sizes = ["8","9","10","11","12","13","14","16","18","20","24","28","32","36","48","72"]
        self.font_size_combo.addItems(sizes)
        self.font_size_combo.setCurrentText("13")
        # Only apply when user SELECTS from dropdown or presses ENTER (not each keystroke)
        self.font_size_combo.activated.connect(
            lambda idx: self._on_font_size_changed(self.font_size_combo.currentText())
        )
        self.font_size_combo.lineEdit().returnPressed.connect(
            lambda: self._on_font_size_changed(self.font_size_combo.currentText())
        )
        toolbar.addWidget(self.font_size_combo)

        # â”€â”€ Text Color Button â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        from PyQt6.QtGui import QColor as _QC, QPixmap as _QP, QPainter as _QPn, QFont as _QFo
        self.text_color_btn = QToolButton()
        self.text_color_btn.setAutoRaise(True)
        self.text_color_btn.setToolTip("Text Color")
        self.text_color_btn._letter = "A"
        self._draw_color_icon(self.text_color_btn, _QC("black"))
        self.text_color_btn.clicked.connect(self.main_window.pick_text_color)
        toolbar.addWidget(self.text_color_btn)

        # â”€â”€ Highlight Color Button â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.highlight_color_btn = QToolButton()
        self.highlight_color_btn.setAutoRaise(True)
        self.highlight_color_btn.setToolTip("Highlight Color")
        self.highlight_color_btn._letter = "H"
        self._draw_color_icon(self.highlight_color_btn, _QC("yellow"))
        self.highlight_color_btn.clicked.connect(self.main_window.pick_highlight_color)
        toolbar.addWidget(self.highlight_color_btn)

        # Alignment Group (Next to Formatting)
        toolbar.addAction(self.actions["align-left"])
        toolbar.addAction(self.actions["align-center"])
        toolbar.addAction(self.actions["align-right"])
        
        # â”€â”€â”€ Expanding Spacer (Push Search/Ghost to the right) â”€â”€â”€
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # â”€â”€â”€ Right Side Actions Group â”€â”€â”€
        right_container = QWidget()
        right_container.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        right_layout = QHBoxLayout(right_container)
        # Senior Fix: Force search cluster to hug the right edge within its assigned space
        right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # Senior Fix: 5px padding on the right as requested by user
        right_layout.setContentsMargins(4, 0, 5, 0) 
        right_layout.setSpacing(8)
        
        # 1. Search Icon
        search_btn = QToolButton()
        search_btn.setDefaultAction(self.actions["search"])
        search_btn.setFixedSize(22, 22) 
        # Alignment here matches the layout
        right_layout.addWidget(search_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 2. Opacity Cluster
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setFixedWidth(40) 
        self.opacity_slider.setToolTip("Window Opacity (Ctrl+Shift+G for Ghost Mode)")
        self.opacity_slider.valueChanged.connect(self.main_window.change_window_opacity)
        right_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("100%")
        self.opacity_label.setFixedWidth(30)
        self.opacity_label.setToolTip("Current Opacity %")
        self.opacity_label.setStyleSheet("font-size: 9px; color: gray;")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        right_layout.addWidget(self.opacity_label)
        
        # 3. Ghost Icon
        ghost_icon_label = QLabel()
        ghost_icon_label.setPixmap(self._icon("ghost.svg").pixmap(14, 14))
        ghost_icon_label.setToolTip("Ghost Mode Active")
        ghost_icon_label.setFixedSize(14, 14) 
        # Alignment here matches the layout
        right_layout.addWidget(ghost_icon_label)
        self.label_ghost = ghost_icon_label

        toolbar.addWidget(right_container)

        # Clean up toolbar layout
        if toolbar.layout():
            toolbar.layout().setContentsMargins(0, 0, 0, 0)
            toolbar.layout().setSpacing(0)
        
        toolbar.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)
        # Reset stylesheet to avoid overriding our custom layout
        toolbar.setStyleSheet("QToolBar { spacing: 0px; padding: 0px; border: none; }")

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
        file_menu.addAction(self.actions["close_all"])
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
        view_menu.addAction(self.actions["ghost_click"])

        view_menu.addSeparator()
        editor_menu = view_menu.addMenu("Editor")
        editor_menu.addAction(self.actions["dev_mode"])
        
        view_menu.addSeparator()
        view_menu.addSeparator()
        appearance_menu = view_menu.addMenu(self._icon("theme.svg"), "Appearance")
        
        theme_gallery = appearance_menu.addMenu("Theme Gallery")
        # Add themes in a specific order if preferred, or just loop
        for theme_id, act in self.actions["themes"].items():
            theme_gallery.addAction(act)
            
        appearance_menu.addSeparator()
        appearance_menu.addAction(self.actions["theme"])
        
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
        format_menu.addAction(self.actions["clear"])
        format_menu.addSeparator()
        format_menu.addAction(self.actions["indent"])
        format_menu.addAction(self.actions["outdent"])
        format_menu.addSeparator()
        format_menu.addAction(self.actions["table"])
        format_menu.addAction(self.actions["insert-image"])
        format_menu.addSeparator()
        format_menu.addAction(self.actions["align-left"])
        format_menu.addAction(self.actions["align-center"])
        format_menu.addAction(self.actions["align-right"])
        format_menu.addAction(self.actions["align-justify"])
        
        # Tools
        tools_menu = menubar.addMenu("Tools")
        tools_menu.addAction(self.actions["prompter"])
        tools_menu.addAction(self.actions["clipboard"])
        
        # Help
        help_menu = menubar.addMenu("Help")
        help_menu.addAction(self.actions["about"])
        help_menu.addSeparator()
        help_menu.addAction(self.actions["update"])
        
    def _icon(self, filename):
        return self.main_window.theme_manager.get_icon(filename)

    def update_icons(self):
        # Update all actions
        from PyQt6.QtGui import QAction, QColor
        for key, action in self.actions.items():
            if isinstance(action, QAction):
                icon_name = getattr(action, "_icon_name", f"{key}.svg")
                action.setIcon(self._icon(icon_name))
            elif isinstance(action, dict):
                # Handle nested theme dictionaries
                for t_key, t_act in action.items():
                    if isinstance(t_act, QAction):
                        icon_name = getattr(t_act, "_icon_name", "theme.svg")
                        t_act.setIcon(self._icon(icon_name))

        # Update theme-aware color icons
        is_dark = True
        if hasattr(self.main_window, 'theme_manager'):
            is_dark = self.main_window.theme_manager.is_dark_mode
        
        # White letter for dark theme, Dark Gray for light theme
        contrast_color = QColor(240, 240, 240) if is_dark else QColor(40, 40, 40)
        
        if self.text_color_btn:
            current_color = getattr(self, '_current_text_color', QColor("black"))
            self._draw_color_icon(self.text_color_btn, current_color, contrast_color)
            
        if self.highlight_color_btn:
            current_color = getattr(self, '_current_highlight_color', QColor("yellow"))
            self._draw_color_icon(self.highlight_color_btn, current_color, contrast_color)
            
    def set_swatch_color(self, btn_type, color):
        """Update internal state and redraw icon for A/H color buttons."""
        from PyQt6.QtGui import QColor
        if btn_type == "text":
            self._current_text_color = color
            if self.text_color_btn:
                self._draw_color_icon(self.text_color_btn, color)
        elif btn_type == "highlight":
            self._current_highlight_color = color
            if self.highlight_color_btn:
                self._draw_color_icon(self.highlight_color_btn, color)

        # Update static labels
        if self.label_ghost:
            self.label_ghost.setPixmap(self._icon("ghost.svg").pixmap(16, 16))

    def _on_font_size_changed(self, text: str):
        """Called when user picks or types a font size in the combo box."""
        try:
            size = int(text)
            if 1 <= size <= 400:
                self.main_window.apply_font_size(size)
        except ValueError:
            pass  # Ignore non-numeric input while the user is still typing

    @staticmethod
    def _draw_color_icon(btn, color, text_color=None):
        """Draw letter + colored underline bar as button icon (no circular import)."""
        from PyQt6.QtGui import QPixmap, QPainter, QFont as _QF, QColor, QIcon
        from PyQt6.QtCore import Qt, QSize
        
        # Determine contrast color if not provided
        if not text_color:
            # Try to detect theme from parent window
            is_dark = True
            try:
                win = btn.window()
                if hasattr(win, 'theme_manager'):
                    is_dark = win.theme_manager.is_dark_mode
                elif hasattr(win, 'current_theme'):
                    is_dark = "dark" in win.current_theme.lower()
            except Exception: pass
            text_color = QColor(240, 240, 240) if is_dark else QColor(40, 40, 40)

        letter = getattr(btn, '_letter', None) or "A"
        px = QPixmap(20, 20)
        px.fill(QColor(0, 0, 0, 0))
        p = QPainter(px)
        f = _QF()
        f.setBold(True)
        f.setPointSize(10) # Scaled for 20px
        p.setFont(f)
        
        p.setPen(text_color)
        # Centered vertically in 20x20 (Top=0, Height=20)
        p.drawText(0, 0, 20, 20, Qt.AlignmentFlag.AlignCenter, letter)
        
        bar_color = color if (color.isValid() and color.alpha() > 0) else QColor("transparent")
        # Bar anchored at bottom (Y=17) for clear visual underline
        p.fillRect(3, 17, 14, 2, bar_color)
        p.end()
        
        btn.setIcon(QIcon(px))
        btn.setIconSize(QSize(20, 20))
        
        # Update tooltip with Hex code for better UX
        if color.isValid() and color.alpha() > 0:
            hex_code = color.name().upper()
            base_tip = getattr(btn, '_base_tip', btn.toolTip().split(" (")[0])
            btn.setToolTip(f"{base_tip} ({hex_code})")
        else:
            base_tip = getattr(btn, '_base_tip', btn.toolTip().split(" (")[0])
            btn.setToolTip(base_tip)
