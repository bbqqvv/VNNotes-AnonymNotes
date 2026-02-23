import logging

from PyQt6.QtWidgets import QLabel

logger = logging.getLogger(__name__)


class StatusBarManager:
    """
    Manages the status bar widgets: cursor position, character count,
    zoom level, EOL format, and encoding display.
    """

    def __init__(self, main_window):
        self.mw = main_window
        self.status_pos_label = None
        self.status_char_label = None
        self.status_zoom_label = None
        self.status_eol_label = None
        self.status_enc_label = None

    def setup_widgets(self):
        """Initializes the labels in the status bar."""
        self.status_pos_label = QLabel("Ln 1, Col 1")
        self.status_char_label = QLabel("0 characters")
        self.status_zoom_label = QLabel("100%")
        self.status_eol_label = QLabel("Windows (CRLF)")
        self.status_enc_label = QLabel("UTF-8")

        sb = self.mw.statusBar()
        sb.addPermanentWidget(self.status_pos_label)
        sb.addPermanentWidget(QLabel("  |  "))
        sb.addPermanentWidget(self.status_char_label)
        sb.addPermanentWidget(QLabel("  |  "))
        sb.addPermanentWidget(self.status_zoom_label)
        sb.addPermanentWidget(QLabel("  |  "))
        sb.addPermanentWidget(self.status_eol_label)
        sb.addPermanentWidget(QLabel("  |  "))
        sb.addPermanentWidget(self.status_enc_label)
        sb.addPermanentWidget(QLabel("   "))

    def update_info(self):
        """Updates the status bar labels based on the active pane's content and cursor."""
        if not self.mw.active_pane:
            self.status_pos_label.setText("")
            self.status_char_label.setText("")
            return

        try:
            cursor = self.mw.active_pane.textCursor()
            line = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.status_pos_label.setText(f"Ln {line}, Col {col}")

            # Performance optimization: extraction of character count without full string copy
            doc = self.mw.active_pane.document()
            count = doc.characterCount() - 1 # QTextDocument appends a trailing block char
            self.status_char_label.setText(f"{max(0, count)} characters")

        except RuntimeError:
            self.mw.active_pane = None
            self.status_pos_label.setText("")
            self.status_char_label.setText("")

    def show_message(self, message, timeout=3000):
        """Shows a temporary message in the status bar."""
        self.mw.statusBar().showMessage(message, timeout)
