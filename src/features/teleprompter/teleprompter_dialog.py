import logging
import os
import re
import base64
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QHBoxLayout,
    QPushButton, QSlider, QLabel, QWidget, QFrame, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QIcon, QTextCursor, QTextCharFormat, QImage
from PyQt6.QtCore import QUrl
from src.utils.ui_utils import get_icon_dir, get_icon


# Default palette (zinc) — used when no theme config is passed
_DEFAULT_THEME = {
    "bg": "#09090b", "surface": "#18181b", "border": "#27272a",
    "text": "#f4f4f5", "text_muted": "#a1a1aa", "accent": "#3b82f6",
    "is_dark": True
}


class TeleprompterDialog(QDialog):
    """Premium, theme-aware Stealth Teleprompter."""

    def __init__(self, text_content="", parent=None, theme_config=None):
        super().__init__(parent)
        try:
            logging.info("Initializing TeleprompterDialog...")
            self.setWindowTitle("Stealth Teleprompter")
            self.resize(720, 480)

            # Theme
            self.tc = theme_config or _DEFAULT_THEME

            # Window Flags: Frameless, Always on Top
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            # Enable Stealth (Anti-Capture)
            from src.core.stealth import StealthManager
            hwnd = int(self.winId())
            StealthManager.set_stealth_mode(hwnd, True)
            StealthManager.set_click_through(hwnd, False)

            # State
            self.scroll_speed = 2
            self.is_playing = False
            self.font_size = 24
            self.opacity_val = 0.85
            self.is_click_through = False

            # Icon paths
            is_dark = self.tc.get("is_dark", True)
            self.icon_dir = get_icon_dir(is_dark)

            # Scroll timer
            self.scroll_timer = QTimer(self)
            self.scroll_timer.timeout.connect(self._scroll_step)
            self.scroll_timer.setInterval(50)

            self._build_ui(text_content)
            self._setup_drag()

            # Fade-in animation
            self.setWindowOpacity(0.0)
            self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
            self._fade_anim.setDuration(250)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(self.opacity_val)
            self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_anim.start()

            logging.info("TeleprompterDialog initialized successfully.")
        except Exception as e:
            logging.critical(f"Failed to initialize TeleprompterDialog: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to open Teleprompter: {e}")

    # ── UI Construction ──────────────────────────────────────────────

    def _build_ui(self, content):
        tc = self.tc
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Main Glass Frame ──
        self.bg_frame = QFrame(self)
        self.bg_frame.setObjectName("HudFrame")
        self._apply_frame_style(locked=False)

        inner = QVBoxLayout(self.bg_frame)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setFixedHeight(40)
        header.setStyleSheet(f"""
            QFrame {{
                background: {tc['surface']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom: 1px solid {tc['border']};
            }}
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 0, 8, 0)
        h_layout.setSpacing(8)

        # Drag Handle
        self.drag_handle = QLabel()
        drag_path = os.path.join(self.icon_dir, "drag_handle.svg")
        if os.path.exists(drag_path):
            self.drag_handle.setPixmap(QIcon(drag_path).pixmap(32, 32))
            self.drag_handle.setFixedSize(16, 16)
            self.drag_handle.setScaledContents(True)
        else:
            self.drag_handle.setText("::")
        self.drag_handle.setStyleSheet("background: transparent;")
        self.drag_handle.setToolTip("Drag to move")
        self.drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)

        # Title
        self.title_lbl = QLabel("TELEPROMPTER")
        self.title_lbl.setStyleSheet(f"""
            color: {tc['text_muted']};
            font-family: 'Inter', 'Segoe UI Variable', 'Segoe UI', sans-serif;
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.1em;
            background: transparent;
        """)

        # Play state indicator dot
        self.state_dot = QLabel("●")
        self.state_dot.setStyleSheet(f"color: {tc['text_muted']}; font-size: 8px; background: transparent;")

        # Lock button
        is_dark = tc.get("is_dark", True)
        self.btn_lock = self._make_header_btn("lock.svg", "Enable Click-Through (Ctrl+Shift+F9)", is_dark=is_dark)
        self.btn_lock.setCheckable(True)
        self.btn_lock.toggled.connect(self._toggle_click_through)

        # Close button
        self.btn_close = self._make_header_btn("close.svg", "Close", is_dark=is_dark, is_close=True)
        self.btn_close.clicked.connect(self.close)

        h_layout.addWidget(self.drag_handle)
        h_layout.addSpacing(4)
        h_layout.addWidget(self.title_lbl)
        h_layout.addSpacing(4)
        h_layout.addWidget(self.state_dot)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_lock)
        h_layout.addWidget(self.btn_close)

        # ── Text Area ──
        self.text_edit = QTextEdit()
        self._set_html_safe(content)
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {tc['text']};
                font-family: 'Inter', 'Segoe UI Variable', 'Segoe UI', sans-serif;
                font-size: {self.font_size}px;
                padding: 16px 20px;
                line-height: 1.8;
            }}
        """)

        # ── Controls Pill ──
        self.controls = QWidget()
        self.controls.setFixedHeight(46)
        self.controls.setStyleSheet(f"""
            QWidget {{
                background: {tc['surface']};
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                border-top: 1px solid {tc['border']};
            }}
        """)
        c_layout = QHBoxLayout(self.controls)
        c_layout.setContentsMargins(16, 0, 16, 0)
        c_layout.setSpacing(6)

        # Play/Pause
        self.btn_play = QPushButton()
        self.btn_play.setCheckable(True)
        self.btn_play.setFixedSize(32, 32)
        self.btn_play.setIcon(get_icon("play.svg", is_dark))
        self.btn_play.setIconSize(QSize(16, 16))
        self.btn_play.toggled.connect(self._toggle_play)
        self._style_control_btn(self.btn_play)

        # Speed slider
        speed_icon = self._make_icon_label("speed.svg")
        self.slide_speed = self._make_slider(1, 10, self.scroll_speed, self._set_speed, "Speed")

        # Font slider
        font_icon = self._make_icon_label("text_size.svg")
        self.slide_font = self._make_slider(12, 72, self.font_size, self._set_font_size, "Font Size")

        # Opacity slider
        opacity_icon = self._make_icon_label("opacity.svg")
        self.slide_opacity = self._make_slider(20, 100, int(self.opacity_val * 100), self._set_opacity, "Opacity")

        # Separators
        def sep():
            s = QFrame()
            s.setFixedSize(1, 24)
            s.setStyleSheet(f"background: {tc['border']};")
            return s

        c_layout.addWidget(self.btn_play)
        c_layout.addWidget(sep())
        c_layout.addSpacing(4)
        c_layout.addWidget(speed_icon)
        c_layout.addWidget(self.slide_speed)
        c_layout.addWidget(sep())
        c_layout.addSpacing(4)
        c_layout.addWidget(font_icon)
        c_layout.addWidget(self.slide_font)
        c_layout.addWidget(sep())
        c_layout.addSpacing(4)
        c_layout.addWidget(opacity_icon)
        c_layout.addWidget(self.slide_opacity)

        # ── Toast Overlay ──
        self.toast_lbl = QLabel("Click-Through Enabled\nCtrl+Shift+F9 to unlock", self)
        self.toast_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toast_lbl.setStyleSheet(f"""
            background: rgba(0, 0, 0, 200);
            color: {tc['accent']};
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            font-family: 'Inter', 'Segoe UI Variable', sans-serif;
            padding: 12px 20px;
            border: 1px solid {tc['accent']};
        """)
        self.toast_lbl.adjustSize()
        self.toast_lbl.hide()

        # ── Assembly ──
        inner.addWidget(header)
        inner.addWidget(self.text_edit, 1)
        inner.addWidget(self.controls)
        root.addWidget(self.bg_frame)

    # ── Widget Factories ─────────────────────────────────────────────

    def _make_header_btn(self, icon_name, tooltip, is_dark=True, is_close=False):
        btn = QPushButton()
        btn.setFixedSize(28, 28)
        btn.setIcon(get_icon(icon_name, is_dark))
        btn.setIconSize(QSize(16, 16))
        btn.setToolTip(tooltip)
        tc = self.tc
        hover = "#ef4444" if is_close else tc['border']
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {hover};
            }}
            QPushButton:checked {{
                background: {tc['accent']};
            }}
        """)
        return btn

    def _make_icon_label(self, icon_name):
        lbl = QLabel()
        path = os.path.join(self.icon_dir, icon_name)
        if os.path.exists(path):
            lbl.setPixmap(QIcon(path).pixmap(32, 32))
            lbl.setScaledContents(True)
        lbl.setStyleSheet("background: transparent;")
        lbl.setFixedSize(16, 16)
        return lbl

    def _make_slider(self, min_v, max_v, current, callback, tooltip):
        tc = self.tc
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(min_v, max_v)
        s.setValue(current)
        s.setFixedWidth(72)
        s.setToolTip(tooltip)
        s.valueChanged.connect(callback)
        s.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 3px;
                background: {tc['border']};
                border-radius: 1px;
            }}
            QSlider::sub-page:horizontal {{
                background: {tc['accent']};
                border-radius: 1px;
            }}
            QSlider::handle:horizontal {{
                background: {tc['accent']};
                width: 12px;
                height: 12px;
                margin: -5px 0;
                border-radius: 6px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {tc['text']};
            }}
        """)
        return s

    def _style_control_btn(self, btn):
        tc = self.tc
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {tc['border']};
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {tc['accent']};
            }}
            QPushButton:checked {{
                background: {tc['accent']};
            }}
        """)

    def _apply_frame_style(self, locked=False):
        tc = self.tc
        if locked:
            self.bg_frame.setStyleSheet(f"""
                QFrame#HudFrame {{
                    background: rgba(0, 0, 0, 40);
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 5);
                }}
            """)
        else:
            # Parse bg color and create translucent version
            bg = QColor(tc['bg'])
            self.bg_frame.setStyleSheet(f"""
                QFrame#HudFrame {{
                    background: rgba({bg.red()}, {bg.green()}, {bg.blue()}, 230);
                    border-radius: 12px;
                    border: 1px solid {tc['border']};
                }}
            """)

    # ── HTML Loading ─────────────────────────────────────────────────

    def _set_html_safe(self, html):
        """Loads HTML content, extracting inline base64 images as resources."""
        pattern = r'src=["\']data:image/(?P<ext>[^;]+);base64,(?P<data>[^"\']+)["\']'
        index = 0
        doc = self.text_edit.document()

        # Preserve user-resized dimensions while ensuring responsiveness
        html = html.replace("<img ", "<img style='max-width: 100%; height: auto;' ")

        def replace_match(match):
            nonlocal index
            ext = match.group('ext')
            data_b64 = match.group('data')
            try:
                img_data = base64.b64decode(data_b64)
                image = QImage.fromData(img_data)
                if not image.isNull():
                    res_name = f"pro_img_{index}.{ext}"
                    doc.addResource(3, QUrl(res_name), image)
                    index += 1
                    return f'src="{res_name}"'
            except Exception:
                pass
            return match.group(0)

        processed = re.sub(pattern, replace_match, html)
        self.text_edit.setHtml(processed)

    # ── Logic ────────────────────────────────────────────────────────

    def _set_speed(self, val):
        self.scroll_speed = val

    def _set_font_size(self, val):
        self.font_size = val
        tc = self.tc
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {tc['text']};
                font-family: 'Inter', 'Segoe UI Variable', 'Segoe UI', sans-serif;
                font-size: {self.font_size}px;
                padding: 16px 20px;
                line-height: 1.8;
            }}
        """)
        # Force apply to existing rich text
        pos = self.text_edit.verticalScrollBar().value()
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        fmt = QTextCharFormat()
        fmt.setFontPointSize(self.font_size)
        fmt.setForeground(QColor(tc['text']))
        cursor.mergeCharFormat(fmt)
        cursor.clearSelection()
        self.text_edit.setTextCursor(cursor)
        self.text_edit.verticalScrollBar().setValue(pos)

        # Update slider if this was called from zoom logic
        if hasattr(self, 'slide_font') and self.slide_font.value() != val:
            self.slide_font.blockSignals(True)
            self.slide_font.setValue(val)
            self.slide_font.blockSignals(False)
        
        logging.info(f"Teleprompter: Font size set to {val}px")

    def _set_opacity(self, val):
        self.opacity_val = val / 100.0
        self.setWindowOpacity(self.opacity_val)

    def _toggle_play(self, checked):
        tc = self.tc
        is_dark = tc.get("is_dark", True)
        if checked:
            self.btn_play.setIcon(get_icon("pause.svg", is_dark))
            self.state_dot.setStyleSheet(f"color: {tc['accent']}; font-size: 8px; background: transparent;")
            self.is_playing = True
            self.scroll_timer.start()
        else:
            self.btn_play.setIcon(QIcon(os.path.join(self.icon_dir, "play.svg")))
            self.state_dot.setStyleSheet(f"color: {tc['text_muted']}; font-size: 8px; background: transparent;")
            self.is_playing = False
            self.scroll_timer.stop()

    def _scroll_step(self):
        sb = self.text_edit.verticalScrollBar()
        if sb.value() >= sb.maximum():
            self.is_playing = False
            self.scroll_timer.stop()
            self.btn_play.setChecked(False)
            return
        sb.setValue(sb.value() + self.scroll_speed)

    def _toggle_click_through(self, checked):
        self.is_click_through = checked
        from src.core.stealth import StealthManager
        tc = self.tc

        if checked:
            StealthManager.set_click_through(int(self.winId()), True)
            self._apply_frame_style(locked=True)
            self.controls.hide()
            self.title_lbl.setText("LOCKED")
            self.title_lbl.setStyleSheet(f"""
                color: {tc['accent']};
                font-family: 'Inter', 'Segoe UI Variable', 'Segoe UI', sans-serif;
                font-size: 10px; font-weight: 600; letter-spacing: 0.1em;
                background: transparent;
            """)
            self.btn_lock.setIcon(QIcon(os.path.join(self.icon_dir, "unlock.svg")))
            self.drag_handle.hide()
            # Toast
            self.toast_lbl.show()
            self.toast_lbl.raise_()
            QTimer.singleShot(2500, self.toast_lbl.hide)
        else:
            StealthManager.set_click_through(int(self.winId()), False)
            self._apply_frame_style(locked=False)
            self.controls.show()
            self.title_lbl.setText("TELEPROMPTER")
            self.title_lbl.setStyleSheet(f"""
                color: {tc['text_muted']};
                font-family: 'Inter', 'Segoe UI Variable', 'Segoe UI', sans-serif;
                font-size: 10px; font-weight: 600; letter-spacing: 0.1em;
                background: transparent;
            """)
            self.btn_lock.setIcon(QIcon(os.path.join(self.icon_dir, "lock.svg")))
            self.drag_handle.show()
            self.btn_lock.setChecked(False)

    def wheelEvent(self, event):
        """Ctrl+Scroll = zoom font size."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom_in()
            elif delta < 0:
                self._zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Handle Ctrl+Plus, Ctrl+Minus, Ctrl+0 for zoom."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self._zoom_in()
                return
            elif event.key() == Qt.Key.Key_Minus:
                self._zoom_out()
                return
            elif event.key() == Qt.Key.Key_0:
                self._set_font_size(24) # Default
                return
        super().keyPressEvent(event)

    def _zoom_in(self):
        new_size = min(72, self.font_size + 2)
        if new_size != self.font_size:
            self._set_font_size(new_size)

    def _zoom_out(self):
        new_size = max(12, self.font_size - 2)
        if new_size != self.font_size:
            self._set_font_size(new_size)

    # ── Window Drag ──────────────────────────────────────────────────

    def _setup_drag(self):
        self._drag_active = False
        self._drag_pos = None

    def mousePressEvent(self, event):
        if self.is_click_through:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_click_through:
            return
        if self._drag_active and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_active = False

    # ── Auto-hide controls while playing ─────────────────────────────

    def enterEvent(self, event):
        if not self.is_click_through:
            self.controls.show()
            self.btn_close.show()
            self.btn_lock.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.is_playing and not self.is_click_through:
            self.controls.hide()
            self.btn_close.hide()
            self.btn_lock.hide()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        if hasattr(self, 'toast_lbl'):
            self.toast_lbl.move(
                (self.width() - self.toast_lbl.width()) // 2,
                (self.height() - self.toast_lbl.height()) // 2
            )
        super().resizeEvent(event)
