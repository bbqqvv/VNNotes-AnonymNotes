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
        sb.addPermanentWidget(QLabel("   "))

    def update_info(self):
        """Updates the status bar labels based on the active pane's content and cursor."""
        if not self.mw.active_pane or not self.status_pos_label:
            return

        try:
            cursor = self.mw.active_pane.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.status_pos_label.setText(f"Ln {line}, Col {col}")

            # Character count
            doc = self.mw.active_pane.document()
            count = doc.characterCount() - 1 
            self.status_char_label.setText(f"{max(0, count)} characters")

        except (RuntimeError, AttributeError):
            # Guard against C++ objects being deleted or partially initialized labels
            pass

    def show_message(self, message, timeout=3000):
        """Shows a temporary message in the status bar."""
        self.mw.statusBar().showMessage(message, timeout)
