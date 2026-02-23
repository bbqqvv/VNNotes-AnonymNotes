"""
Compact Find Bar that overlays the top-right corner of the editor.
Theme-aware: adapts to dark/light mode from MainWindow.current_theme.
Auto-expanding input: grows vertically when long text is pasted (like VS Code).
"""
import logging
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPlainTextEdit,
                              QToolButton, QLabel, QGraphicsDropShadowEffect,
                              QSizePolicy, QDockWidget)
from PyQt6.QtGui import QTextCursor, QTextDocument, QColor, QFontMetrics, QIcon
from PyQt6.QtCore import Qt, QEvent, QSize

from src.utils.ui_utils import get_icon

logger = logging.getLogger(__name__)

# ── Theme palettes ────────────────────────────────────────────────────
DARK = {
    "bg": "#2b2b2b", "surface": "#333333", "text": "#eeeeee", "accent": "#3498db", "border": "#444444"
}
LIGHT = {
    "bg": "#ffffff", "surface": "#f3f4f6", "text": "#1f2937", "accent": "#2563eb", "border": "#e2e8f0"
}

MIN_INPUT_HEIGHT = 28
MAX_INPUT_HEIGHT = 120  # Max ~6 lines before scrolling

def _build_stylesheet(c):
    is_dark = c.get("is_dark", True)
    # High contrast force
    text_color = "#ffffff" if is_dark else "#000000"
    
    colors = {
        "bar_bg": c.get("surface", "#2b2b2b"),
        "border": c.get("border", "#444444"),
        "input_bg": c.get("bg", "#3a3a3a"),
        "text": text_color,
        "focus": c.get("accent", "#3498db"),
        "btn_hover": c.get("bg", "#3a3a3a"),
        "label_color": text_color,
        "close_hover": "#ef4444"
    }
    
    return f"""
    #FindBar {{
        background: {colors['bar_bg']};
        border: 1px solid {colors['border']};
        border-radius: 8px;
        padding: 4px;
    }}
    #FindInput {{
        background: {colors['input_bg']};
        color: {colors['text']};
        border: 1px solid {colors['border']};
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 13px;
        font-family: 'Consolas', 'Segoe UI', monospace;
    }}
    #FindInput[error="true"] {{
        border-color: #ef4444;
    }}
    #FindInput:focus {{
        border: 1px solid {colors['focus']};
        background: {colors['input_bg']};
    }}
    #FindBar QToolButton {{ 
        background: transparent; 
        border: 1px solid transparent;
        border-radius: 4px; 
        padding: 2px; 
        color: {colors['text']};
        font-weight: bold;
    }}
    #FindBar QToolButton:hover {{ 
        background: {colors['btn_hover']};
        border-color: {colors['border']};
    }}
    #FindBar QToolButton:checked {{ 
        background: {colors['focus']}; 
        color: white; 
        border-color: {colors['focus']};
    }}
    #FindBar QToolButton#closeBtn:hover {{ 
        background: {colors['close_hover']}; 
        color: white; 
    }}
    #FindBar QLabel#matchLabel {{ 
        color: {colors['focus']}; 
        font-size: 13px;
        font-weight: bold;
        padding: 0 10px;
    }}
    """


