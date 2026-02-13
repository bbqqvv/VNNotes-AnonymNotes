from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
import os
import sys

class BrandingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)  # Let clicks pass through if needed
        
        # Load Logo
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
        # User confirmed logo.png is transparent and ready
        self.logo_path = os.path.join(base_path, "logo.png")
        # Fallback only
        if not os.path.exists(self.logo_path):
             self.logo_path = os.path.join(base_path, "appnote.png")
             
        self.logo_pixmap = None
        if os.path.exists(self.logo_path):
            self.logo_pixmap = QPixmap(self.logo_path)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dimensions
        w = self.width()
        h = self.height()
        
        # 1. Draw Subtle Background Logo
        if self.logo_pixmap:
            # Scale logo to 20% of window height
            target_h = int(h * 0.3)
            scaled = self.logo_pixmap.scaledToHeight(target_h, Qt.TransformationMode.SmoothTransformation)
            
            # center position
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            
            # Set Opacity for "Watermark" feel
            painter.setOpacity(0.15) # Increased from 0.05
            painter.drawPixmap(x, y, scaled)
            
        # 2. Draw Text "Stealth Assist"
        painter.setOpacity(0.3) # Increased from 0.1
        font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff") if self._is_dark_mode() else QColor("#000000"))
        
        text = "STEALTH ASSIST"
        metrics = painter.fontMetrics()
        text_w = metrics.horizontalAdvance(text)
        
        # Position below logo
        text_y = y + scaled.height() + 40 if self.logo_pixmap else h // 2
        painter.drawText((w - text_w) // 2, text_y, text)

    def _is_dark_mode(self):
        # Infer from parent or default to dark
        window = self.window()
        if hasattr(window, "current_theme"):
            return window.current_theme == "dark"
        return True
