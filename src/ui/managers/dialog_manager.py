import os
import logging

from PyQt6.QtWidgets import QMessageBox, QFileDialog, QDockWidget

from src.core.reader import UniversalReader
from src.core.version import check_for_updates, CURRENT_VERSION

logger = logging.getLogger(__name__)


class DialogManager:
    """
    Manages application dialogs: Open File, Shortcuts, About,
    Teleprompter, Update Check, and Note Rename.
    """

    def __init__(self, main_window):
        self.mw = main_window

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self.mw, "Open File", "",
            "Word & Text Files (*.docx *.txt *.md *.py *.js *.html);;All Files (*)")
        if path:
            content = UniversalReader.read_file(path)
            if content:
                self.mw.add_note_dock(content=content, title=os.path.basename(path), file_path=path)

    def save_file(self):
        """Standard 'Save' (Ctrl+S) - uses existing path if available."""
        if not self.mw.active_pane:
            return
        
        pane = self.mw.active_pane
        if hasattr(pane, 'file_path') and pane.file_path:
            self._write_to_file(pane, pane.file_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        """'Save As' - always prompts for path."""
        if not self.mw.active_pane:
            return
            
        pane = self.mw.active_pane
        path, _ = QFileDialog.getSaveFileName(
            self.mw, "Save Note As", "", 
            "Text File (*.txt);;Markdown File (*.md);;HTML File (*.html);;All Files (*)")
            
        if path:
            self._write_to_file(pane, path)
            pane.file_path = path
            # Update dock title to match new filename
            for dock in self.mw.findChildren(QDockWidget):
                if dock.widget() == pane:
                    dock.setWindowTitle(os.path.basename(path))
                    break
            if hasattr(self.mw, 'sidebar'):
                self.mw.sidebar.refresh_tree()

    def _write_to_file(self, pane, path):
        """Internal helper to write NotePane content to disk."""
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".html":
                content = pane.toHtml()
            elif ext == ".md" or ext == ".txt":
                # Use plain text for these formats
                content = pane.toPlainText()
            else:
                # Default to plain text
                content = pane.toPlainText()
                
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Show feedback in status bar if possible
            if hasattr(self.mw, 'status_bar_manager'):
                self.mw.status_bar_manager.show_message(f"Saved to {os.path.basename(path)}", 3000)
        except Exception as e:
            QMessageBox.critical(self.mw, "Save Error", f"Could not save file:\n{e}")

    def show_shortcuts_dialog(self):
        QMessageBox.information(
            self.mw, "Shortcuts",
            "Ctrl+N: Note\nCtrl+Shift+B: Browser\nCtrl+Shift+P: Prompter\n"
            "Ctrl+Shift+S: Stealth\nCtrl+Shift+F9: Ghost Click")

    def show_about_dialog(self):
        """Shows professional About dialog."""
        import platform
        about_text = f"""
        <h2 style='color: #3498db;'>VNNotes</h2>
        <p><b>Version:</b> {CURRENT_VERSION}</p>
        <p><b>Author:</b> Bùi Quốc Văn</p>
                <p><b>Email: <a href="mailto:vanbq.dev@gmail.com">vanbq.dev@gmail.com</a></p>

        <p><b>A modern, stealthy, and highly optimized note-taking application.</b></p>
        <hr>
        <p><b>Core Features:</b></p>
        <ul>
            <li>Elite Startup Restoration (Multi-tab batch loading)</li>
            <li>Extended Stealth & Anti-Capture Protection</li>
            <li>Integrated Mini Browser & Teleprompter</li>
            <li>Clipboard History Management</li>
        </ul>
        <hr>
        <p><b>System Info:</b> {platform.system()} {platform.release()}</p>
        <p style='font-size: 10px; color: #888;'>© 2026 Bùi Quốc Văn. Bản quyền thuộc về VTech Digital Solution.</p>
        """
        QMessageBox.about(self.mw, "About VNNotes", about_text)

    def open_teleprompter(self):
        """Opens Teleprompter with fully embedded base64 content."""
        from src.features.teleprompter.teleprompter_dialog import TeleprompterDialog
        if not self.mw.active_pane:
            return
        content = self.mw.active_pane.get_content_with_embedded_images()
        
        # Pass theme config so Teleprompter matches the app's look
        theme_config = None
        if hasattr(self.mw, 'theme_manager'):
            from src.ui.managers.theme_manager import ThemeManager
            theme_config = ThemeManager.THEME_CONFIG.get(self.mw.theme_manager.current_theme)
        
        self.mw.teleprompter = TeleprompterDialog(content, theme_config=theme_config)
        self.mw.teleprompter.show()

    def check_for_updates(self, manual=True):
        """Checks for updates and reports results."""
        has_update, latest_version, url, error = check_for_updates()
        if has_update:
            msg = (f"<b>VNNotes v{latest_version} is available!</b><br><br>"
                   f"Download now at:<br><a href='{url}'>{url}</a>")
            QMessageBox.information(self.mw, "Update Available", msg)
        elif error:
            if manual:
                QMessageBox.warning(
                    self.mw, "Update Check Failed",
                    f"Error checking for updates:<br>{error}")
        elif manual:
            QMessageBox.information(
                self.mw, "Update",
                "You are using the latest version of VNNotes.")

    def rename_active_note(self):
        """Standard rename method (useful for shortcut)."""
        if not self.mw.active_pane:
            return
        for dock in self.mw.findChildren(QDockWidget):
            if dock.widget() == self.mw.active_pane:
                self.show_rename_dialog(dock)
                break

    def show_rename_dialog(self, dock):
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self.mw, "Rename Note", "New name:", text=dock.windowTitle())
        if ok and new_name.strip():
            new_title = new_name.strip()
            dock.setWindowTitle(new_title)

            # Sync to note service so sidebar reflects the change
            obj_name = dock.objectName()
            if hasattr(self.mw, 'note_service') and obj_name:
                self.mw.note_service.rename_note(obj_name, new_title)
            if hasattr(self.mw, 'sidebar'):
                self.mw.sidebar.refresh_tree()

            self.mw.save_app_state()

    def show_limit_reached_dialog(self, limit=10):
        """Plan v6: Shows a warning when the maximum number of splits is reached."""
        QMessageBox.warning(
            self.mw, "Limit Reached",
            f"Standard capacity reached: <b>{limit} Note areas</b>.<br><br>"
            "To maintain professional legibility and performance, additional splitting "
            "is restricted. Use existing notes or close unused areas to continue."
        )
