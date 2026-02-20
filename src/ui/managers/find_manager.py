"""
Compact Find Bar that overlays the top-right corner of the editor.
Theme-aware: adapts to dark/light mode from MainWindow.current_theme.
Auto-expanding input: grows vertically when long text is pasted (like VS Code).
"""
import logging
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPlainTextEdit,
                              QToolButton, QLabel, QGraphicsDropShadowEffect,
                              QSizePolicy)
from PyQt6.QtGui import QTextCursor, QTextDocument, QColor, QFontMetrics
from PyQt6.QtCore import Qt, QEvent

logger = logging.getLogger(__name__)

# ── Theme palettes ────────────────────────────────────────────────────
DARK = {
    "bg": "#2b2b2b", "border": "#444", "input_bg": "#3a3a3a",
    "input_text": "#eeeeee", "input_border": "#555",
    "focus": "#3498db", "btn_hover": "#3a3a3a", "btn_checked_border": "#3498db",
    "close_hover": "#c0392b", "label_color": "#999", "shadow": (0, 0, 0, 100),
    "no_match_bg": "#5a2020", "no_match_border": "#c0392b",
}
LIGHT = {
    "bg": "#ffffff", "border": "#e2e8f0", "input_bg": "#f9fafb",
    "input_text": "#1f2937", "input_border": "#cbd5e1",
    "focus": "#2563eb", "btn_hover": "#f3f4f6", "btn_checked_border": "#2563eb",
    "close_hover": "#fee2e2", "label_color": "#6b7280", "shadow": (0, 0, 0, 40),
    "no_match_bg": "#fee2e2", "no_match_border": "#ef4444",
}

MIN_INPUT_HEIGHT = 24
MAX_INPUT_HEIGHT = 120  # Max ~6 lines before scrolling


