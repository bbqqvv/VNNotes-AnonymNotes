import sys
import logging
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QLineEdit, QListWidget, 
                             QListWidgetItem, QApplication, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QRect, QPoint
from PyQt6.QtGui import QColor, QFont
from PyQt6 import sip

class QuickSwitcher(QFrame):
    """
    A premium fuzzy-search switcher inspired by VS Code (Ctrl+P).
    Floating, semi-transparent, and keyboard-driven.
    """
    note_selected = pyqtSignal(str) # Emits note objectName

    def __init__(self, parent=None):
        super().__init__(parent)
        # Frameless and Always on Top of its own application
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.setup_ui()
        self.installEventFilter(self)
        
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        # Container for Glassmorphism
        self.container = QFrame()
        self.container.setObjectName("SwitcherContainer")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        # Search Box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search notes... (Enter to go, Esc to close)")
        self.search_box.setFrame(False)
        self.search_box.setObjectName("SwitcherSearch")
        self.search_box.textChanged.connect(self.filter_results)
        self.container_layout.addWidget(self.search_box)
        
        # Results List
        self.results_list = QListWidget()
        self.results_list.setFrame(False)
        self.results_list.setObjectName("SwitcherResults")
        self.results_list.itemActivated.connect(self.on_item_activated)
        
        # Key interception for QListWidget
        self.results_list.installEventFilter(self)
        
        self.container_layout.addWidget(self.results_list)
        
        self.layout.addWidget(self.container)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 15)
        self.container.setGraphicsEffect(shadow)

    def apply_theme(self, theme_palette):
        """Standardizes look across all themes."""
        is_dark = theme_palette.get("is_dark", True)
        bg = theme_palette["surface"]
        border = theme_palette["border"]
        text = theme_palette["text"]
        accent = theme_palette["accent"]
        hover = theme_palette["hover"]
        
        # Semi-transparent background for glass effect
        rgba_bg = QColor(bg)
        rgba_bg.setAlpha(245)
        rgba_bg_str = f"rgba({rgba_bg.red()}, {rgba_bg.green()}, {rgba_bg.blue()}, {rgba_bg.alpha()})"
        
        style = f"""
            #SwitcherContainer {{
                background: {rgba_bg_str};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            #SwitcherSearch {{
                background: transparent;
                color: {text};
                font-family: 'Segoe UI', sans-serif;
                font-size: 16px;
                padding: 16px;
                border-bottom: 1px solid {border};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
            #SwitcherResults {{
                background: transparent;
                color: {text};
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                outline: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                padding: 6px;
            }}
            #SwitcherResults::item {{
                padding: 12px 16px;
                border-radius: 6px;
                margin: 2px 6px;
                background: transparent;
            }}
            #SwitcherResults::item:selected {{
                background: {accent};
                color: white;
            }}
            #SwitcherResults::item:hover {{
                background: {hover};
            }}
        """
        self.setStyleSheet(style)

    def show_at_center(self, main_window):
        self.populate_notes(main_window)
        
        # Dimensions
        w = 600
        h = 450
        
        # Center on parent window
        geo = main_window.geometry()
        center = geo.center()
        
        self.setFixedSize(w, h)
        self.move(center.x() - w // 2, geo.y() + 150) # Elevated position
        
        # Visual Refresh
        if hasattr(main_window, 'theme_manager'):
            self.apply_theme(main_window.theme_manager.get_theme_palette())
        
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_box.setFocus()
        self.search_box.selectAll()

    def populate_notes(self, main_window):
        self.results_list.clear()
        self.all_notes = []
        
        from PyQt6.QtWidgets import QDockWidget
        # 1. Active Docks (opened notes)
        opened_ids = set()
        for dock in main_window.findChildren(QDockWidget):
            try:
                if sip.isdeleted(dock): continue
                obj_name = dock.objectName()
                if obj_name.startswith("NoteDock_"):
                    title = dock.windowTitle()
                    self.all_notes.append({"title": title, "id": obj_name, "isOpen": True})
                    opened_ids.add(obj_name)
            except RuntimeError: continue
        
        # 2. Closed Notes (from Sidebar/NoteService)
        if hasattr(main_window, 'sidebar') and hasattr(main_window.sidebar, 'note_items'):
            for note_id, item in main_window.sidebar.note_items.items():
                if note_id not in opened_ids:
                    title = item.text()
                    self.all_notes.append({"title": title, "id": note_id, "isOpen": False})
        
        self.filter_results("")

    def filter_results(self, text):
        self.results_list.clear()
        query = text.lower().strip()
        
        for note in self.all_notes:
            if not query or query in note["title"].lower():
                display_text = note["title"]
                if note["isOpen"]:
                    # Small indicator for open tabs
                    display_text = f"â— {note['title']}"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, note["id"])
                
                if note["isOpen"]:
                    # Muted color for open indicator label
                    item.setForeground(QColor("#a1a1aa")) 
                
                self.results_list.addItem(item)
        
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)

    def on_item_activated(self, item):
        note_id = item.data(Qt.ItemDataRole.UserRole)
        self.note_selected.emit(note_id)
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
        elif event.key() in [Qt.Key.Key_Down, Qt.Key.Key_Up]:
            # Forward navigation keys to the list
            self.results_list.setFocus()
            QApplication.sendEvent(self.results_list, event)
        elif event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
            item = self.results_list.currentItem()
            if item:
                self.on_item_activated(item)
            event.accept()
        else:
            super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        # Close on loss of focus
        if event.type() == QEvent.Type.WindowDeactivate:
            # We use a small delay to avoid flicker if focus is just shifting internally
            QTimer.singleShot(100, self.hide)
            return False
            
        # Intercept keys in search box to navigate list
        if obj == self.search_box and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Down:
                self.results_list.setCurrentRow(min(self.results_list.currentRow() + 1, self.results_list.count() - 1))
                return True
            elif event.key() == Qt.Key.Key_Up:
                self.results_list.setCurrentRow(max(0, self.results_list.currentRow() - 1))
                return True
                
        return super().eventFilter(obj, event)

from PyQt6.QtCore import QTimer
