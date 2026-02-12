from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QScreen, QPixmap
from PyQt6.QtCore import Qt, QRect, pyqtSignal

class SnippingWidget(QWidget):
    snippet_captured = pyqtSignal(QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        self.start_pos = None
        self.end_pos = None
        self.is_sniping = False
        
        # Reset opacity to handle drawing ourselves
        self.setWindowOpacity(1.0) 

    def start_snip(self):
        self.show()
        self.activateWindow()
        self.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dim entire screen
        path = QRect(0, 0, self.width(), self.height())
        # Semi-transparent black overlay
        painter.fillRect(path, QColor(0, 0, 0, 100))
        
        if self.start_pos and self.end_pos:
            # Draw selection rectangle
            rect = QRect(self.start_pos, self.end_pos).normalized()
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        self.start_pos = event.pos()
        self.end_pos = event.pos()
        self.is_sniping = True
        self.update()

    def mouseMoveEvent(self, event):
        if self.is_sniping:
            self.end_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        self.is_sniping = False
        self.hide()
        
        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            if rect.width() > 10 and rect.height() > 10:
                self.take_screenshot(rect)
        
        self.start_pos = None
        self.end_pos = None

    def take_screenshot(self, rect):
        screen = QApplication.primaryScreen()
        if screen:
             # Grab from desktop (windowId 0)
             pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
             self.snippet_captured.emit(pixmap)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
