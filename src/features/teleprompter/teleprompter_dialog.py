import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QHBoxLayout, 
    QPushButton, QSlider, QLabel, QWidget, QFrame, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, QEvent, QPoint
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPainter, QAction, QTextCursor, QTextCharFormat, QTextDocument
import os

class TeleprompterDialog(QDialog):
    def __init__(self, text_content="", parent=None):
        super().__init__(parent)
        try:
            logging.info("Initializing TeleprompterDialog...")
            self.setWindowTitle("Stealth Teleprompter")
            self.resize(700, 450)
            
            # Window Flags: Frameless, Always on Top
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint
            )
            
            # Translucency
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            
            # Enable Stealth (Anti-Capture)
            from src.core.stealth import StealthManager
            hwnd = int(self.winId())
            logging.info(f"Teleprompter HWND: {hwnd}")
            
            if not StealthManager.set_stealth_mode(hwnd, True):
                logging.warning("Failed to enable stealth mode for Teleprompter")
                
            # Explicitly DISABLE click-through on start
            StealthManager.set_click_through(hwnd, False)
            
            # Data
            self.scroll_speed = 2
            self.is_playing = False
            self.font_size = 24
            self.opacity_val = 0.8
            self.is_click_through = False
            
            # Paths
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.icon_dir = os.path.join(base_path, "assets", "icons", "dark_theme")
            logging.info(f"Icon Dir: {self.icon_dir}")

            # Timer for scrolling
            self.scroll_timer = QTimer(self)
            self.scroll_timer.timeout.connect(self.scroll_text)
            self.scroll_timer.setInterval(50) 
            
            self.init_ui(text_content)
            self.setup_drag_behavior()
            
            # Initial Opacity
            self.setWindowOpacity(self.opacity_val)
            logging.info("TeleprompterDialog initialized successfully.")
            
        except Exception as e:
            logging.critical(f"Failed to initialize TeleprompterDialog: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to open Teleprompter: {e}")

    def init_ui(self, content):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # --- Main Background Frame ---
        self.bg_frame = QFrame(self)
        self.bg_frame.setObjectName("HudFrame")
        self.bg_frame.setStyleSheet("""
            QFrame#HudFrame {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setContentsMargins(15, 15, 15, 15)
        
        # --- Header (Draggable Area + Close) ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Drag Handle
        self.drag_handle = QLabel()
        drag_icon_path = os.path.join(self.icon_dir, "drag_handle.svg")
        if os.path.exists(drag_icon_path):
            self.drag_handle.setPixmap(QIcon(drag_icon_path).pixmap(20, 20))
        else:
            self.drag_handle.setText("::") # Fallback
            
        self.drag_handle.setStyleSheet("background: transparent; color: white;")
        self.drag_handle.setToolTip("Drag here to move")
        
        self.title_lbl = QLabel("Teleprompter")
        self.title_lbl.setStyleSheet("color: rgba(255, 255, 255, 180); font-weight: 600; font-size: 14px; font-family: 'Segoe UI';")
        
        self.btn_click_through = QPushButton()
        self.btn_click_through.setCheckable(True)
        self.btn_click_through.setFixedSize(28, 28)
        self.btn_click_through.setIcon(QIcon(os.path.join(self.icon_dir, "lock.svg")))
        self.btn_click_through.setIconSize(QSize(16, 16))
        self.btn_click_through.setToolTip("Enable Click-Through Mode (Lock Position)\nUnlock with Ctrl+Shift+F9")
        self.btn_click_through.toggled.connect(self.toggle_click_through)
        self.style_hud_button(self.btn_click_through)

        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setIcon(QIcon(os.path.join(self.icon_dir, "close.svg")))
        self.btn_close.setIconSize(QSize(16, 16))
        self.btn_close.clicked.connect(self.close)
        self.style_hud_button(self.btn_close, is_close=True)
        
        header_layout.addWidget(self.drag_handle)
        header_layout.addSpacing(5)
        header_layout.addWidget(self.title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_click_through)
        header_layout.addSpacing(5)
        header_layout.addWidget(self.btn_close)
        
        # --- Toast Message Overlay ---
        self.toast_lbl = QLabel("Click-Through Enabled\nPress Ctrl+Shift+F9 to Unlock", self)
        self.toast_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.toast_lbl.setStyleSheet("""
            background-color: rgba(0, 0, 0, 200);
            color: #10b981;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            padding: 10px;
            border: 1px solid #10b981;
        """)
        self.toast_lbl.adjustSize()
        self.toast_lbl.hide()

        # --- Text Area ---
        self.text_edit = QTextEdit()
        self.set_html_safe(content)
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: {self.font_size}px;
                line-height: 1.6;
            }}
        """)
        
        # --- Controls Container (Auto-hide) ---
        self.controls_widget = QWidget()
        self.controls_widget.setFixedHeight(50)
        self.controls_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 200);
                border-radius: 25px;
            }
        """)
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(15, 5, 15, 5)
        
        # Play/Pause
        self.btn_play = QPushButton()
        self.btn_play.setCheckable(True)
        self.btn_play.setFixedSize(36, 36)
        self.btn_play.setIcon(QIcon(os.path.join(self.icon_dir, "play.svg")))
        self.btn_play.setIconSize(QSize(20, 20))
        self.btn_play.toggled.connect(self.toggle_play)
        self.style_hud_button(self.btn_play)
        
        # Speed
        icon_speed = QIcon(os.path.join(self.icon_dir, "speed.svg"))
        self.slide_speed = self.create_slider(1, 10, self.scroll_speed, self.set_speed, icon_speed, "Speed")

        # Font
        icon_text = QIcon(os.path.join(self.icon_dir, "text_size.svg"))
        self.slide_font = self.create_slider(12, 72, self.font_size, self.set_font_size, icon_text, "Font Size")

        # Opacity
        icon_opacity = QIcon(os.path.join(self.icon_dir, "opacity.svg"))
        self.slide_opacity = self.create_slider(20, 100, int(self.opacity_val * 100), self.set_opacity, icon_opacity, "Opacity")

        controls_layout.addWidget(self.btn_play)
        controls_layout.addSpacing(15)
        controls_layout.addWidget(QLabel("", pixmap=icon_speed.pixmap(16, 16)))
        controls_layout.addWidget(self.slide_speed)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(QLabel("", pixmap=icon_text.pixmap(16, 16)))
        controls_layout.addWidget(self.slide_font)
        controls_layout.addSpacing(10)
        controls_layout.addWidget(QLabel("", pixmap=icon_opacity.pixmap(16, 16)))
        controls_layout.addWidget(self.slide_opacity)
        
        # Assemble
        bg_layout.addLayout(header_layout)
        bg_layout.addWidget(self.text_edit)
        bg_layout.addWidget(self.controls_widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        layout.addWidget(self.bg_frame)

    def set_html_safe(self, html):
        """Robustly sets HTML by extracting base64 images (Unified Logic)."""
        import re
        import base64
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import QUrl
        
        pattern = r'src=["\']data:image/(?P<ext>[^;]+);base64,(?P<data>[^"\']+)["\']'
        index = 0
        doc = self.text_edit.document()
        
        # Strip conflicting attributes that might have leaked or were hardcoded
        html = re.sub(r'(<img[^>]+)style=["\'][^"\']*["\']', r'\1', html)
        html = re.sub(r'(<img[^>]+)width=["\'][^"\']*["\']', r'\1', html)
        html = re.sub(r'(<img[^>]+)height=["\'][^"\']*["\']', r'\1', html)
        
        # Responsive Image CSS (Ensure it's added LAST)
        html = html.replace("<img ", "<img style='max-width: 100%;' ")

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
            except: pass
            return match.group(0)

        processed_html = re.sub(pattern, replace_match, html)
        self.text_edit.setHtml(processed_html)

    def resizeEvent(self, event):
        # Center toast
        if hasattr(self, 'toast_lbl'):
             self.toast_lbl.move(
                (self.width() - self.toast_lbl.width()) // 2,
                (self.height() - self.toast_lbl.height()) // 2
            )
        super().resizeEvent(event)

    def toggle_click_through(self, checked):
        self.is_click_through = checked
        from src.core.stealth import StealthManager
        
        if checked:
            StealthManager.set_click_through(int(self.winId()), True)
            self.bg_frame.setStyleSheet("""
                QFrame#HudFrame {
                    background-color: rgba(0, 0, 0, 40);
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 5);
                }
            """)
            self.controls_widget.hide()
            self.title_lbl.setText("🔒 Locked")
            self.btn_click_through.setIcon(QIcon(os.path.join(self.icon_dir, "unlock.svg")))
            self.drag_handle.hide()
            
            # Show Toast
            self.toast_lbl.show()
            self.toast_lbl.raise_()
            QTimer.singleShot(3000, self.toast_lbl.hide)
            
        else:
            StealthManager.set_click_through(int(self.winId()), False)
            self.bg_frame.setStyleSheet("""
                QFrame#HudFrame {
                    background-color: rgba(0, 0, 0, 180);
                    border-radius: 8px;
                    border: 1px solid rgba(255, 255, 255, 20);
                }
            """)
            self.controls_widget.show()
            self.title_lbl.setText("Teleprompter")
            self.btn_click_through.setIcon(QIcon(os.path.join(self.icon_dir, "lock.svg")))
            self.drag_handle.show()
            self.btn_click_through.setChecked(False) # Ensure UI state sync

    def create_slider(self, min_val, max_val, current_val, callback, icon, tooltip):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(current_val)
        slider.setFixedWidth(80)
        slider.setToolTip(tooltip)
        slider.valueChanged.connect(callback)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #5ca0fa;
                height: 4px;
                background: rgba(255, 255, 255, 50);
                margin: 0px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #5ca0fa;
                border: 1px solid #5ca0fa;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
        """)
        return slider

    def style_hud_button(self, btn, is_close=False):
        hover_color = "#ff5555" if is_close else "rgba(255, 255, 255, 40)"
        bg_color = "transparent" if is_close else "rgba(255, 255, 255, 10)"
        border = "none" if is_close else "1px solid rgba(255, 255, 255, 20)"
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: {border};
                border-radius: 14px; /* Circle/Round */
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:checked {{
                background-color: #10b981;
                border: 1px solid #10b981;
            }}
        """)

    # --- Logic ---

    # --- Logic ---

    def set_speed(self, val):
        self.scroll_speed = val

    def set_font_size(self, val):
        self.font_size = val
        
        # 1. Update stylesheet (keeps base style correct)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: white;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: {self.font_size}px;
                line-height: 1.6;
            }}
        """)
        
        # 2. Force apply to existing Rich Text content
        # We must preserve scroll position
        scrollbar = self.text_edit.verticalScrollBar()
        scroll_pos = scrollbar.value()
        
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        
        fmt = QTextCharFormat()
        fmt.setFontPointSize(self.font_size)
        fmt.setForeground(QColor("white")) # Ensure text remains white
        
        cursor.mergeCharFormat(fmt)
        
        # Restore cursor and scroll
        cursor.clearSelection()
        self.text_edit.setTextCursor(cursor)
        scrollbar.setValue(scroll_pos)

    def set_opacity(self, val):
        self.opacity_val = val / 100.0
        self.setWindowOpacity(self.opacity_val)

    def toggle_play(self, checked):
        if checked:
            self.btn_play.setIcon(QIcon(os.path.join(self.icon_dir, "pause.svg")))
            self.start_scrolling()
        else:
            self.btn_play.setIcon(QIcon(os.path.join(self.icon_dir, "play.svg")))
            self.stop_scrolling()

    def toggle_click_through(self, checked):
        self.is_click_through = checked
        
        # If enabled, we need to be transparent to mouse
        # BUT we still need to capture mouse for the header controls if possible?
        # Actually, standard WS_EX_TRANSPARENT makes the WHOLE window ignored.
        # So we can't click "Close" or "Toggle Back" easily if we do full window click-through.
        # Typically we use a global hotkey to toggle back.
        
        from src.core.stealth import StealthManager
        if checked:
            StealthManager.set_click_through(int(self.winId()), True)
            self.bg_frame.setStyleSheet("""
                QFrame#HudFrame {
                    background-color: rgba(0, 0, 0, 50); /* Dimmer when locked */
                    border-radius: 15px;
                    border: 1px solid rgba(255, 255, 255, 10);
                }
            """)
            self.controls_widget.hide() # Hide controls when locked
            self.title_lbl.setText("🔒 Locked (Ctrl+Shift+F9 to unlock)")
        else:
            StealthManager.set_click_through(int(self.winId()), False)
            self.bg_frame.setStyleSheet("""
                QFrame#HudFrame {
                    background-color: rgba(0, 0, 0, 180);
                    border-radius: 15px;
                    border: 1px solid rgba(255, 255, 255, 30);
                }
            """)
            self.controls_widget.show()
            self.title_lbl.setText("📜 Teleprompter")

    def start_scrolling(self):
        self.is_playing = True
        self.scroll_timer.start()

    def stop_scrolling(self):
        self.is_playing = False
        self.scroll_timer.stop()

    def scroll_text(self):
        scrollbar = self.text_edit.verticalScrollBar()
        current_val = scrollbar.value()
        max_val = scrollbar.maximum()
        if current_val >= max_val:
            self.stop_scrolling()
            self.btn_play.setChecked(False)
            self.btn_play.setIcon(QIcon(os.path.join(self.icon_dir, "play.svg")))
            return
        scrollbar.setValue(current_val + self.scroll_speed)

    # --- Auto-Hide Controls ---
    def enterEvent(self, event):
        if not self.is_click_through:
            self.controls_widget.show()
            self.btn_close.show()
            self.btn_click_through.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.is_playing and not self.is_click_through:
             # Look minimal when playing and mouse leaves
             self.controls_widget.hide()
             self.btn_close.hide()
             self.btn_click_through.hide()
        super().leaveEvent(event)

    # --- Window Dragging Logic ---
    def setup_drag_behavior(self):
        self._drag_active = False
        self._drag_pos = None

    def mousePressEvent(self, event):
        if self.is_click_through: return 
        if event.button() == Qt.MouseButton.LeftButton:
            # Only drag if not clicking a control
            self._drag_active = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_click_through: return
        if self._drag_active and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_active = False
