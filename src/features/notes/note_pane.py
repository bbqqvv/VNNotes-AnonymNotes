import logging
import re
import os
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt, QUrl, QRect, QSize, QTimer, QEvent
from PyQt6.QtGui import (QFont, QTextListFormat, QTextCursor, QTextBlockFormat, 
                         QPainter, QColor, QFontMetrics, QTextCharFormat, QImage, QDesktopServices, QTextDocument,
                         QTextTableFormat, QTextFrameFormat, QTextLength, QPalette, QAction)
from PyQt6.QtWidgets import QTextEdit, QWidget, QApplication, QFileDialog, QInputDialog

# Component Imports
from src.features.notes.image_manager import NoteImageManager
from src.features.notes.paging_engine import NotePagingEngine

class NotePane(QTextEdit):
    """The core rich-text editor component (formerly NoteEditor, reverted to NotePane)."""
    focus_received = pyqtSignal(object)   # Notify main window of focus
    content_changed = pyqtSignal()
    cursor_format_changed = pyqtSignal(object)  # Emits QTextCharFormat on cursor move

    def __init__(self, parent=None, zoom=100):
        super().__init__(parent)
        self.setPlaceholderText("Type notes here... (Paste images supported)")
        self.setMinimumHeight(100) # Prevent massive layout expansion during dock creation
        self.setMouseTracking(True) 
        self.viewport().setMouseTracking(True)
        self.setAcceptDrops(True)
        self.file_path = None # Tracking the physical file on disk
        self._current_url_highlight: "tuple[int, int] | None" = None 
        self._is_dirty = False # Track if user has modified the content
        
        # Managers (Plan v12.3: Reduced page size to 250KB for better performance)
        self.paging_engine = NotePagingEngine(self, page_size=250000)
        self.image_manager = NoteImageManager(self)
        
        self.textChanged.connect(self._on_content_modified)
        self.verticalScrollBar().valueChanged.connect(self.paging_engine.check_scroll)
        self._search_highlight_timer = None
        
        # Search Cache (Instance based to avoid clashing)
        self._plain_text_cache = None
        self._last_full_html = None
        
        # Zoom state
        self._zoom_factor = zoom  # percentage, 100 = default
        self._base_font_size = 13.0 # Default base size (100% zoom)
        
        # Sequential Search State
        self._current_page_start_line = 0 # 0-indexed
        
        # Selection tracking for Ctrl+F (saved before focus leaves)
        self._last_selection = ""
        
        # ALWAYS initialize theme and font on startup
        QTimer.singleShot(0, self._sync_initial_theme)
        
        # Emit format info when cursor moves — used to sync toolbar widgets
        self.cursorPositionChanged.connect(self._emit_cursor_format)


    def _emit_cursor_format(self):
        """Broadcast current char format so toolbar can update font size / color swatches."""
        self.cursor_format_changed.emit(self.currentCharFormat())

    def _sync_initial_theme(self):
        """Finds main window and applies current theme colors."""
        main_window = self.window()
        # Find the actual MainWindow if parented to something else
        while main_window and not hasattr(main_window, "theme_manager"):
            # Check if it's the root widget of a dock
            if hasattr(main_window, 'parentWidget'):
                main_window = main_window.parentWidget()
            else:
                break
            
        if main_window and hasattr(main_window, "theme_manager"):
            palette = main_window.theme_manager.get_theme_palette()
            text_color = QColor(palette.get('text', '#000000'))
            is_dark = palette.get('is_dark', True)
            self.apply_theme_colors(text_color, is_dark)
        
        self._apply_zoom()

    # ── Text Color / Highlight Color / Font Size ──────────────────────
    def set_font_size(self, size: int):
        """Apply explicit font size (pt) to current selection or next typed text."""
        if size <= 0:
            return
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        cursor.mergeCharFormat(fmt)
        self.setTextCursor(cursor)  # CRITICAL: apply back to the editor
        self.setFocus()

    def set_text_color(self, color: QColor):
        """Apply foreground color to selection."""
        if not color.isValid():
            return
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor.mergeCharFormat(fmt)
        self.setTextCursor(cursor)  # CRITICAL: apply back to the editor
        self.setFocus()

    def set_highlight_color(self, color: QColor):
        """Apply background highlight color to selection. Invalid color = clear."""
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        if color.isValid():
            fmt.setBackground(color)
        else:
            fmt.setBackground(Qt.GlobalColor.transparent)
        cursor.mergeCharFormat(fmt)
        self.setTextCursor(cursor)  # CRITICAL: apply back to the editor
        self.setFocus()

    def apply_theme_colors(self, text_color: QColor, is_dark: bool):
        """Explicitly update editor colors to match the theme."""
        # 1. Update default char format (for new text)
        fmt = self.currentCharFormat()
        fmt.setForeground(text_color)
        self.setCurrentCharFormat(fmt)
        
        # 2. Update palette for the widget itself
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Text, text_color)
        pal.setColor(QPalette.ColorRole.WindowText, text_color)
        self.setPalette(pal)
        
        # 3. Store for future resets
        self._theme_text_color = text_color
        self._is_dark_mode = is_dark

    def focusInEvent(self, event):
        """Tell MainWindow that this pane is now active."""
        super().focusInEvent(event)
        self.focus_received.emit(self)

    def focusOutEvent(self, event):
        """Save selected text before focus leaves so Ctrl+F can use it."""
        selected = self.textCursor().selectedText()
        if selected:
            self._last_selection = selected.replace('\u2029', ' ').strip()
        super().focusOutEvent(event)


    def _on_content_modified(self):
        self._is_dirty = True
        self.content_changed.emit()

    # ── Zoom In / Zoom Out ───────────────────────────────────────────

    def zoom_in(self):
        """Increase zoom by 10%, max 300%."""
        if self._zoom_factor < 300:
            self._zoom_factor += 10
            self._apply_zoom()
            logging.info(f"NotePane: Zoom In triggered. Current level: {self._zoom_factor}%")

    def zoom_out(self):
        """Decrease zoom by 10%, min 50%."""
        if self._zoom_factor > 50:
            self._zoom_factor -= 10
            self._apply_zoom()
            logging.info(f"NotePane: Zoom Out triggered. Current level: {self._zoom_factor}%")

    def zoom_reset(self):
        """Reset zoom to 100%."""
        self._zoom_factor = 100
        self._apply_zoom()

    def get_zoom(self):
        return self._zoom_factor

    def set_zoom(self, val):
        self._zoom_factor = val
        self._apply_zoom(force_full_refresh=True)

    def _apply_zoom(self, force_full_refresh=False):
        """
        Calculates and applies font size. 
        Plan v12.3: Made refresh optional and added byte-size safety guard.
        """
        # Ensure _base_font_size is sane
        base_size = self._base_font_size if self._base_font_size > 0 else 13.0
        new_size = max(1.0, base_size * (self._zoom_factor / 100.0))
        
        if new_size <= 0:
            logging.error(f"NotePane: INVALID font size calculated: {new_size} (zoom={self._zoom_factor}, base={base_size})")
            new_size = 13.0
        
        # 1. Update the document's default font (low cost, handles new text)
        doc = self.document()
        doc_font = doc.defaultFont()
        doc_font.setPointSizeF(new_size)
        doc.setDefaultFont(doc_font)
        
        # 2. Update widget font
        font = self.font()
        font.setPointSizeF(new_size)
        self.setFont(font)

        if not force_full_refresh:
            return

        # 3. SAFETY GUARD: If document is massive (> 500k characters), do NOT do full refresh
        # Plan v12.3: Use O(1) characterCount() instead of O(N) toHtml() which crashes.
        if doc.characterCount() > 500000:
            logging.warning("NotePane: Document too large for full zoom refresh. Skipping deep format.")
            return

        # 4. Full Document Refresh (High cost)
        self.blockSignals(True)
        try:
            curr_cursor = self.textCursor()
            pos = curr_cursor.position()
            anchor = curr_cursor.anchor()

            cursor = QTextCursor(doc)
            cursor.beginEditBlock()
            cursor.select(QTextCursor.SelectionType.Document)
            
            fmt = QTextCharFormat()
            fmt.setFontPointSize(new_size)
            cursor.mergeCharFormat(fmt)
            cursor.endEditBlock()
            
            # Restore cursor
            curr_cursor.setPosition(anchor)
            curr_cursor.setPosition(pos, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(curr_cursor)
        finally:
            self.blockSignals(False)
            
        self._show_zoom_status()

    def _show_zoom_status(self):
        """Show zoom level in status bar if available."""
        main_win = self.window()
        if hasattr(main_win, 'status_bar_manager'):
            main_win.status_bar_manager.show_message(f"Zoom: {self._zoom_factor}%", 1500)

    def wheelEvent(self, event):
        """Ctrl+Scroll = zoom, normal scroll = scroll."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            elif delta < 0:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event):
        """Handle shortcuts: Ctrl+Zoom, Tab/Shift+Tab for block indentation."""
        modifiers = event.modifiers()
        
        # 1. Zoom Shortcuts
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.zoom_in()
                return
            elif event.key() == Qt.Key.Key_Minus:
                self.zoom_out()
                return
            elif event.key() == Qt.Key.Key_0:
                self.zoom_reset()
                return
        
        # 2. Indentation Shortcuts (Nested Lists/Checkboxes)
        # Shift+Tab is recognized as Key_Backtab
        if event.key() == Qt.Key.Key_Tab and not (modifiers & Qt.KeyboardModifier.ControlModifier):
            self.apply_indent(increment=True)
            return
        elif event.key() == Qt.Key.Key_Backtab:
            self.apply_indent(increment=False)
            return
            
        # 3. Auto-Formatting on Space
        if event.key() == Qt.Key.Key_Space and not modifiers:
            cursor = self.textCursor()
            block = cursor.block()
            text = block.text()
            
            # Check if block is just a single hyphen (meaning cursor is right after it)
            if text == "-" and cursor.positionInBlock() == 1:
                # Remove the hyphen
                cursor.beginEditBlock()
                cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
                cursor.removeSelectedText()
                # Senior Fix: Trick QT into hiding the placeholder on empty documents by inserting a zero-width space
                cursor.insertText("\u200B")
                # Apply bullet list format
                self.apply_format("list")
                cursor.endEditBlock()
                # Intercept the space so it doesn't get inserted AFTER the bullet
                return
            
        super().keyPressEvent(event)

    def get_save_content(self):
        """
        Returns the content to be saved. Delegated to managers for safety.
        Returns None to SKIP saving in cases where saving would destroy data.
        """
        if self.paging_engine._loaded_length < len(self.paging_engine._full_content_html or ""):
            if not self._is_dirty:
                logging.debug("NotePane: Partial Paging view detected, skipping save to protect data.")
                return None
            else:
                logging.warning("NotePane: CRITICAL - User edited a partial Paged note. Returning FULL content.")
        
        if self.paging_engine.has_deferred():
            logging.info("NotePane: SKIPPED - deferred content not loaded yet")
            return None
        
        # Get processed HTML (images back to base64)
        html = self.toHtml()
        final_html = self.image_manager.get_html_with_base64(html)
        
        # Guard 3: Empty boilerplate check
        plain = self.toPlainText().strip()
        if not self._is_dirty and not plain and len(final_html) < 800:
            logging.info("NotePane: SKIPPED - empty boilerplate")
            return None
            
        return final_html

    def append_html_chunk(self, html):
        """Helper for PagingEngine to append content."""
        # Plan v12.3: Block scroll signals to prevent recursive loading loops
        self.verticalScrollBar().blockSignals(True)
        self.blockSignals(True)
        try:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertHtml(html)
            # Apply the current zoom level to the document default ensuring the chunk matches
            self._apply_zoom(force_full_refresh=False) 
        finally:
            self.blockSignals(False)
            self.verticalScrollBar().blockSignals(False)
        self._is_dirty = False

    def load_deferred_content(self):
        """Loads the content only when actually needed (visible)."""
        return self.paging_engine.load_deferred()

    def showEvent(self, event):
        """Triggered when the widget is shown. Perfect time for lazy loading."""
        super().showEvent(event)
        self.load_deferred_content()
    def set_html_safe(self, html):
        """Safely sets the document HTML with Paging support."""
        if not html:
            self.setHtml("")
            self.paging_engine.set_content("")
            return

        processed = self.image_manager.process_html_for_insertion(html)
        self.paging_engine.set_content(processed)
        self._apply_zoom(force_full_refresh=False) # Plan v12.3: Avoid expensive refresh on load
        self._is_dirty = False
        
    def highlight_search_result(self, query, line_number=0):
        """
        Highlights the occurrence of query on/near the target line_number.
        For paged notes, loads the required content first.
        """
        if not query: return
        logging.info(f"highlight_search_result: query='{query}', line={line_number}")
        
        # For paged documents, load content around the target line
        if self.paging_engine._full_content_html and line_number and line_number > 0:
            self._load_content_for_line(line_number, query)
            return
        
        # For normal documents, highlight directly (Ensure int)
        self._do_highlight(query, int(line_number) if line_number is not None else 0)
    
    def _load_content_for_line(self, line_number, query):
        """For paged documents, loads content around the target line using Indexing."""
        if not self.paging_engine._full_content_html:
            self._do_highlight(query, line_number)
            return

        # --- HIGH-PERFORMANCE SLICING ---
        offsets = self.paging_engine._line_offsets
        if not offsets:
             # Fallback if index isn't ready
             self._do_highlight(query, line_number)
             return
             
        total_lines = len(offsets)
        line_idx = max(0, min(line_number - 1, total_lines - 1))
        
        # Window: 100 lines before, 100 lines after
        start_idx = max(0, line_idx - 100)
        end_idx = min(total_lines - 1, line_idx + 100)
        
        self._current_page_start_line = start_idx
        
        # Relative line for the jump (0-indexed for findBlockByNumber)
        relative_line = line_idx - start_idx
        
        # Build context HTML by slicing the big buffer instead of joining small ones
        # This is O(1) memory operation in Python (string views / efficient slices)
        start_pos = offsets[start_idx]
        end_pos = offsets[min(end_idx + 1, total_lines - 1)] if end_idx + 1 < total_lines else len(self.paging_engine._full_content_html)
        
        raw_content = self.paging_engine._full_content_html[start_pos:end_pos]
        
        # Ensure block structure is preserved (PagingEngine uses <p> usually)
        if not raw_content.strip().startswith("<"):
            raw_content = f"<p>{raw_content}</p>"
        
        self.blockSignals(True)
        self.setHtml(raw_content)
        self._apply_zoom(force_full_refresh=False)
        self.blockSignals(False)
        self._is_dirty = False
        
        # Reset cursor to top so find() starts from beginning of new chunk
        self.moveCursor(QTextCursor.MoveOperation.Start)
        
        # Give UI a moment to render before jumping
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(20, lambda: self._do_highlight(query, relative_line))
    
    def _do_highlight(self, query, line_number=0):
        """Core highlight logic: finds the correct occurrence of query and highlights it."""
        doc = self.document()
        
        # Jump to block - line_number is 0-indexed here
        block = doc.findBlockByNumber(line_number)
        if block.isValid():
            from_cursor = QTextCursor(block)
            cursor = doc.find(query, from_cursor)
            if cursor.isNull():
                # Fallback: search from beginning of document
                cursor = doc.find(query)
        else:
            cursor = doc.find(query)
        
        if cursor.isNull():
            logging.warning(f"NotePane: Query '{query}' not found in document")
            return
        
        self._apply_search_selection(cursor)
        self._center_cursor_manually(cursor)
        
        logging.info(f"NotePane: Highlighted '{query}' at position {cursor.position()} (custom centered)")

    def _apply_search_selection(self, cursor):
        """Applies a bright yellow highlight to the given cursor selection."""
        from src.ui.style_registry import StyleRegistry
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor(StyleRegistry.SEARCH_HIGHLIGHT_COLOR))
        selection.format.setForeground(QColor("#000000"))
        selection.cursor = cursor
        self.setExtraSelections([selection])
        
        # Ensure cursor is set so "Find Next" works from this point
        self.setTextCursor(cursor)
        # ENTERPRISE FIX: Do NOT call setFocus() here.
        # This prevents the NotePane from stealing focus from the Find Bar overlay
        # during sequential search jumps (Enter key).

    def _center_cursor_manually(self, cursor):
        """Manually adjusts the vertical scrollbar to center the given cursor."""
        cursor_rect = self.cursorRect(cursor)
        vbar = self.verticalScrollBar()
        target_v = vbar.value() + cursor_rect.center().y() - self.viewport().height() // 2
        vbar.setValue(max(0, min(target_v, vbar.maximum())))

    # --- Search Buffer ---

    def get_total_matches(self, text, case_sensitive=False, whole_words=False):
        """
        Returns total matches in the document. 
        Plan v12.1: Optimized live search vs. buffer search.
        """
        if not text: return 0
        
        # 1. If document is small/fully loaded, use LIVE editor content (always accurate/up-to-date)
        if not self.paging_engine.is_paged() or self.paging_engine.is_fully_loaded():
            content = self.toPlainText()
            flags = 0
            if not case_sensitive:
                flags = re.IGNORECASE
            
            pattern_str = re.escape(text)
            if whole_words:
                pattern_str = rf"\b{pattern_str}\b"
            
            try:
                # Plan v12.2: Use generator expression with sum() for O(1) space counting
                return sum(1 for _ in re.finditer(pattern_str, content, flags=flags))
            except:
                # Fallback to simple count if regex fails (though re.escape should prevent it)
                if not case_sensitive:
                    content = content.lower()
                    text = text.lower()
                return content.count(text)
        
        # 2. For massive paged documents, fallback to the background HTML buffer
        return self.paging_engine.count_occurrences(text, case_sensitive, whole_words)

    def find_global(self, text, backward=False, case_sensitive=False, whole_words=False):
        """Sequential search across the entire document including hidden paging buffer."""
        # 1. Try standard find in the current visible chunk
        flags = QTextDocument.FindFlag(0)
        if (backward): flags |= QTextDocument.FindFlag.FindBackward
        if (case_sensitive): flags |= QTextDocument.FindFlag.FindCaseSensitively
        if (whole_words): flags |= QTextDocument.FindFlag.FindWholeWords
        
        if self.find(text, flags):
            cursor = self.textCursor()
            self._apply_search_selection(cursor)
            self._center_cursor_manually(cursor)
            return True 
            
        # 2. If not found in current chunk, search in the PagingEngine buffer
        if self.paging_engine._full_content_html:
            # Calculate current absolute char position for the jump
            current_cursor = self.textCursor()
            # DIAMOND FIX: Use end of selection for forward search to avoid re-finding same match
            rel_pos = current_cursor.selectionEnd() if not backward else current_cursor.selectionStart()
            
            # Absolute base for the current visible chunk
            chunk_base = 0
            if self._current_page_start_line < len(self.paging_engine._line_offsets):
                chunk_base = self.paging_engine._line_offsets[self._current_page_start_line]
            
            abs_start_pos = chunk_base + rel_pos
            
            # Find next absolute line
            line_number, abs_pos = self.paging_engine.get_line_for_match(
                text, 
                backward=backward, 
                case_sensitive=case_sensitive, 
                whole_words=whole_words,
                start_char_pos=abs_start_pos
            )
            
            if line_number != -1:
                logging.info(f"NotePane: Global search jumping to Line {line_number} (Pos {abs_pos})")
                self.highlight_search_result(text, line_number)
                return True
                
        return False



    def resizeEvent(self, event):
        super().resizeEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
             # Use precision spatial sensor
             img_cursor = self.image_manager.get_image_at_cursor(self.cursorForPosition(event.pos()), event.pos())
             if img_cursor:
                 self.image_manager.resize_image_dialog(img_cursor)
                 return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        """Provide visual feedback. ENTERPRISE OPTIMIZATION: Checkboxes hover freely, URLs/Images need CTRL."""
        # Qt's cursorForPosition often lands *after* a wide character if clicked on its right half.
        # So we check BOTH the character to the right AND the character to the left.
        cursor_pos = self.cursorForPosition(event.pos())
        
        # Check right side
        c_right = QTextCursor(cursor_pos)
        c_right.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
        char_right = c_right.selectedText()
        
        # Check left side
        c_left = QTextCursor(cursor_pos)
        c_left.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
        char_left = c_left.selectedText()
        
        valid_chars = ["▢", "☑", "☐", "〇", "✅"]
        is_over_checkbox = char_right in valid_chars or char_left in valid_chars
        
        # 1. Checkboxes ALWAYS show hand cursor
        if is_over_checkbox:
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
            if self._current_url_highlight:
                self.setExtraSelections([])
                self._current_url_highlight = None
            super().mouseMoveEvent(event)
            return

        modifiers = event.modifiers()
        has_ctrl = (modifiers & Qt.KeyboardModifier.ControlModifier)
        
        if not has_ctrl:
            if self._current_url_highlight:
                self.setExtraSelections([])
                self._current_url_highlight = None
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
            super().mouseMoveEvent(event)
            return

        # Only reach here if CTRL is held
        is_over_image = self.image_manager.get_image_at_cursor(cursor_pos, event.pos())
        url_data = self._get_url_at_pos(event.pos())
        
        if is_over_image or url_data:
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)

        # Highlight feedback (ExtraSelections)
        if url_data:
            url, start, end = url_data
            if self._current_url_highlight != (start, end):
                selection = QTextEdit.ExtraSelection()
                fmt = QTextCharFormat()
                fmt.setForeground(QColor("#3498db")) # Nice blue
                fmt.setFontUnderline(True)
                selection.format = fmt
                
                cursor = self.textCursor()
                cursor.setPosition(start)
                cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                selection.cursor = cursor
                
                self.setExtraSelections([selection])
                self._current_url_highlight = (start, end)
        else:
            if self._current_url_highlight:
                self.setExtraSelections([])
                self._current_url_highlight = None

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 1. Ctrl + Click URL detection
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                url_data = self._get_url_at_pos(event.pos())
                if url_data:
                    url = url_data[0] # Just the string
                    main_window = self.window()
                    dock_manager = getattr(main_window, 'dock_manager', None)
                    if dock_manager:
                        dock_manager.add_browser_dock(url)
                        return # Consume the event
            # Check for Checkbox Click
            cursor_pos = self.cursorForPosition(event.pos())
            
            # Check right side
            c_right = QTextCursor(cursor_pos)
            c_right.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            char_right = c_right.selectedText()
            
            # Check left side
            c_left = QTextCursor(cursor_pos)
            c_left.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
            char_left = c_left.selectedText()
            
            valid_chars = ["▢", "☑", "☐", "〇", "✅"]
            target_char = ""
            target_cursor = None
            
            if char_right in valid_chars:
                target_char = char_right
                target_cursor = c_right
            elif char_left in valid_chars:
                target_char = char_left
                target_cursor = c_left
            
            if target_char and target_cursor:
                # Use the perfectly matched Ballot Box pair (U+2610 and U+2611)
                new_char = "☑" if target_char in ["▢", "☐", "〇"] else "☐"
                
                # Insert the new character
                target_cursor.insertText(new_char)
                
                # Apply/Remove strikethrough for the ENTIRE block (which accidentally affects the checkbox too)
                block_cursor = QTextCursor(cursor_pos)
                block_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                fmt = QTextCharFormat()
                if new_char == "☑":
                    fmt.setFontStrikeOut(True)
                    fmt.setForeground(QColor("#888888")) # Muted gray for completed tasks
                else:
                    fmt.setFontStrikeOut(False)
                    # Reset to theme-aware default color
                    reset_color = getattr(self, "_theme_text_color", QColor("black"))
                    if not self._is_dark_mode and reset_color.lightness() > 200:
                        reset_color = QColor("black") # Safety for light theme
                    elif self._is_dark_mode and reset_color.lightness() < 50:
                        reset_color = QColor("white") # Safety for dark theme
                        
                    fmt.setForeground(reset_color)
                    
                block_cursor.mergeCharFormat(fmt)
                
                # NOW: Re-select JUST the checkbox character and force its size back to match the block text
                checkbox_cursor = QTextCursor(cursor_pos)
                # We need to explicitly find the start of the block to target the first character (the checkbox)
                checkbox_cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                
                # Get the current zoom/inherited font size from the text RIGHT AFTER the checkbox
                peek_cursor = QTextCursor(checkbox_cursor)
                peek_cursor.movePosition(QTextCursor.MoveOperation.Right)
                current_size = peek_cursor.charFormat().fontPointSize()
                if current_size <= 0:
                    current_size = 14 # Fallback
                
                checkbox_cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
                
                cfmt = QTextCharFormat()
                cfmt.setFontPointSize(current_size) # Matched perfectly with text
                cfmt.setFontFamily("Segoe UI Symbol") # Ensures identical glyph metrics
                # Explicitly remove strikethrough from the checkbox itself for a cleaner look
                cfmt.setFontStrikeOut(False) 
                
                checkbox_cursor.mergeCharFormat(cfmt)
                
                return 

        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """Enhanced context menu with specialized submenus and improved aesthetics."""
        menu = self.createStandardContextMenu()
        
        main_window = self.window()
        is_dark = getattr(main_window.theme_manager, "is_dark_mode", True) if hasattr(main_window, "theme_manager") else True
        from src.utils.ui_utils import get_icon
        
        # 1. Clean up & Iconify Standard Actions
        icon_map = {
            "Undo": "undo.svg", "Redo": "redo.svg", "Cut": "cut.svg", 
            "Copy": "copy.svg", "Paste": "clipboard.svg", "Delete": "trash.svg", 
            "Select All": "select-all.svg"
        }
        for action in menu.actions():
            clean_text = action.text().replace("&", "")
            if clean_text in icon_map:
                action.setIcon(get_icon(icon_map[clean_text], is_dark))

        menu.addSeparator()

        # 2. Alignment Submenu (Available for both text and images)
        align_menu = menu.addMenu(get_icon("align-left.svg", is_dark), "Alignment")
        align_map = {
            "Align Left": (Qt.AlignmentFlag.AlignLeft, "align-left.svg"),
            "Align Center": (Qt.AlignmentFlag.AlignCenter, "align-center.svg"),
            "Align Right": (Qt.AlignmentFlag.AlignRight, "align-right.svg"),
            "Justify": (Qt.AlignmentFlag.AlignJustify, "align-justify.svg")
        }
        for text, (align, icon) in align_map.items():
            act = align_menu.addAction(get_icon(icon, is_dark), text)
            act.triggered.connect(lambda checked=False, a=align: self.apply_alignment(a))

        # 3. Format Submenu
        format_menu = menu.addMenu(get_icon("bold.svg", is_dark), "Format")
        fmt_map = {
            "Bold": ("bold", "bold.svg"),
            "Italic": ("italic", "italic.svg"),
            "Underline": ("underline", "underline.svg"),
            "Strikethrough": ("strikethrough", "strikethrough.svg"),
            "Code Block": ("code", "code.svg"),
            "Highlight": ("highlight", "highlight.svg")
        }
        for text, (fmt, icon) in fmt_map.items():
            act = format_menu.addAction(get_icon(icon, is_dark), text)
            act.triggered.connect(lambda checked=False, f=fmt: self.apply_format(f))
        
        format_menu.addSeparator()
        format_menu.addAction(get_icon("trash.svg", is_dark), "Clear Formatting").triggered.connect(
            lambda: self.apply_format("clear"))

        # 4. Paragraph Submenu
        para_menu = menu.addMenu(get_icon("paragraph.svg", is_dark) if os.path.exists(os.path.join(self.window().theme_manager.base_path, "assets/icons/dark_theme/paragraph.svg")) else get_icon("list.svg", is_dark), "Paragraph")
        para_menu.addAction(get_icon("list.svg", is_dark), "Bullet List").triggered.connect(lambda: self.apply_format("list"))
        para_menu.addAction(get_icon("check.svg", is_dark), "Checkbox List").triggered.connect(lambda: self.apply_format("checkbox"))
        para_menu.addSeparator()
        para_menu.addAction(get_icon("refresh.svg", is_dark), "Increase Indent").triggered.connect(lambda: self.apply_indent(True))
        para_menu.addAction(get_icon("undo.svg", is_dark), "Decrease Indent").triggered.connect(lambda: self.apply_indent(False))

        # 5. Insert Submenu
        insert_menu = menu.addMenu(get_icon("note-add.svg", is_dark), "Insert")
        insert_menu.addAction(get_icon("image.svg", is_dark), "Image...").triggered.connect(self.insert_image_from_file)
        insert_menu.addAction(get_icon("table.svg", is_dark), "Table...").triggered.connect(lambda: self.apply_format("table"))
        insert_menu.addAction(get_icon("code.svg", is_dark), "Horizontal Rule").triggered.connect(self.insert_horizontal_rule)

        # 6. Specialized Image Options (Only if over image)
        img_cursor = self.image_manager.get_image_at_cursor(self.cursorForPosition(event.pos()), event.pos())
        if img_cursor:
            menu.addSeparator()
            _ic = img_cursor
            menu.addAction(get_icon("image.svg", is_dark), "Resize Image...").triggered.connect(
                lambda checked=False, ic=_ic: self.image_manager.resize_image_dialog(ic))
            menu.addAction(get_icon("refresh.svg", is_dark), "Reset Size").triggered.connect(
                lambda checked=False, ic=_ic: self.image_manager.reset_image_size(ic))
            menu.addAction(get_icon("clipboard.svg", is_dark), "Save Image As...").triggered.connect(
                lambda checked=False, ic=_ic: self.image_manager.save_image_as(ic))

        # 7. AI / Search / Translate (Move to top)
        cursor = self.textCursor()
        selected_text = cursor.selectedText().strip()
        if selected_text:
            menu.addSeparator()
            dock_manager = getattr(main_window, 'dock_manager', None)
            
            ai_act = QAction(get_icon("ai.svg", is_dark), "Ask AI", self)
            if dock_manager:
                ai_act.triggered.connect(lambda: dock_manager.add_browser_dock(f"https://www.perplexity.ai/?q={selected_text}"))

            search_act = QAction(get_icon("search.svg", is_dark), "Search on Google", self)
            if dock_manager:
                search_act.triggered.connect(lambda: dock_manager.add_browser_dock(f"https://www.google.com/search?q={selected_text}"))

            translate_act = QAction(get_icon("browser.svg", is_dark), "Translate to Vietnamese", self)
            if dock_manager:
                translate_act.triggered.connect(lambda: dock_manager.add_browser_dock(f"https://translate.google.com/?sl=auto&tl=vi&text={selected_text}&op=translate"))

            # Insert at top
            actions = menu.actions()
            menu.insertAction(actions[0], translate_act)
            menu.insertAction(translate_act, search_act) 
            menu.insertAction(search_act, ai_act)
            menu.insertSeparator(actions[3])

        menu.exec(event.globalPos())

    def insert_horizontal_rule(self):
        """Inserts a thematic break (horizontal rule)."""
        cursor = self.textCursor()
        cursor.insertHtml("<hr>")
        self.setFocus()

    def apply_strikethrough(self):
        """Toggles strikethrough on the current selection."""
        cursor = self.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontStrikeOut(not fmt.fontStrikeOut())
        cursor.mergeCharFormat(fmt)
        self.setTextCursor(cursor)
        self.setFocus()

    def apply_alignment(self, alignment):
        """Applies alignment to the current block(s)."""
        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(alignment)
        cursor = self.textCursor()
        cursor.mergeBlockFormat(block_fmt)
        self.setFocus()

    def apply_indent(self, increment=True):
        """Increase or decrease block indentation."""
        cursor = self.textCursor()
        block_fmt = cursor.blockFormat()
        indent = block_fmt.indent()
        if increment:
            block_fmt.setIndent(indent + 1)
        else:
            block_fmt.setIndent(max(0, indent - 1))
        cursor.setBlockFormat(block_fmt)
        self.setFocus()

    def apply_format(self, fmt_type):
        """Applies rich text formatting to the current selection."""
        cursor = self.textCursor()
        fmt = cursor.charFormat()
        
        if fmt_type == "bold":
            fmt.setFontWeight(QFont.Weight.Bold if fmt.fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal)
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "italic":
            fmt.setFontItalic(not fmt.fontItalic())
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "underline":
            fmt.setFontUnderline(not fmt.fontUnderline())
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "strikethrough":
            fmt.setFontStrikeOut(not fmt.fontStrikeOut())
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "list":
            cursor.createList(QTextListFormat.Style.ListDisc)
        elif fmt_type == "checkbox":
            # Smart Todo: Insert perfectly matched Ballot Box checkbox
            cursor.beginEditBlock()
            
            # Determine current font size before moving
            current_size = cursor.charFormat().fontPointSize()
            if current_size <= 0:
                current_size = 14 # Fallback
                
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            
            # Make the checkbox perfectly balanced
            cfmt = QTextCharFormat()
            cfmt.setFontPointSize(current_size)
            cfmt.setFontFamily("Segoe UI Symbol")
            cursor.insertText("☐", cfmt)
            
            # Reset format for the space and text that follows
            normal_fmt = QTextCharFormat()
            cursor.insertText(" ", normal_fmt)
            cursor.endEditBlock()
        elif fmt_type == "clear":
            # Reset char format and block format indent
            cursor.setCharFormat(QTextCharFormat())
            block_fmt = cursor.blockFormat()
            block_fmt.setIndent(0)
            cursor.setBlockFormat(block_fmt)
        elif fmt_type == "code":
            fmt.setFontFamilies(["Consolas", "Courier New", "Monospace"])
            fmt.setBackground(QColor("#444444"))
            fmt.setForeground(QColor("#e0e0e0"))
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "highlight":
            if fmt.background().color().name() == "#ffff00":
                fmt.setBackground(Qt.GlobalColor.transparent)
            else:
                fmt.setBackground(QColor("yellow"))
                fmt.setForeground(QColor("black"))
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "table":
            rows, ok1 = QInputDialog.getInt(self, "Insert Table", "Number of rows:", 3, 1, 50, 1)
            if not ok1:
                return
            cols, ok2 = QInputDialog.getInt(self, "Insert Table", "Number of columns:", 3, 1, 20, 1)
            if not ok2:
                return
            # Build table format
            tbl_fmt = QTextTableFormat()
            tbl_fmt.setCellPadding(4)
            tbl_fmt.setCellSpacing(0)
            tbl_fmt.setBorder(1)
            tbl_fmt.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
            tbl_fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
            # Even column widths
            col_width = 100.0 / cols
            tbl_fmt.setColumnWidthConstraints([
                QTextLength(QTextLength.Type.PercentageLength, col_width)
                for _ in range(cols)
            ])
            cursor.insertTable(rows, cols, tbl_fmt)
        elif fmt_type.startswith("align-"):
            mapping = {
                "align-left": Qt.AlignmentFlag.AlignLeft,
                "align-center": Qt.AlignmentFlag.AlignCenter,
                "align-right": Qt.AlignmentFlag.AlignRight,
                "align-justify": Qt.AlignmentFlag.AlignJustify
            }
            if fmt_type in mapping:
                self.apply_alignment(mapping[fmt_type])
            
        self.setFocus()


    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if image:
                if not isinstance(image, QImage): image = QImage(image)
                base64_data = self.image_manager.image_to_base64(image)
                processed_img = self.image_manager.process_html_for_insertion(f'<img src="data:image/png;base64,{base64_data}" />')
                self.textCursor().insertHtml(processed_img)
                return
        super().insertFromMimeData(source)

    def insert_image_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not file_path: return
        image = QImage(file_path)
        if image.isNull(): return
        base64_data = self.image_manager.image_to_base64(image)
        processed_img = self.image_manager.process_html_for_insertion(f'<img src="data:image/png;base64,{base64_data}" />')
        self.textCursor().insertHtml(processed_img)

    def get_content_with_embedded_images(self):
        """Exports HTML with images embedded as base64 data URIs."""
        self.load_deferred_content()
        html = self.toHtml()
        return self.image_manager.get_html_with_base64(html)

    def canInsertFromMimeData(self, source):
        return source.hasImage() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        """
        Override paste to handle very large text without freezing the UI.
        - Text < 1MB: normal Qt paste (fast, no intervention needed).
        - Text >= 1MB: chunked insert with processEvents() to yield back to Qt
          between chunks, while keeping the entire paste as ONE undo action.
        """
        if not source.hasText():
            super().insertFromMimeData(source)
            return

        text = source.text()
        SIZE_THRESHOLD = 1 * 1024 * 1024  # 1 MB

        if len(text.encode('utf-8')) < SIZE_THRESHOLD:
            # Small paste: use normal path (fastest, no overhead)
            super().insertFromMimeData(source)
            return

        # Large paste: chunked insert to keep UI responsive
        CHUNK_SIZE = 100_000  # 100K characters per chunk
        chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
        total = len(chunks)

        cursor = self.textCursor()
        cursor.beginEditBlock()  # All chunks = ONE Ctrl+Z undo action
        try:
            for i, chunk in enumerate(chunks):
                cursor.insertText(chunk)
                # Update status bar if available
                try:
                    mw = self.window()
                    if hasattr(mw, 'statusBar'):
                        mw.statusBar().showMessage(
                            f"Pasting large text... {i+1}/{total} ({(i+1)*100//total}%)", 0
                        )
                except Exception:
                    pass
                QApplication.processEvents()  # Yield to Qt event loop (keeps UI alive)
        finally:
            cursor.endEditBlock()
            try:
                mw = self.window()
                if hasattr(mw, 'statusBar'):
                    size_mb = len(text.encode('utf-8')) / 1024 / 1024
                    mw.statusBar().showMessage(f"Pasted {size_mb:.1f} MB of text.", 3000)
            except Exception:
                pass


    def _get_url_at_pos(self, pos):
        """Detects if a URL (anchor or plain text) exists at the given viewport position."""
        # 1. Check for explicit HTML anchor
        anchor = self.anchorAt(pos)
        
        # 2. Extract text at position regardless of anchor
        cursor = self.cursorForPosition(pos)
        block = cursor.block()
        block_text = block.text()
        col = cursor.positionInBlock()
        
        if not block_text:
            return (anchor, 0, 0) if anchor else None

        # --- Case A: Robust HTML Anchor Range Detection ---
        if anchor:
            # We need to find the full extent of this anchor in the current block
            # Scan fragments in the block
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                if frag.charFormat().isAnchor() and frag.charFormat().anchorHref() == anchor:
                    # Check if our column is within this fragment
                    f_start = frag.position() - block.position()
                    f_end = f_start + frag.length()
                    if f_start <= col <= f_end:
                        return (anchor, frag.position(), frag.position() + frag.length())
                it += 1
            # Fallback for anchor if spatial scan failed: use the word boundaries
            pass

        # --- Case B: Plain-Text URL Robust Detection (Regex) ---
        import re
        # Relaxed pattern for common web links
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+|[a-zA-Z0-9.-]+\.(com|net|org|edu|gov|io|vn)/[^\s<>"]*)'
        matches = list(re.finditer(url_pattern, block_text, re.IGNORECASE))
        
        for match in matches:
            if match.start() <= col <= match.end():
                full_url = match.group(0)
                if full_url.startswith("www."): full_url = "https://" + full_url
                
                global_start = block.position() + match.start()
                global_end = block.position() + match.end()
                return (full_url, global_start, global_end)
        
        # --- Case C: Final Fallback for Anchor (Word-based) ---
        if anchor:
            # Scan outward from col to find non-whitespace boundaries
            start = col
            while start > 0 and not block_text[start-1].isspace(): start -= 1
            end = col
            while end < len(block_text) and not block_text[end].isspace(): end += 1
            return (anchor, block.position() + start, block.position() + end)
            
        return None
    # Shared properties MainWindow expects
    @property
    def is_dirty(self): return self._is_dirty
    @is_dirty.setter
    def is_dirty(self, val): self._is_dirty = val