class FindManager:
    """Compact Find Bar overlaying the top-right of the active editor."""

    def __init__(self, main_window):
        self.mw = main_window
        self._find_bar = None
        self._find_input = None
        self._match_label = None
        self._btn_case = None
        self._btn_word = None
        self._find_current_index = 0
        self._find_total = 0

    def show(self):
        if not self.mw.active_pane:
            return
            
        if self._find_bar is None:
            self._create_find_bar()
        
        target_parent = self.mw
        dock = self._get_active_dock()
        if dock and dock.isFloating():
            target_parent = dock
            
        if self._find_bar and self._find_bar.parent() != target_parent:
            self._find_bar.setParent(target_parent)
            self._apply_theme()

        self._apply_theme()
        
        pane = self.mw.active_pane
        if pane and hasattr(pane, '_last_selection') and pane._last_selection:
            self._find_input.setPlainText(pane._last_selection)
        elif pane and hasattr(pane, 'textCursor'):
            try:
                selected_text = pane.textCursor().selectedText()
                clean_text = selected_text.replace('\u2029', ' ').strip()
                if clean_text:
                    self._find_input.setPlainText(clean_text)
            except Exception as e:
                logging.debug(f"FindManager: Could not auto-fill selection: {e}")

        self._find_bar.show()
        self._find_bar.raise_()
        self.reposition()
        self._find_input.setFocus()
        self._find_input.selectAll()

    def _get_active_dock(self):
        if not self.mw.active_pane: return None
        p = self.mw.active_pane.parent()
        while p:
            if isinstance(p, QDockWidget):
                return p
            p = p.parent()
        return None

    def close(self):
        if self._find_bar:
            self._find_bar.hide()
            if self.mw.active_pane:
                self.mw.active_pane.setFocus()

    def reposition(self):
        if not self._find_bar or not self._find_bar.isVisible():
            return
        
        bar = self._find_bar
        parent = bar.parent()
        
        # Wider for modern high-res screens
        bar_w = 600 
        bar_h = bar.sizeHint().height()

        right_margin = 15
        top_offset = 6 # Tighter alignment
        
        if parent == self.mw:
            top_offset = 64 
            
        x = parent.width() - bar_w - right_margin
        bar.setGeometry(max(10, x), top_offset, bar_w, bar_h)
        bar.setMinimumWidth(bar_w)

    def handle_key_event(self, obj, event):
        if self._find_input and obj == self._find_input:
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                modifiers = event.modifiers()
                if key == Qt.Key.Key_Escape:
                    self.close()
                    return True
                if key == Qt.Key.Key_V and (modifiers & Qt.KeyboardModifier.ControlModifier):
                    self._find_input.paste()
                    return True
                if key == Qt.Key.Key_A and (modifiers & Qt.KeyboardModifier.ControlModifier):
                    self._find_input.selectAll()
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    if modifiers & Qt.KeyboardModifier.ShiftModifier:
                        self._find_prev()
                    else:
                        self._find_next()
                    return True
        return False

    def _get_palette(self):
        if hasattr(self.mw, 'theme_manager'):
            tm = self.mw.theme_manager
            return tm.get_theme_palette()
        return DARK

    def _apply_theme(self):
        if self._find_bar:
            t = self._get_palette()
            self._find_bar.setStyleSheet(_build_stylesheet(t))
            shadow = self._find_bar.graphicsEffect()
            if shadow and isinstance(shadow, QGraphicsDropShadowEffect):
                shadow.setColor(QColor(0, 0, 0, 100 if self.mw.theme_manager.is_dark_mode else 40))
            
            # Refresh icons
            is_dark = self.mw.theme_manager.is_dark_mode
            self._btn_up.setIcon(get_icon("chevron-up.svg", is_dark))
            self._btn_down.setIcon(get_icon("chevron-down.svg", is_dark))
            self._btn_extract.setIcon(get_icon("clipboard.svg", is_dark))
            self._btn_close.setIcon(get_icon("close.svg", is_dark))

    def _create_find_bar(self):
        bar = QWidget(self.mw)
        bar.setObjectName("FindBar")

        shadow = QGraphicsDropShadowEffect(bar)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80))
        bar.setGraphicsEffect(shadow)

        main_layout = QHBoxLayout(bar)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(4)

        self._find_input = QPlainTextEdit(bar)
        self._find_input.setObjectName("FindInput")
        self._find_input.setPlaceholderText("Search notes...")
        self._find_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._find_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._find_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._find_input.setTabChangesFocus(True)
        self._find_input.setFixedHeight(MIN_INPUT_HEIGHT)
        self._find_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._find_input.textChanged.connect(self._on_text_changed)
        self._find_input.installEventFilter(self.mw)
        main_layout.addWidget(self._find_input, 1)

        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(2)

        self._btn_case = self._make_toggle("Aa", "Match Case", bar)
        self._btn_case.setStyleSheet("padding: 0 4px;") # Text-icons need breathing room
        controls_layout.addWidget(self._btn_case)

        self._btn_word = self._make_toggle("ab", "Whole Word", bar)
        self._btn_word.setStyleSheet("padding: 0 4px;")
        controls_layout.addWidget(self._btn_word)

        self._match_label = QLabel("", bar)
        self._match_label.setObjectName("matchLabel")
        self._match_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        controls_layout.addWidget(self._match_label)

        self._btn_up = self._make_btn("", "Previous (Shift+Enter)", bar)
        self._btn_up.clicked.connect(self._find_prev)
        controls_layout.addWidget(self._btn_up)

        self._btn_down = self._make_btn("", "Next (Enter)", bar)
        self._btn_down.clicked.connect(self._find_next)
        controls_layout.addWidget(self._btn_down)

        self._btn_extract = self._make_btn("", "Extract all matches", bar)
        self._btn_extract.clicked.connect(self._on_extract_clicked)
        controls_layout.addWidget(self._btn_extract)

        self._btn_close = self._make_btn("", "Close (Esc)", bar)
        self._btn_close.setObjectName("closeBtn")
        self._btn_close.clicked.connect(self.close)
        controls_layout.addWidget(self._btn_close)

        main_layout.addLayout(controls_layout)

        self._find_bar = bar
        self._find_bar.setParent(self.mw)
        self._find_bar.hide()

    def _make_btn(self, text, tooltip, parent):
        btn = QToolButton(parent)
        btn.setText(text)
        btn.setFixedSize(26, 26)
        btn.setToolTip(tooltip)
        btn.setIconSize(QSize(16, 16))
        return btn

    def _make_toggle(self, text, tooltip, parent):
        btn = QToolButton(parent)
        btn.setText(text)
        btn.setCheckable(True)
        btn.setFixedSize(26, 26)
        btn.setToolTip(tooltip)
        btn.toggled.connect(lambda _: self._on_text_changed())
        return btn

    def _adjust_input_height(self):
        doc = self._find_input.document()
        # Force a layout update to ensure size() is accurate
        doc.setTextWidth(self._find_input.viewport().width())
        doc_height = doc.size().height()
        
        # Add a bit of padding for margins
        new_h = int(doc_height + 8)
        clamped_h = max(MIN_INPUT_HEIGHT, min(new_h, MAX_INPUT_HEIGHT))
        
        if self._find_input.height() != clamped_h:
            self._find_input.setFixedHeight(clamped_h)
            self.reposition()
            # Ensure cursor is visible
            self._find_input.ensureCursorVisible()

    def _get_search_text(self):
        return self._find_input.toPlainText()

    def _on_text_changed(self):
        self._adjust_input_height()
        text = self._get_search_text()
        if not text:
            self._match_label.setText("")
            self._find_total = 0
            self._find_current_index = 0
            self._set_input_error(False)
            self.reposition()
            return
        self._count_matches(text)
        self._find_from_top(text)

    def _count_matches(self, text):
        if not self.mw.active_pane:
            self._find_total = 0
            return
        from src.features.notes.note_pane import NotePane
        if isinstance(self.mw.active_pane, NotePane):
            case_sensitive = self._btn_case and self._btn_case.isChecked()
            whole_words = self._btn_word and self._btn_word.isChecked()
            self._find_total = self.mw.active_pane.get_total_matches(text, case_sensitive, whole_words)
        else:
            content = self.mw.active_pane.toPlainText()
            case_sensitive = self._btn_case and self._btn_case.isChecked()
            if not case_sensitive:
                content = content.lower()
                text = text.lower()
            self._find_total = content.count(text)
        self._find_current_index = 0

    def _do_find(self, text, backward=False):
        if not self.mw.active_pane or not text:
            return False
        from src.features.notes.note_pane import NotePane
        if isinstance(self.mw.active_pane, NotePane):
            case_sensitive = self._btn_case and self._btn_case.isChecked()
            whole_words = self._btn_word and self._btn_word.isChecked()
            return self.mw.active_pane.find_global(text, backward, case_sensitive, whole_words)
        flags = QTextDocument.FindFlag(0)
        if backward: flags = flags | QTextDocument.FindFlag.FindBackward
        if self._btn_case and self._btn_case.isChecked(): flags = flags | QTextDocument.FindFlag.FindCaseSensitively
        if self._btn_word and self._btn_word.isChecked(): flags = flags | QTextDocument.FindFlag.FindWholeWords
        return self.mw.active_pane.find(text, flags)

    def _find_from_top(self, text):
        if not self.mw.active_pane or not text:
            return
        cursor = self.mw.active_pane.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.mw.active_pane.setTextCursor(cursor)
        if self._do_find(text):
            self._find_current_index = 1
        else:
            self._find_current_index = 0
        self._update_status()

    def _find_next(self):
        if not self.mw.active_pane: return
        text = self._get_search_text()
        if not text: return
        is_at_end = (self._find_current_index >= self._find_total and self._find_total > 0)
        if is_at_end or not self._do_find(text):
            cursor = self.mw.active_pane.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.mw.active_pane.setTextCursor(cursor)
            if self._do_find(text): self._find_current_index = 1
            else: self._find_current_index = 0
        else:
            self._find_current_index = min(self._find_current_index + 1, self._find_total)
        self._update_status()

    def _find_prev(self):
        if not self.mw.active_pane: return
        text = self._get_search_text()
        if not text: return
        is_at_start = (self._find_current_index <= 1 and self._find_total > 0)
        if is_at_start or not self._do_find(text, backward=True):
            cursor = self.mw.active_pane.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.mw.active_pane.setTextCursor(cursor)
            if self._do_find(text, backward=True): self._find_current_index = self._find_total
            else: self._find_current_index = 0
        else:
            self._find_current_index = max(self._find_current_index - 1, 1)
        self._update_status()

    def _update_status(self):
        text = self._get_search_text()
        if self._find_total == 0:
            self._match_label.setText("No results" if text else "")
            self._set_input_error(bool(text))
        else:
            self._match_label.setText(f"{self._find_current_index}/{self._find_total}")
            self._set_input_error(False)

    def _set_input_error(self, is_error):
        if self._find_input.property("error") != is_error:
            self._find_input.setProperty("error", is_error)
            self._find_input.style().unpolish(self._find_input)
            self._find_input.style().polish(self._find_input)

    def _on_extract_clicked(self):
        if not self.mw.active_pane: return
        text = self._get_search_text()
        if not text: return
        from src.features.notes.note_pane import NotePane
        if isinstance(self.mw.active_pane, NotePane):
            case_sensitive = self._btn_case and self._btn_case.isChecked()
            summary = self.mw.active_pane.paging_engine.get_matches_summary(text, case_sensitive)
            title = f"Search: {text}"
            self.mw.add_note_dock(content=summary, title=title)
