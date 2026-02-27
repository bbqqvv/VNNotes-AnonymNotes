import logging
from PyQt6.QtWidgets import QLabel, QPushButton
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class StatusBarManager:
    """
    Manages the status bar widgets: cursor position, character count,
    encoding display, and Markdown mode toggle.
    """

    def __init__(self, main_window):
        self.mw = main_window
        self.status_pos_label = None
        self.status_char_label = None
        self.status_enc_label = None
        self.mode_toggle_btn = None

    def setup_widgets(self):
        """Initializes the labels in the status bar."""
        self.status_pos_label = QLabel("Ln 1, Col 1")
        self.status_char_label = QLabel("0 characters")
        self.status_enc_label = QLabel("UTF-8")
        
        # Markdown Mode Toggle (Moved to far right)
        self.mode_toggle_btn = QPushButton("Markdown")
        self.mode_toggle_btn.setFlat(True)
        self.mode_toggle_btn.setFixedWidth(80)
        self.mode_toggle_btn.setToolTip("Toggle between Markdown syntax and Rich Text (Ctrl+Alt+M)")
        self.mode_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_toggle_btn.setStyleSheet("""
            QPushButton { 
                color: #569CD6; 
                font-weight: bold; 
                font-size: 11px;
                border: 1px solid transparent;
                padding: 0px 4px;
            }
            QPushButton:hover { 
                background: rgba(255, 255, 255, 0.1); 
                border: 1px solid #569CD6;
                color: #4EC9B0;
            }
        """)
        self.mode_toggle_btn.clicked.connect(self.mw.convert_markdown)

        sb = self.mw.statusBar()
        
        # Left side
        sb.addPermanentWidget(self.status_pos_label)
        sb.addPermanentWidget(QLabel("  |  "))
        sb.addPermanentWidget(self.status_char_label)
        
        # Spacer
        dummy = QLabel("")
        sb.addWidget(dummy, 1) # This pushes widgets to the edges
        
        # Right side (Permanent)
        sb.addPermanentWidget(self.status_enc_label)
        sb.addPermanentWidget(QLabel("  |  "))
        sb.addPermanentWidget(self.mode_toggle_btn)
        sb.addPermanentWidget(QLabel("   "))

    def update_info(self):
        """Updates the status bar labels based on the active pane's content and cursor."""
        if not self.mw.active_pane:
            self.status_pos_label.setText("")
            self.status_char_label.setText("")
            if self.mode_toggle_btn:
                self.mode_toggle_btn.hide()
            return

        if self.mode_toggle_btn:
            self.mode_toggle_btn.show()
            self.update_mode_label(getattr(self.mw.active_pane, '_is_md_mode', True))

        try:
            cursor = self.mw.active_pane.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.status_pos_label.setText(f"Ln {line}, Col {col}")

            # Character count
            doc = self.mw.active_pane.document()
            count = doc.characterCount() - 1 
            self.status_char_label.setText(f"{max(0, count)} characters")

        except RuntimeError:
            self.mw.active_pane = None
            self.status_pos_label.setText("")
            self.status_char_label.setText("")

    def update_mode_label(self, is_md):
        """Updates the text of the MD/Rich toggle button."""
        if self.mode_toggle_btn:
            text = "Markdown" if is_md else "Rich Text"
            self.mode_toggle_btn.setText(text)
            self.mode_toggle_btn.setToolTip(f"Current mode: {text}. Click to toggle.")

    def show_message(self, message, timeout=3000):
        """Shows a temporary message in the status bar."""
        self.mw.statusBar().showMessage(message, timeout)
