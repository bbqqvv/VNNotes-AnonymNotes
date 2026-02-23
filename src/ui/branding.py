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

        # ─── Simple Stacked Centering (Absolute Stability) ───
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
        container_layout.addWidget(self.text_label)
        
        self.main_layout.addWidget(self.content_container, 0, Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch(1)

        # Pre-allocate effects
        self._logo_opacity_effect = QGraphicsOpacityEffect(self.logo_label)
        self.logo_label.setGraphicsEffect(self._logo_opacity_effect)
        
        self._text_opacity_effect = QGraphicsOpacityEffect(self.text_label)
        self.text_label.setGraphicsEffect(self._text_opacity_effect)

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

    def showEvent(self, event):
        """Final safety check when showing."""
        super().showEvent(event)
        # Fire once more after a delay to catch the final window state
        QTimer.singleShot(500, self._update_elements)

    def resizeEvent(self, event):
        """Update logo scaling when widget size changes."""
        super().resizeEvent(event)
        self._update_elements()

    def _update_elements(self):
        """Syncs element sizes and colors with the current theme and geometry."""
        if getattr(self, "_updating", False): return
        self._updating = True
        
        try:
            h = self.height()
            window = self.window()
            
            if h < 20: return 

            # 1. Scale Logo
            if self.logo_pixmap:
                max_logo_h = min(int(h * 0.3), 300)
                scaled = self.logo_pixmap.scaledToHeight(max_logo_h, Qt.TransformationMode.SmoothTransformation)
                self.logo_label.setPixmap(scaled)
            
            # 2. Update Font
            font_size = 32
            if h < 400: font_size = 24
            font = QFont("Inter", font_size, QFont.Weight.Medium)
            if sys.platform == "win32":
                 font = QFont("Segoe UI Variable Display", font_size, QFont.Weight.Medium)
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
            self.text_label.setFont(font)

            # 3. Apply Theme Opacity/Colors
            is_dark = self._is_dark_mode()
            text_color = "#ffffff" if is_dark else "#000000"
            
            window = self.window()
            if hasattr(window, "theme_manager"):
                tm = window.theme_manager
                c = tm.THEME_CONFIG.get(tm.current_theme, {})
                text_color = c.get("text", text_color)
                
            l_op = 0.25 if is_dark else 0.45
            t_op = 0.55 if is_dark else 0.65
            
            self.text_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
            self.logo_label.setStyleSheet("background: transparent; border: none;")
            
            self._logo_opacity_effect.setOpacity(l_op)
            self._text_opacity_effect.setOpacity(t_op)
        finally:
            self._updating = False

    def paintEvent(self, event):
        """Handle background fill - Always default to dark for professional splash experience."""
        painter = QPainter(self)
        
        # Default fallback is deep zinc (#0b0b0e) to prevent "White Screen" if theme manager delay occurs
        bg_color = QColor("#0b0b0e") 
        
        window = self.window()
        if hasattr(window, "theme_manager") and window.theme_manager:
            tm = window.theme_manager
            # Safe retrieval to prevent crash during init
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