def _build_stylesheet(t):
    return f"""
    #FindBar {{
        background: {t['bg']};
        border: 1px solid {t['border']};
        border-radius: 5px;
        padding: 3px 5px;
    }}
    #FindInput {{
        background: {t['input_bg']};
        color: {t['input_text']};
        border: 1px solid {t['input_border']};
        border-radius: 3px;
        padding: 2px 6px;
        font-size: 13px;
        font-family: 'Consolas', 'Segoe UI', monospace;
    }}
    #FindInput:focus {{
        border-color: {t['focus']};
    }}
    #FindBar QToolButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 3px;
        padding: 1px;
        color: {t['input_text']};
        font-size: 12px;
        min-width: 22px;
        max-width: 22px;
        min-height: 22px;
        max-height: 22px;
    }}
    #FindBar QToolButton:hover {{
        background: {t['btn_hover']};
    }}
    #FindBar QToolButton:checked {{
        border-color: {t['btn_checked_border']};
    }}
    #FindBar QToolButton#closeBtn:hover {{
        background: {t['close_hover']};
    }}
    #FindBar QLabel#matchLabel {{
        color: {t['label_color']};
        font-size: 11px;
        font-family: 'Segoe UI', sans-serif;
        padding: 0 2px;
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

    # ── Public API ────────────────────────────────────────────────────

    def show(self):
        if not self.mw.active_pane:
            return
        if self._find_bar is None:
            self._create_find_bar()
        self._apply_theme()
        self._find_bar.show()
        self._find_bar.raise_()
        self.reposition()
        self._find_input.setFocus()
        self._find_input.selectAll()

    def close(self):
        if self._find_bar:
            self._find_bar.hide()
            if self.mw.active_pane:
                self.mw.active_pane.setFocus()

    def reposition(self):
        if not self._find_bar or not self._find_bar.isVisible():
            return
        bar = self._find_bar
        bar_w = 340  # Fixed width
        bar_h = bar.sizeHint().height()

        right_margin = 28
        top_offset = 62
        x = self.mw.width() - bar_w - right_margin
        bar.setGeometry(max(0, x), top_offset, bar_w, bar_h)

    def handle_key_event(self, obj, event):
        if self._find_input and obj == self._find_input:
            if event.type() == QEvent.Type.KeyPress:
                key = event.key()
                if key == Qt.Key.Key_Escape:
                    self.close()
                    return True
                # Enter/Return → find next (Shift+Enter → find prev)
                # But let plain Enter through only if NO modifiers (no newlines)
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                        self._find_prev()
                    else:
                        self._find_next()
                    return True
        return False

    # ── Theme ─────────────────────────────────────────────────────────

    def _get_palette(self):
        theme = getattr(self.mw, 'current_theme', 'dark')
        return LIGHT if theme == 'light' else DARK

    def _apply_theme(self):
        if self._find_bar:
            t = self._get_palette()
            self._find_bar.setStyleSheet(_build_stylesheet(t))
            shadow = self._find_bar.graphicsEffect()
            if shadow and isinstance(shadow, QGraphicsDropShadowEffect):
                r, g, b, a = t['shadow']
                shadow.setColor(QColor(r, g, b, a))

    # ── Build UI ──────────────────────────────────────────────────────

    def _create_find_bar(self):
        bar = QWidget(self.mw)
        bar.setObjectName("FindBar")

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(bar)
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 80))
        bar.setGraphicsEffect(shadow)

        # Main horizontal: [input] [controls column]
        main_layout = QHBoxLayout(bar)
        main_layout.setContentsMargins(5, 4, 5, 4)
        main_layout.setSpacing(4)

        # ── Auto-expanding text input ──
        self._find_input = QPlainTextEdit(bar)
        self._find_input.setObjectName("FindInput")
        self._find_input.setPlaceholderText("Search…")
        self._find_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._find_input.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._find_input.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._find_input.setTabChangesFocus(True)
        self._find_input.setFixedHeight(MIN_INPUT_HEIGHT)
        self._find_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._find_input.textChanged.connect(self._on_text_changed)
        self._find_input.installEventFilter(self.mw)
        main_layout.addWidget(self._find_input, 1)

        # ── Controls column (right side) ──
        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(2)

        # Top row: Aa, ab, match count, ↑, ↓, ✕
        top_row = QHBoxLayout()
        top_row.setSpacing(2)

        self._btn_case = self._make_toggle("Aa", "Match Case", bar)
        top_row.addWidget(self._btn_case)

        self._btn_word = self._make_toggle("ab", "Whole Word", bar)
        top_row.addWidget(self._btn_word)

        self._match_label = QLabel("", bar)
        self._match_label.setObjectName("matchLabel")
        self._match_label.setMinimumWidth(40)
        top_row.addWidget(self._match_label)

        btn_up = self._make_btn("↑", "Previous (Shift+Enter)", bar)
        btn_up.clicked.connect(self._find_prev)
        top_row.addWidget(btn_up)

        btn_down = self._make_btn("↓", "Next (Enter)", bar)
        btn_down.clicked.connect(self._find_next)
        top_row.addWidget(btn_down)

        btn_close = self._make_btn("✕", "Close (Esc)", bar)
        btn_close.setObjectName("closeBtn")
        btn_close.clicked.connect(self.close)
        top_row.addWidget(btn_close)

        controls_layout.addLayout(top_row)
        controls_layout.addStretch()

        main_layout.addLayout(controls_layout)

        self._find_bar = bar
        self._find_bar.setParent(self.mw)
        self._find_bar.hide()

    def _make_btn(self, text, tooltip, parent):
        btn = QToolButton(parent)
        btn.setText(text)
        btn.setFixedSize(22, 22)
        btn.setToolTip(tooltip)
        return btn

    def _make_toggle(self, text, tooltip, parent):
        btn = QToolButton(parent)
        btn.setText(text)
        btn.setCheckable(True)
        btn.setFixedSize(22, 22)
        btn.setToolTip(tooltip)
        btn.toggled.connect(lambda _: self._on_text_changed())
        return btn

    # ── Auto-expand input ─────────────────────────────────────────────

    def _adjust_input_height(self):
        """Grow/shrink the input based on content lines."""
        doc = self._find_input.document()
        fm = QFontMetrics(self._find_input.font())
        line_height = fm.lineSpacing()
        line_count = max(1, doc.blockCount())
        # content height + padding
        desired = int(line_count * line_height + 10)
        new_h = max(MIN_INPUT_HEIGHT, min(desired, MAX_INPUT_HEIGHT))
        if self._find_input.fixedHeight != new_h if hasattr(self._find_input, 'fixedHeight') else True:
            self._find_input.setFixedHeight(new_h)
            self.reposition()

    # ── Search logic ──────────────────────────────────────────────────

    def _get_search_text(self):
        """Get search text (first line only for multi-line paste, or all)."""
        return self._find_input.toPlainText()

    def _on_text_changed(self):
        self._adjust_input_height()
        text = self._get_search_text()
        if not text:
            self._match_label.setText("")
            self._find_total = 0
            self._find_current_index = 0
            self._find_input.setStyleSheet("")
            self.reposition()
            return
        self._count_matches(text)
        self._find_from_top(text)

    def _count_matches(self, text):
        if not self.mw.active_pane:
            self._find_total = 0
            return
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
        flags = QTextDocument.FindFlag(0)
        if backward:
            flags = flags | QTextDocument.FindFlag.FindBackward
        if self._btn_case and self._btn_case.isChecked():
            flags = flags | QTextDocument.FindFlag.FindCaseSensitively
        if self._btn_word and self._btn_word.isChecked():
            flags = flags | QTextDocument.FindFlag.FindWholeWords
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
        if not self.mw.active_pane:
            return
        text = self._get_search_text()
        if not text:
            return
        if not self._do_find(text):
            cursor = self.mw.active_pane.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.mw.active_pane.setTextCursor(cursor)
            if self._do_find(text):
                self._find_current_index = 1
            else:
                self._find_current_index = 0
        else:
            self._find_current_index = min(
                self._find_current_index + 1, self._find_total)
        self._update_status()

    def _find_prev(self):
        if not self.mw.active_pane:
            return
        text = self._get_search_text()
        if not text:
            return
        if not self._do_find(text, backward=True):
            cursor = self.mw.active_pane.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.mw.active_pane.setTextCursor(cursor)
            if self._do_find(text, backward=True):
                self._find_current_index = self._find_total
            else:
                self._find_current_index = 0
        else:
            self._find_current_index = max(
                self._find_current_index - 1, 1)
        self._update_status()

    def _update_status(self):
        text = self._get_search_text()
        t = self._get_palette()
        if self._find_total == 0:
            self._match_label.setText("No results" if text else "")
            if text:
                self._find_input.setStyleSheet(
                    f"QPlainTextEdit {{ background: {t['no_match_bg']}; "
                    f"border-color: {t['no_match_border']}; }}")
            else:
                self._find_input.setStyleSheet("")
        else:
            self._match_label.setText(
                f"{self._find_current_index} of {self._find_total}")
            self._find_input.setStyleSheet("")
