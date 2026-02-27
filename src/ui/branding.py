from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy, QGraphicsOpacityEffect, QGridLayout
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, pyqtProperty, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QFontMetrics
import os
import sys

class BrandingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        # Load Logo Assets
        self.logo_pixmap = self._load_logo()

        # â”€â”€â”€ Simple Stacked Centering (Absolute Stability) â”€â”€â”€
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.main_layout.addStretch(1)
        
        # Internal container for the Logo + Text block
        self.content_container = QWidget()
        container_layout = QVBoxLayout(self.content_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(40)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.logo_label)
        
        self.text_label = QLabel("VNNOTES")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Stylized Typography (Refined): Light, Spaced
        font = QFont("Segoe UI Light", 34)
        if sys.platform != "win32":
            font.setFamily("Inter")
        self.text_label.setFont(font)
        
        # Visual Depth: Subtle Shadow
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.text_label.setGraphicsEffect(shadow)
        
        container_layout.addWidget(self.text_label)
        
        self.main_layout.addWidget(self.content_container, 0, Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch(1)

    def _load_logo(self):
        """Helper to find the correct logo path."""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        p1 = os.path.join(base_path, "logo.png")
        p2 = os.path.join(base_path, "appnote.png")
        path = p1 if os.path.exists(p1) else p2
        
        if os.path.exists(path):
            return QPixmap(path)
        return None

    @property
    def is_suppressed(self):
        return getattr(self, "_is_suppressed", False)
    
    @is_suppressed.setter
    def is_suppressed(self, value):
        self._is_suppressed = value
        if value:
            self.content_container.hide()
        else:
            self.content_container.show()
        self.update() # Plan v8.18: Post-visibility signal
        self.repaint() # Plan v9.2: Synchronous visual commit before GUI freeze

    def showEvent(self, event):
        """Final safety check when showing."""
        super().showEvent(event)
        if not self.is_suppressed:
            # Fire once more after a delay to catch the final window state
            QTimer.singleShot(200, self._update_elements)

    def resizeEvent(self, event):
        """Minimal update on resize."""
        super().resizeEvent(event)
        if not self.is_suppressed:
            self._update_elements()

    def _update_elements(self):
        """Syncs logo scaling and colors with the current theme."""
        if getattr(self, "_updating", False) or self.is_suppressed: return
        self._updating = True
        
        try:
            h = self.height()
            if h < 20 or not self.content_container.isVisible(): 
                return 
            
            # 1. Scale Logo (Plan v8.17: Larger, more prominent)
            if hasattr(self, 'logo_pixmap') and self.logo_pixmap and not self.logo_pixmap.isNull():
                target_h = min(180, h // 3)
                scaled = self.logo_pixmap.scaledToHeight(target_h, Qt.TransformationMode.SmoothTransformation)
                self.logo_label.setPixmap(scaled)
                
            # 2. Theme Opacity/Colors
            is_dark = self._is_dark_mode()
            text_alpha = 100 if is_dark else 150
            
            window = self.window()
            text_color = QColor("#ffffff") if is_dark else QColor("#000000")
            
            if hasattr(window, "theme_manager"):
                tm = window.theme_manager
                c = tm.THEME_CONFIG.get(tm.current_theme, {})
                text_color = QColor(c.get("text", text_color.name()))
            
            rgba_str = f"rgba({text_color.red()}, {text_color.green()}, {text_color.blue()}, {text_alpha})"
            self.text_label.setStyleSheet(f"color: {rgba_str}; background: transparent; border: none; letter-spacing: 8px;")
            
            self.logo_label.adjustSize()
            self.text_label.adjustSize()
            self.content_container.adjustSize()
            self.content_container.updateGeometry()
            
            # 3. Force the layout refresh (Plan v8.18: Removed for Python 3.14 stability)
            pass
                
            self.update()
        except Exception:
            pass
        finally:
            self._updating = False

    def paintEvent(self, event):
        """Handle background fill (Plan v9.2: Continuity even when suppressed)."""
        
        painter = QPainter(self)
        bg_color = QColor("#0b0b0e") 
        
        window = self.window()
        if hasattr(window, "theme_manager") and window.theme_manager:
            tm = window.theme_manager
            try:
                c = tm.THEME_CONFIG.get(tm.current_theme, {})
                bg_color = QColor(c.get("bg", "#0b0b0e"))
            except Exception:
                pass
                
        painter.fillRect(self.rect(), bg_color)

    def _is_dark_mode(self):
        window = self.window()
        if hasattr(window, "theme_manager"):
            try:
                return window.theme_manager.is_dark_mode
            except Exception:
                return True
        return True
