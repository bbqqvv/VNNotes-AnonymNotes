import json
import os
import sys
import threading
import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QDockWidget, 
    QApplication, QStackedWidget, QTabWidget, QSplitter, QToolBar,
    QMessageBox, QLabel, QSizePolicy, QSlider, QSystemTrayIcon, QMenu, QFileDialog,
    QFrame
)
from PyQt6.QtGui import QAction, QFont, QIcon, QDesktopServices, QTextCursor, QColor, QPixmap, QPainter
from PyQt6.QtCore import Qt, QUrl, QSize, QTimer, pyqtSlot, QMetaObject, Q_ARG, QByteArray, QPoint, QEvent
from PyQt6 import QtCore
from PyQt6.QtWebEngineWidgets import QWebEngineView




# Consolidating color icon updates into MenuToolbarManager
def _update_color_btn(btn, color: QColor, main_window=None, btn_type="text"):
    """Draw a colored underline bar as the button icon — theme aware."""
    try:
        mtm = getattr(main_window, 'menu_toolbar_manager', None)
        if mtm:
            # Senior Fix: Update the manager's state so it survives theme changes/redraws
            mtm.set_swatch_color(btn_type, color)
    except Exception as e:
        logging.error(f"MainWindow: Failed to update color icon: {e}")

from src.features.notes.note_pane import NotePane
from src.features.clipboard.clipboard_manager import ClipboardManager
from src.ui.branding import BrandingOverlay
from src.ui.managers.dock_manager import DockManager
from src.ui.managers.menu_toolbar_manager import MenuToolbarManager
from src.ui.managers.find_manager import FindManager
from src.ui.managers.visibility_manager import VisibilityManager
from src.ui.managers.tab_manager import TabManager
from src.ui.managers.dialog_manager import DialogManager
from src.ui.managers.status_bar_manager import StatusBarManager
from src.core.context import ServiceContext
from src.core.session_manager import SessionManager
from src.ui.sidebar import SidebarWidget
from src.ui.managers.theme_manager import ThemeManager
from src.ui.quick_switcher import QuickSwitcher

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ctx = ServiceContext.get_instance()
        self.config = self.ctx.config
        self.setWindowTitle("VNNotes")
        
        # Paths
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        icon_path = os.path.join(self.base_path, "logo.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # State
        self._active_pane = None
        self.current_theme = self.config.get_value("app/theme", "dark")
        
        # Core Managers
        self.dock_manager = DockManager(self)
        self.menu_manager = MenuToolbarManager(self)
        self.theme_manager = ThemeManager(self, self.config, self.base_path)
        self.session_manager = SessionManager(self, self.ctx)
        self.clipboard_manager = ClipboardManager()
        self._is_restoring = False
        self._active_dock = None 
        self.status_bar_manager = StatusBarManager(self)
        
        # RESTORED INITIALIZATION CALL
        self.late_init()
        
    @property
    def active_pane(self):
        """Diamond-Standard: Safely access the active pane, guarding against C++ deletion."""
        if self._active_pane is None:
            return None
        try:
            # Check if the underlying C++ object is still alive
            # If deleted, PyQt6 will raise a RuntimeError on most attribute accesses
            _ = self._active_pane.parent()
            return self._active_pane
        except (RuntimeError, AttributeError):
            self._active_pane = None
            return None

    @active_pane.setter
    def active_pane(self, value):
        self._active_pane = value
        
    def late_init(self):
        # Feature Managers (extracted for maintainability)
        self.find_manager = FindManager(self)
        self.visibility_manager = VisibilityManager(self)
        self.tab_manager = TabManager(self)
        self.dialog_manager = DialogManager(self)
        
        # Shortcuts to services from context
        self.note_service = self.ctx.notes
        self.browser_service = self.ctx.browser
        
        # Setup UI
        self.setup_window()
        self.setup_ui()
        self.setup_stealth()
        self.setup_tray()
        
        # Final Setup
        self.setup_status_bar_widgets()
        
        # Hook tab bars after dock changes (single-shot, re-triggered by dock_manager)
        self.tab_hook_timer = QTimer(self)
        self.tab_hook_timer.setSingleShot(True)
        self.tab_hook_timer.timeout.connect(self.hook_tab_bars)
        self.tab_hook_timer.start(500)  # Initial hook after setup
        
        # Signal Debouncing (Phase 3: Realtime UI Sync)
        # 1. UI-Only Sync (Title/Sidebar): High frequency (100ms) for "Realtime" feel
        self._ui_sync_timer = QTimer(self)
        self._ui_sync_timer.setSingleShot(True)
        self._ui_sync_timer.timeout.connect(self._do_ui_sync)
        
        # 2. Heavy Tasks (Auto-save): Low frequency (1000ms) for stability during massive edits
        self._content_change_timer = QTimer(self)
        self._content_change_timer.setSingleShot(True)
        self._content_change_timer.timeout.connect(self._do_on_content_changed)
        
        # Status bar updates are now signal-driven (connected in set_active_pane)
        # No polling timer needed — cursorPositionChanged fires on every keystroke/click

        
        # Restore State (Synchronous Atomic Flow - Senior Standard)
        self.session_manager.restore_app_state()
        
        if self.session_manager:
             self.session_manager.start_autosave()

        # SENIOR SAFETY: Watchdog for Sidebar Release (Global Event Filter is too unreliable for splitters)
        self._sidebar_watchdog = QTimer(self)
        self._sidebar_watchdog.setInterval(50)
        self._sidebar_watchdog.timeout.connect(self._check_sidebar_release_watchdog)

        # Check for updates
        # QTimer.singleShot(3000, lambda: self.check_for_updates(manual=False))

        # Senior Fix: Delayed stability check for Sidebar width
        # This fixes the "Startup Glitch" where the sidebar restores to a near-0 width.
        QTimer.singleShot(1500, self._check_sidebar_stability)

    def _check_sidebar_stability(self):
        """Diamond-Standard: Ensures sidebar is at a usable width after startup settlement."""
        try:
            # Hardened: check for C++ object validity
            if self.sidebar_dock and self.sidebar_dock.isVisible() and self.sidebar_dock.width() < 185:
                logging.info("MainWindow: Sidebar too narrow after settlement, expanding...")
                target_w = getattr(self.sidebar, '_last_stable_width', 300)
                # Use resizeDocks ONLY after settlement for maximum stability
                self.resizeDocks([self.sidebar_dock], [int(target_w)], Qt.Orientation.Horizontal)
        except (RuntimeError, AttributeError) as e:
            logging.error(f"MainWindow: Sidebar stability check failed (likely deleted): {e}")

    def auto_save(self):
         self.session_manager.auto_save()

    def toggle_autosave(self):
        """Toggles the auto-save timer based on user action."""
        enabled = False
        if "autosave" in self.menu_manager.actions:
            autosave_act = self.menu_manager.actions.get("autosave")
            enabled = autosave_act.isChecked()
            
        self.session_manager.set_autosave_enabled(enabled)
            
        status = "Enabled" if enabled else "Disabled"
        self.statusBar().showMessage(f"Auto-Save {status}", 2000)

    def setup_window(self):
        # Reverted: Use standard OS decorations
        geo = self.config.get_value("window/geometry")
        if geo:
            try:
                geo_bytes = bytes.fromhex(geo)
                if len(geo_bytes) > 20: 
                    self.restoreGeometry(geo_bytes)
            except Exception:
                pass
            
        # Senior Root Cause Fix: Explicit maximization persistence
        # restoreGeometry is flaky with WindowState on multi-monitor/DPI changes.
        is_max = self.config.get_value("window/is_maximized", True)
        if isinstance(is_max, str): is_max = is_max.lower() == 'true'
        
        if is_max:
            self.setWindowState(Qt.WindowState.WindowMaximized)
        elif self.width() < 300 or self.height() < 300:
            self.resize(1280, 800)
            self.setDockNestingEnabled(True)
        self.setDocumentMode(True) # Senior Fix: Eliminates native padding/gap around docked tabs
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | 
                           QMainWindow.DockOption.AnimatedDocks |
                           QMainWindow.DockOption.GroupedDragging)
        
        # Top Tabs (IDE Standard) — apply to L/R areas only to prevent mask crashes
        for area in [Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea]:
            self.setTabPosition(area, QTabWidget.TabPosition.North)
        
        # Senior Fix: Full-Height Sidebar (V-Priority Layout)
        # Sets all 4 corners to belong to the Vertical (Left/Right) areas.
        # This prevents Bottom/Top docks from overlapping the Sidebar/Explorer.
        self.setCorner(Qt.Corner.TopLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.TopRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)


    def setup_ui(self):
        # Senior Fix: Use QStackedWidget as central to allow 0-pixel collapse
        self.central_stack = QStackedWidget(self)
        self.setCentralWidget(self.central_stack)
        
        # 1. Branding Overlay (Slot 0)
        self.branding = BrandingOverlay(self)
        self.central_stack.addWidget(self.branding)
        
        # 2. Empty collapse point (Slot 1)
        self.collapse_widget = QWidget()
        self.collapse_widget.setFixedSize(0, 0)
        self.central_stack.addWidget(self.collapse_widget)
        
        self.central_stack.setCurrentIndex(0)
        
        # 1.5 Flush-Left Snap Indicator (VSCode Style)
        # Global indicator that appears at the absolute left edge when sidebar is collapsed.
        self.snap_indicator = QFrame(self)
        self.snap_indicator.setObjectName("GlobalSnapIndicator")
        self.snap_indicator.setFixedWidth(2)
        self.snap_indicator.setStyleSheet("background-color: #007ACC;")
        self.snap_indicator.hide()
        
        # 2. Sidebar Setup
        self.sidebar = SidebarWidget(self.note_service, self)
        self.sidebar_dock = QDockWidget("Note Explorer", self)
        self.sidebar_dock.setObjectName("SidebarDock")
        self.sidebar_dock.setWidget(self.sidebar)
        
        # Sidebar: Flexible width for power users (up to 600px)
        self.sidebar_dock.setMinimumWidth(80)
        self.sidebar_dock.setMaximumWidth(600)

        # Senior Design Decision: Restrict Sidebar to LEFT area only.
        # This prevents it from being dragged to the RIGHT (Note area) and becoming a tab.
        self.sidebar_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)

        # Hide standard title bar to use custom EXPLORER header
        self.sidebar_dock.setTitleBarWidget(QWidget())
        
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock)
        
        # 3. Toolbar & Actions
        self.setup_actions()
        self.setup_toolbar()
        self.setup_menu()
        
        # Ensure data is loaded
        self.note_service.load_notes()
        
        # Connect Sidebar signals
        self.sidebar.note_selected.connect(self.on_sidebar_note_selected)
        self.sidebar.note_renamed.connect(self.on_note_renamed)
        self.sidebar.note_deleted.connect(self.on_note_deleted)
        self.sidebar.search_result_picked.connect(self.on_search_result_picked)
        
        # 4. Global Shortcuts
        search_act = QAction("Global Search", self)
        search_act.setShortcut("Ctrl+Shift+F")
        search_act.triggered.connect(self.focus_sidebar_search)
        self.addAction(search_act)
        
        # 5. Apply Theme
        self.theme_manager.apply_theme()
        
        QTimer.singleShot(100, self._setup_screen_listener)
        QTimer.singleShot(150, self._stabilize_layout)


    def _on_screen_changed(self, screen):
        """Handle screen DPI/scaling changes."""
        if not screen: return
        logging.info(f"Screen changed: {screen.name()}. Re-syncing layout.")
        QTimer.singleShot(500, self._stabilize_layout)

    def _setup_screen_listener(self):
        """Connects screen change signal to handle monitor moves."""
        handle = self.windowHandle()
        if handle:
            handle.screenChanged.connect(self._on_screen_changed)
            logging.info("Primary screen listener initialized.")

    def showEvent(self, event):
        """Initial show event to kick-start layout stabilization."""
        super().showEvent(event)
        # Sequence-based settling: Windows 11 maximization takes time to settle geometry.
        # One pass at 200ms is standard for DWM settlement.
        QTimer.singleShot(200, self._stabilize_layout)
        
        # Update snap indicator geometry
        self._update_snap_indicator_geometry()

    def resizeEvent(self, event):
        """Handle window resizing to keep indicators flush."""
        super().resizeEvent(event)
        self._update_snap_indicator_geometry()

    def _update_snap_indicator_geometry(self):
        """Keep the snap indicator flush with the left edge and full height."""
        if hasattr(self, 'snap_indicator'):
            self.snap_indicator.setGeometry(0, 0, 2, self.height())
            self.snap_indicator.raise_()
        # Removed infinite layout loop here

    def _stabilize_layout(self):
        """Forces a full layout refresh and synchronizes geometry."""
        # 0. Flush OS event queue
        QApplication.processEvents()
        
        # 1. Force the layout to discard cached constraints and re-activate
        mw_layout = self.layout()
        if mw_layout and hasattr(mw_layout, 'invalidate'):
            mw_layout.invalidate()
        if mw_layout and hasattr(mw_layout, 'activate'):
            mw_layout.activate()
            
        # 2. Refresh sidebar geometry
        if self.sidebar and hasattr(self.sidebar, 'tree') and self.sidebar.tree:
            self.sidebar.tree.updateGeometry()
            
        # 3. Refresh Branding
        if self.branding:
            self.update_branding_visibility()
            if hasattr(self.branding, '_update_elements'):
                getattr(self.branding, '_update_elements')()
            self.branding.update()

    def _on_screen_changed(self, screen):
        """Triggered when window moves to a different monitor."""
        logging.info(f"Screen changed: {screen.name()}. Re-applying theme and refreshing layout.")
        
        # 1. Re-apply theme to update QSS values
        self.theme_manager.apply_theme()
        
        # 2. Force layout recalculation
        if self.toolbar:
            self.toolbar.updateGeometry()
            tb_layout = self.toolbar.layout()
            if tb_layout and hasattr(tb_layout, 'invalidate'):
                tb_layout.invalidate()
            if tb_layout and hasattr(tb_layout, 'activate'):
                tb_layout.activate()
        
        # 3. FIX: Force sidebar to repaint and re-sync viewport
        if self.sidebar:
            self.sidebar.repaint()
            self.sidebar.tree.viewport().update()
        
        # 4. Persistence: Re-apply stealth and opacity which often "lose" their native effects on monitor switch
        if self.visibility_manager:
            vm = self.visibility_manager
            # Re-apply stealth (SetWindowDisplayAffinity)
            stealth_act = self.menu_manager.actions.get("stealth")
            if stealth_act:
                vm.toggle_stealth(stealth_act.isChecked())
            
            # Re-apply opacity (Layered Window attribute)
            vm.change_window_opacity(self.windowOpacity() * 100)
        
        # Removed Nudge logic for stability.

        # 6. Refresh window geometry to ensure everything snaps into place
        QApplication.processEvents()
        self._stabilize_layout() # Definitive settlement
        self.update()
        
        # 7. Safety: Ensure window is actually shown and not lost in virtual space
        if not self.isVisible():
            self.show()
        if self.isMinimized():
            self.showNormal()
        self.raise_()



    def focus_sidebar_search(self):
        """Toggles the sidebar search bar."""
        if self.sidebar_dock and self.sidebar:
            if not self.sidebar_dock.isVisible():
                self.sidebar_dock.show()
            
            # self.sidebar is the widget.
            if hasattr(self.sidebar, 'toggle_search'):
                self.sidebar.toggle_search()

    def setup_actions(self):
        self.menu_manager.setup_actions()

    def setup_toolbar(self):
        self.menu_manager.setup_toolbar()

    def setup_menu(self):
        self.menu_manager.setup_menu()

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        
        tray_menu = QMenu()
        show_act = QAction("Show/Hide", self)
        show_act.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(show_act)
        
        tray_menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_act)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()


    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_visibility()

    def quit_app(self):
        self.save_app_state()
        QApplication.quit()

    def _check_sidebar_release_watchdog(self):
        """Hardware-level polling to ensure the sidebar collapses and SAVES when the user lets go."""
        if not (QApplication.mouseButtons() & Qt.MouseButton.LeftButton):
            if hasattr(self, 'sidebar'):
                # Persistent Width: Commit the buffered RAM width to Disk (Disk I/O happens only ONCE here)
                current_w = self.sidebar._last_stable_width
                self.config.set_value("window/sidebar_width", current_w)
                logging.info(f"MainWindow: Watchdog saved stable width {current_w}px to config.")
                
                if getattr(self.sidebar, '_pending_collapse', False):
                    logging.info("MainWindow: Watchdog triggered collapse.")
                    self.sidebar._pending_collapse = False
                    self._sidebar_watchdog.stop()
                    QTimer.singleShot(50, self.toggle_sidebar)
                    return
            
            self._sidebar_watchdog.stop()

    def toggle_sidebar(self):
        """Native Qt visibility toggle using Nuclear Excision and DocumentMode to prevent ghost gaps."""
        logging.info("Toggling Sidebar visibility...")
        if not self.sidebar_dock:
            logging.error("Sidebar dock not found!")
            return

        is_visible = self.sidebar_dock.isVisible()
        # If it's mostly hidden (width < 10), treat as not visible
        if is_visible and self.sidebar_dock.width() < 10:
            is_visible = False

        if is_visible:
            # 1. Nuclear Excision: Completely remove the dock from the layout engine to PREVENT CRASHES.
            # This destroys the QSplitter handle cleanly while the user might still be dragging it.
            self.removeDockWidget(self.sidebar_dock)
            self.sidebar_dock.hide()
            
            # Frictionless Collapse constraints
            self.sidebar_dock.setMinimumWidth(0)
            self.sidebar_dock.setMaximumWidth(0)
            self.sidebar.updateGeometry()
            
            if hasattr(self, 'snap_indicator'):
                self.snap_indicator.show()
        else:
            if hasattr(self, 'snap_indicator'):
                self.snap_indicator.hide() 
                
            self.sidebar_dock.setMaximumWidth(600)
            
            # Senior Pivot: Use the exact buffered width. No arbitrary floors.
            target_w = getattr(self.sidebar, '_last_stable_width', 300)
            target_w = int(max(80, target_w)) # Minimum safety only
            self.sidebar_dock.setMinimumWidth(target_w)
            
            # 2. RE-DOCK: Must add the dock back to the layout engine
            from PyQt6.QtCore import Qt
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock)
            if self.sidebar_dock.isFloating():
                self.sidebar_dock.setFloating(False)
                
            self.sidebar_dock.show()
            self.sidebar_dock.raise_()
            
            self.resizeDocks([self.sidebar_dock], [int(target_w)], Qt.Orientation.Horizontal)
            
            def release_lockdown():
                try:
                    if self.sidebar_dock:
                        self.sidebar_dock.setMinimumWidth(80)
                except RuntimeError: pass
            
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, release_lockdown)
            
            self.sidebar.updateGeometry()

    # Branding and Visibility Management
    def update_branding_visibility(self):
        """Show branding only when no docks are visible."""
        # Clean list and check for visible docks
        visible_docks = []
        
        for dock in self.findChildren(QDockWidget):
            try:
                # Skip Sidebar and check visibility
                if dock.objectName() == "SidebarDock":
                    continue
                    
                if dock.isVisible():
                    visible_docks.append(dock)
            except RuntimeError:
                pass
        
        logging.debug(f"Branding Check: {len(visible_docks)} visible docks.")
        
        if visible_docks:
            # Hide the central widget completely
            if self.central_stack.isVisible():
                self.central_stack.setVisible(False)
        else:
            # Return to Branding splash
            self.central_stack.setCurrentIndex(0)
            if not self.central_stack.isVisible():
                self.central_stack.setVisible(True)
            self.branding.updateGeometry()
            self.branding.update()

    def check_docks_closed(self):
        self.update_branding_visibility()

    # --- File Management (Delegated) ---

    def save_file(self):
        self.dialog_manager.save_file()
    def save_file_as(self):
        self.dialog_manager.save_file_as()

    # --- Dock Management ---

    def add_note_dock(self, content="", title=None, obj_name=None, anchor_dock=None, file_path=None, zoom=100):
        if not obj_name and not self._is_restoring:
            # New note created by user: Get entity from service first
            note_data = self.note_service.add_note(title or "New Note", content)
            obj_name = note_data["obj_name"]
            title = note_data["title"]
            # content is already provided
        elif obj_name and not content:
            # Reopening an existing note (metadata exists, content might be separate)
            note_data = self.note_service.get_note_by_id(obj_name)
            if note_data:
                title = note_data.get("title", title)
                content = self.note_service.get_note_content(obj_name)
            
        dock = self.dock_manager.add_note_dock(content, title, obj_name, anchor_dock=anchor_dock, file_path=file_path, zoom=zoom)

        # Organic Fix: Softly nudge the sidebar back to its requested width
        # after Qt finishes redistributing the space from the hidden central widget.
        if not self._is_restoring and self.sidebar_dock and self.sidebar_dock.isVisible():
            target_w = getattr(self.sidebar, '_last_stable_width', 260)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, lambda: self.resizeDocks([self.sidebar_dock], [int(target_w)], Qt.Orientation.Horizontal))

        # Realtime Update for Sidebar (Skip during restoration)
        if not self._is_restoring and self.sidebar:
            self.sidebar.refresh_tree()
            
        return dock

    def add_browser_dock(self, url=None, anchor_dock=None, obj_name=None):
        if not url and not self._is_restoring:
            # New browser session
            browser_data = self.browser_service.add_browser()
            url = browser_data["url"]
            obj_name = browser_data["obj_name"]
            
        dock = self.dock_manager.add_browser_dock(url, anchor_dock=anchor_dock, obj_name=obj_name)
        
        # Organic Fix: Softly nudge the sidebar back
        if not self._is_restoring and self.sidebar_dock and self.sidebar_dock.isVisible():
            target_w = getattr(self.sidebar, '_last_stable_width', 260)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, lambda: self.resizeDocks([self.sidebar_dock], [int(target_w)], Qt.Orientation.Horizontal))
            
        return dock





    def add_clipboard_dock(self):
        self.dock_manager.add_clipboard_dock(self.clipboard_manager)

    def paste_from_clipboard(self, text):
        """Sets system clipboard and inserts into active note if possible."""
        # 1. Update system clipboard
        self.clipboard_manager.clipboard.setText(text)
        
        # 2. Insert into active note
        if self.active_pane and isinstance(self.active_pane, NotePane):
            self.active_pane.insertPlainText(text)
            self.statusBar().showMessage("Pasted from clipboard history", 2000)
            self.active_pane.setFocus()
        else:
            self.statusBar().showMessage("Copied to clipboard (Open a note to paste)", 2000)

    def set_active_pane(self, pane):
        # If switching to a different pane, close find bar for the old one
        if self.active_pane != pane:
            self.find_manager.close()
            # Disconnect signals from old pane
            old = self.active_pane
            if old:
                try:
                    if hasattr(old, 'cursor_format_changed'):
                        old.cursor_format_changed.disconnect(self._on_cursor_format_changed)
                except Exception:
                    pass
                try:
                    old.cursorPositionChanged.disconnect(self.update_status_bar_info)
                except Exception:
                    pass
                
        self.active_pane = pane
        if not pane:
            self._active_dock = None
            return
            
        # Cache the parent dock to avoid findChildren loops
        for dock in self.findChildren(QDockWidget):
            if not self._is_dock_deleted(dock) and dock.widget() == pane:
                self._active_dock = dock
                break
        
        # Connect signals: cursor format (toolbar sync) + cursor position (status bar)
        if hasattr(pane, 'cursor_format_changed'):
            try:
                pane.cursor_format_changed.connect(self._on_cursor_format_changed)
            except Exception:
                pass
        try:
            pane.cursorPositionChanged.connect(self.update_status_bar_info)
        except Exception:
            pass

    def _on_cursor_format_changed(self, char_fmt):
        """Update toolbar font size combo and color swatches when cursor moves."""
        mtm = getattr(self, 'menu_toolbar_manager', None)
        if not mtm:
            return
        # Update font size combo
        size_combo = getattr(mtm, 'font_size_combo', None)
        if size_combo:
            pt = char_fmt.fontPointSize()
            size_val = int(pt) if pt > 0 else 13  # default 13
            size_combo.blockSignals(True)
            size_combo.setCurrentText(str(size_val))
            size_combo.blockSignals(False)

        # Update text color swatch (Theme-aware default)
        color_btn = getattr(mtm, 'text_color_btn', None)
        if color_btn:
            fg = char_fmt.foreground().color()
            is_dark = self.theme_manager.is_dark_mode
            default_fg = QColor("white") if is_dark else QColor("black")
            _update_color_btn(color_btn, fg if (fg.isValid() and fg.alpha() > 10) else default_fg, self, "text")

        # Update highlight color swatch
        hl_btn = getattr(mtm, 'highlight_color_btn', None)
        if hl_btn:
            bg = char_fmt.background().color()
            _update_color_btn(hl_btn, bg if (bg.isValid() and bg.alpha() > 10) else QColor("transparent"), self, "highlight")

    def apply_format(self, fmt_type):
        if self.active_pane:
            self.active_pane.apply_format(fmt_type)

    def apply_font_size(self, size: int):
        if self.active_pane:
            self.active_pane.set_font_size(size)

    def pick_text_color(self):
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QTextCursor as _TC
        if not self.active_pane: return
        
        saved_cursor = _TC(self.active_pane.textCursor())
        initial = saved_cursor.charFormat().foreground().color()
        
        # UX Fix: If current color is invalid, hidden, or pure black, 
        # default to a vibrant color so hue/saturation changes are visible immediately.
        # This prevents the native brightness slider from zeroing out.
        if not initial.isValid() or initial.alpha() < 10 or initial.value() == 0:
            initial = QColor("#ff4757") # Vibrant coral/red
        
        dlg = QColorDialog(initial, self)
        dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)
        dlg.setWindowTitle("Choose Text Color")
        mtm = getattr(self, 'menu_toolbar_manager', None)
        
        def on_preview(color):
            if mtm and hasattr(mtm, 'text_color_btn'):
                _update_color_btn(mtm.text_color_btn, color, self)
        
        dlg.currentColorChanged.connect(on_preview)
        if dlg.exec():
            color = dlg.selectedColor()
            self.active_pane.setTextCursor(saved_cursor)
            self.active_pane.set_text_color(color)
            if mtm and hasattr(mtm, 'text_color_btn'):
                _update_color_btn(mtm.text_color_btn, color, self)
        else:
            # Restore original icon if cancelled
            if mtm and hasattr(mtm, 'text_color_btn'):
                _update_color_btn(mtm.text_color_btn, initial, self)

    def pick_highlight_color(self):
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QTextCursor as _TC
        if not self.active_pane: return
        
        saved_cursor = _TC(self.active_pane.textCursor())
        initial = saved_cursor.charFormat().background().color()
        if not initial.isValid() or initial.alpha() < 10 or initial.value() == 0: 
            initial = QColor("yellow")
        
        dlg = QColorDialog(initial, self)
        dlg.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)
        dlg.setWindowTitle("Choose Highlight Color")
        mtm = getattr(self, 'menu_toolbar_manager', None)
        
        def on_preview(color):
            if mtm and hasattr(mtm, 'highlight_color_btn'):
                _update_color_btn(mtm.highlight_color_btn, color, self)
        
        dlg.currentColorChanged.connect(on_preview)
        if dlg.exec():
            color = dlg.selectedColor()
            self.active_pane.setTextCursor(saved_cursor)
            self.active_pane.set_highlight_color(color)
            if mtm and hasattr(mtm, 'highlight_color_btn'):
                _update_color_btn(mtm.highlight_color_btn, color, self)
        else:
            # Restore original icon if cancelled
            if mtm and hasattr(mtm, 'highlight_color_btn'):
                _update_color_btn(mtm.highlight_color_btn, initial, self)

    def insert_image_to_active_note(self):
        if self.active_pane and hasattr(self.active_pane, 'insert_image_from_file'):
            self.active_pane.insert_image_from_file()

    # --- Persistence ---
    def save_current_work(self):
        """Manual save triggered by user"""
        self.session_manager.save_app_state()
        self.statusBar().showMessage("Saved successfully!", 2000)

    def save_app_state(self):
        self.session_manager.save_app_state()

    @pyqtSlot()
    def on_content_changed(self):
        """ENTRY POINT: Triggered on every keystroke. Restarts dual-debounce timers."""
        if getattr(self, '_is_restoring', False):
            return
        # Start both timers: UI sync is near-realtime, Auto-save is on a cooling cycle
        self._ui_sync_timer.start(100)
        self._content_change_timer.start(1000)

    def _do_ui_sync(self):
        """REALTIME UI WORKER: Surgical updates to Title and Sidebar (Zero-Copy)."""
        pane = self.active_pane
        dock = self._active_dock
        
        # Guard: If cache is lost or mismatch, re-sync once
        if not dock or self._is_dock_deleted(dock) or dock.widget() != pane:
            self._active_dock = None
            for d in self.findChildren(QDockWidget):
                if not self._is_dock_deleted(d) and d.widget() == pane:
                    self._active_dock = d
                    dock = d
                    break
        
        if isinstance(pane, NotePane) and dock:
             # Performance optimization: extract only the first block/line without full text copy
             doc = pane.document()
             first_block = doc.begin()
             first_line = first_block.text().strip()[:30] if first_block.isValid() else ""
             
             if not first_line: first_line = "Untitled"
             
             if dock.windowTitle() != first_line:
                 dock.setWindowTitle(first_line)
                 if self.sidebar:
                     self.sidebar.update_note_title(pane.objectName(), first_line)

    def _do_on_content_changed(self):
        """DEBOUNCED WORKER: Triggers heavy auto-save after longer typing pauses."""
        autosave_enabled = self.config.get_value("app/autosave_enabled", True)
        if isinstance(autosave_enabled, str):
            autosave_enabled = autosave_enabled.lower() == 'true'
            
        if autosave_enabled:
            # DIAMOND-STANDARD: Try incremental save first (just the active note)
            if self._active_dock:
                self.session_manager.save_single_note_state(self._active_dock)
            else:
                self.session_manager.start_autosave()

    def on_sidebar_note_selected(self, note_obj_name):
        """Opens or focuses a note selected from the sidebar."""
        # Check if already open
        for dock in self.findChildren(QDockWidget):
             if dock.objectName() == note_obj_name:
                 dock.show()
                 dock.raise_()
                 dock.setFocus()
                 return
        
        # If not open, restore it from Service
        logging.info(f"Restoring closed note: {note_obj_name}")
        note_data = self.note_service.get_note_by_id(note_obj_name)
        if note_data:
            # CORRECT: Call self.add_note_dock which handles distributed storage retrieval
            self.add_note_dock(content="", title=note_data.get("title", "Untitled"), obj_name=note_obj_name)
        else:
            logging.error(f"Could not find note data for {note_obj_name}")

    def on_search_result_picked(self, obj_name, query, line):
        """Handle search result click: open note, highlight match, scroll to it."""
        # First, open/focus the note using existing logic
        self.on_sidebar_note_selected(obj_name)
        
        # Then find the dock and highlight
        dock = self.findChild(QDockWidget, obj_name)
        if dock:
            pane = dock.widget()
            if hasattr(pane, 'highlight_search_result'):
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(150, lambda: pane.highlight_search_result(query, line))

    def _is_dock_deleted(self, dock):
        if not dock: return True
        try:
            # Accessing objectName will raise RuntimeError if deleted
            _ = dock.objectName()
            return False
        except (RuntimeError, AttributeError):
            return True

    def on_dock_destroyed(self, obj):
        """Globally invalidate the active dock cache if it was destroyed."""
        if self._active_dock == obj:
            self._active_dock = None
            self.active_pane = None

    def on_note_renamed(self, obj_name, new_title):
        """Updates Dock title when note is renamed via Sidebar."""
        try:
            # logging.info(f"on_note_renamed triggered for {obj_name} -> {new_title}")
            
            dock = self.findChild(QDockWidget, obj_name)
            if dock:
                dock.setWindowTitle(new_title)
            else:
                for d in self.findChildren(QDockWidget):
                    try:
                        if not self._is_dock_deleted(d) and d.objectName() == obj_name:
                            d.setWindowTitle(new_title)
                            return
                    except (RuntimeError, AttributeError): continue
        except Exception as e:
            logging.error(f"Error renaming dock: {e}")

    def on_note_deleted(self, obj_name):
        """Closes Dock when note is deleted via Sidebar."""
        try:
            dock = self.findChild(QDockWidget, obj_name)
            if dock and not self._is_dock_deleted(dock):
                dock.close()
            
            # Robust fallback lookup
            for d in self.findChildren(QDockWidget):
                try:
                    if not self._is_dock_deleted(d) and d.objectName() == obj_name:
                        d.close()
                except (RuntimeError, AttributeError):
                    pass
        except Exception as e:
            logging.error(f"Error deleting dock: {e}")

    def restore_app_state(self):
        self.session_manager.restore_app_state()

    # --- Delegated to FindManager ---
    def show_find_dialog(self):
        # ★ CRITICAL: Capture selection HERE, before focus shifts away from the note pane.
        # This is the very first thing called when Ctrl+F is pressed — the pane still
        # has its text cursor with the user's selection intact at this exact moment.
        pane = self.active_pane
        if pane and hasattr(pane, '_last_selection') and hasattr(pane, 'textCursor'):
            try:
                selected_text = pane.textCursor().selectedText()
                clean = selected_text.replace('\u2029', ' ').strip()
                if clean:
                    pane._last_selection = clean
            except Exception:
                pass
        self.find_manager.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.find_manager.reposition()
        
    # nativeEvent handler removed — window is not frameless, so WM_NCHITTEST was dead code

    def eventFilter(self, obj, event):
        if self.find_manager.handle_key_event(obj, event):
            return True
        return super().eventFilter(obj, event)

    # --- Quick Switcher ---
    def show_quick_switcher(self):
        """Displays the floating fuzzy-search note switcher."""
        if hasattr(self, 'quick_switcher'):
            self.quick_switcher.show_at_center(self)



    # --- Tab Grouping (Split View) ---
    def split_active_note(self, horizontal=True):
        """Splits the active note dock into a new group."""
        active_pane = self.active_pane
        if not active_pane: return
        
        # 1. Find the parent dock of the active pane
        from PyQt6.QtWidgets import QDockWidget
        source_dock = None
        curr = active_pane
        while curr:
            if isinstance(curr, QDockWidget):
                source_dock = curr
                break
            curr = curr.parentWidget()
            
        if not source_dock: return
        
        # 2. Find a neighbor dock (anchor) to split against
        # We look for another note dock in the same area
        docks = self.dock_manager.get_note_docks()
        anchor_dock = None
        for d in docks:
            if d != source_dock and d.isVisible():
                anchor_dock = d
                break
        
        if not anchor_dock:
            logging.info("Split View: No visible neighbor found. Opening new note to split.")
            self.on_new_note_triggered()
            return # User can split again once new note is visible

        # 3. Perform the Split
        orientation = Qt.Orientation.Horizontal if horizontal else Qt.Orientation.Vertical
        self.splitDockWidget(anchor_dock, source_dock, orientation)
        logging.info(f"Split View: Splitting {source_dock.objectName()} against {anchor_dock.objectName()}")

    # --- Delegated to VisibilityManager ---

    def setup_stealth(self):
        self.visibility_manager.setup_stealth()

    @pyqtSlot()
    def toggle_visibility(self):
        self.visibility_manager.toggle_visibility()

    def toggle_stealth(self, checked):
        self.visibility_manager.toggle_stealth(checked)

    @pyqtSlot()
    def toggle_ghost_click_external(self):
        self.visibility_manager.toggle_ghost_click_external()

    def toggle_ghost_click(self, checked):
        self.visibility_manager.toggle_ghost_click(checked)

    def toggle_always_on_top(self):
        self.visibility_manager.toggle_always_on_top()

    def change_window_opacity(self, value):
        self.visibility_manager.change_window_opacity(value)

    # --- Delegated to DialogManager ---

    def open_file_dialog(self):
        self.dialog_manager.open_file_dialog()

    def show_shortcuts_dialog(self):
        self.dialog_manager.show_shortcuts_dialog()

    def show_about_dialog(self):
        self.dialog_manager.show_about_dialog()

    def open_teleprompter(self):
        self.dialog_manager.open_teleprompter()

    def check_for_updates(self, manual=True):
        self.dialog_manager.check_for_updates(manual)

    def rename_active_note(self):
        self.dialog_manager.rename_active_note()

    def _show_rename_dialog(self, dock):
        self.dialog_manager.show_rename_dialog(dock)

    # --- Delegated to TabManager ---

    def hook_tab_bars(self):
        self.tab_manager.hook_tab_bars()

    def close_active_tab(self):
        self.tab_manager.close_active_tab()

    def reopen_last_closed_tab(self):
        self.tab_manager.reopen_last_closed_tab()

    # --- Delegated to StatusBarManager ---

    def setup_status_bar_widgets(self):
        self.status_bar_manager.setup_widgets()
        # Create convenience references for backward compatibility
        self.status_pos_label = self.status_bar_manager.status_pos_label
        self.status_char_label = self.status_bar_manager.status_char_label
        self.status_zoom_label = self.status_bar_manager.status_zoom_label
        self.status_eol_label = self.status_bar_manager.status_eol_label
        self.status_enc_label = self.status_bar_manager.status_enc_label

    def update_status_bar_info(self):
        self.status_bar_manager.update_info()

    def setup_tray(self):
        """Standard System Tray hook with show/hide toggle."""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        
        tray_menu = QMenu()
        show_act = QAction("Show/Hide", self)
        show_act.triggered.connect(self.toggle_visibility)
        tray_menu.addAction(show_act)
        
        exit_act = QAction("Exit VNNotes", self)
        exit_act.triggered.connect(self.close)
        tray_menu.addAction(exit_act)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def closeEvent(self, event):
        self.save_app_state()
        super().closeEvent(event)



