import logging
import re
from PyQt6.QtCore import QTimer

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.features.notes.note_pane import NotePane

class NotePagingEngine:
    """
    Component to manage paging and lazy loading for NotePane.
    Handles massive documents by chunking content and loading on-demand.
    """
    def __init__(self, editor: "NoteEditor", page_size=200000):
        self.editor = editor
        self.page_size = page_size
        self._full_content_html: "str | None" = None
        self._deferred_content: "str | None" = None
        self._loaded_length = 0
        self._line_offsets = [] # Absolute char offsets of line starts

    def set_content(self, html):
        """Sets full content and prepares paging if needed."""
        if html is None: html = ""
        self._full_content_html = html
        self._loaded_length = 0
        self._deferred_content = None
        
        # Build line offset index for high-performance jumps
        self._build_index(html)
        
        if len(html) > self.page_size:
            chunk = self._extract_safe_chunk(html, self.page_size)
            self._loaded_length = len(chunk)
            from src.ui.style_registry import StyleRegistry
            self.editor.setHtml(chunk + StyleRegistry.PAGING_MESSAGE)
            logging.info(f"PagingEngine: Massive document detected ({len(html)} bytes). Paging enabled.")
            return True
        else:
            self.editor.setHtml(html)
            self._loaded_length = len(html) # CRITICAL: Mark as fully loaded for safety guards
            return False

    def _build_index(self, html):
        """Builds an index of absolute character offsets for line breaks (Tags and \n)."""
        if not html:
            self._line_offsets = [0]
            return
        
        # Use finditer for memory-efficient offset detection
        # Pattern matches the START of logical blocks or raw newlines
        split_pattern = r'<(?:br|p|div|li)[^>]*>|\n'
        self._line_offsets = [0] # First line starts at 0
        for match in re.finditer(split_pattern, html, flags=re.IGNORECASE|re.UNICODE):
            self._line_offsets.append(match.end())
        
        logging.info(f"PagingEngine: Indexed {len(self._line_offsets)} lines (including raw newlines).")

    def count_occurrences(self, text, case_sensitive=False, whole_words=False):
        """Memory-efficient occurrence count on the full buffer."""
        full_html = self._full_content_html or self._deferred_content or ""
        if not full_html or not text: return 0
        
        # We search once. If it's 100MB, this is O(N) but only one pass.
        import re
        flags = re.IGNORECASE if not case_sensitive else 0
        pattern_str = re.escape(text)
        if whole_words:
            pattern_str = rf"\b{pattern_str}\b"
        
        count = 0
        for _ in re.finditer(pattern_str, full_html, flags=flags):
            count += 1
        return count

    def set_deferred_content(self, content):
        """Standardizes deferred content handoff from managers."""
        self._deferred_content = content
        self._loaded_length = 0 # Not loaded yet
        self._full_content_html = None
        self._line_offsets = []
        logging.debug("PagingEngine: Deferred content registered.")

    def has_deferred(self):
        """Checks if there is pending content that hasn't been loaded into the editor yet."""
        return self._deferred_content is not None

    def _extract_safe_chunk(self, html, limit):
        """Extracts a chunk of HTML and attempts to close open tags safely."""
        chunk = html[:limit]
        last_tag = chunk.rfind("<")
        if last_tag != -1 and ">" not in chunk[last_tag:]:
              chunk = chunk[:last_tag]
        return chunk

    def check_scroll(self, value):
        """Triggered on scroll to check if more content should be loaded."""
        full_html = self._full_content_html or ""
        if self._loaded_length >= len(full_html):
            return

        sb = self.editor.verticalScrollBar()
        if value > sb.maximum() * 0.9:
            self.load_next_chunk()

    def load_next_chunk(self):
        """Appends the next chunk from the buffer to the editor."""
        full_html = self._full_content_html or ""
        if self._loaded_length >= len(full_html):
            return

        remaining = full_html[self._loaded_length:]
        next_limit = min(len(remaining), self.page_size)
        chunk = self._extract_safe_chunk(remaining, next_limit)
        
        self._loaded_length += len(chunk)
        
        # Append to editor - signals are blocked inside append_html_chunk
        self.editor.append_html_chunk(chunk)
        
        full_html = self._full_content_html or ""
        if self._loaded_length >= len(full_html):
            from src.ui.style_registry import StyleRegistry
            self.editor.append_html_chunk(StyleRegistry.PAGING_END_MESSAGE)


    def load_deferred(self):
        if self._deferred_content:
            content = self._deferred_content
            self._deferred_content = None
            self.editor.set_html_safe(content)
            return True
        return False

    def get_line_for_match(self, text, backward=False, case_sensitive=False, whole_words=False, start_char_pos=0):
        """
        Scans the full HTML buffer for occurrences of 'text'.
        Returns (line_number, abs_char_pos) or (-1, -1), prioritizing results after 'start_char_pos'.
        """
        full_html = self._full_content_html or self._deferred_content or ""
        if not full_html or not text: return -1, -1
        
        # --- HIGH-PERFORMANCE SEARCH ---
        import bisect
        flags = re.IGNORECASE if not case_sensitive else 0
        pattern_str = re.escape(text)
        if whole_words:
            pattern_str = rf"\b{pattern_str}\b"
        
        matches = [] # List of absolute char starts
        for match in re.finditer(pattern_str, full_html, flags=flags):
            matches.append(match.start())
        
        if not matches:
            return -1, -1
            
        # Sequential prioritization based on absolute position
        target_pos = -1
        if backward:
            # Find the largest match < start_char_pos
            candidates = [m for m in matches if m < start_char_pos]
            if not candidates: return -1, -1 # No more results in this direction
            target_pos = candidates[-1]
        else:
            # Find the smallest match > start_char_pos
            candidates = [m for m in matches if m > start_char_pos]
            if not candidates: return -1, -1 # No more results in this direction
            target_pos = candidates[0]
            
        # Map target_pos back to line number
        line_idx = bisect.bisect_right(self._line_offsets, target_pos)
        return line_idx, target_pos
            
    def get_matches_summary(self, text, case_sensitive=False):
        """Generates a full summary of all matching lines in the 100MB+ buffer."""
        full_html = self._full_content_html or self._deferred_content or ""
        if not full_html or not text: return "No results found."
        
        import re
        flags = re.IGNORECASE if not case_sensitive else 0
        pattern_str = re.escape(text)
        
        # Consolidate results by line index to avoid duplicates in the summary
        found_lines = {} # line_idx -> clean_content
        import bisect
        
        for match in re.finditer(pattern_str, full_html, flags=flags):
            pos = match.start()
            line_idx = bisect.bisect_right(self._line_offsets, pos)
            
            if line_idx not in found_lines:
                # Extract the line using pre-indexed offsets
                start = self._line_offsets[line_idx-1]
                end = self._line_offsets[line_idx] if line_idx < len(self._line_offsets) else len(full_html)
                raw_chunk = full_html[start:end]
                # Clean HTML for human-readable summary
                clean_chunk = re.sub(r'<[^>]+>', ' ', raw_chunk).strip()
                found_lines[line_idx] = clean_chunk

        if not found_lines:
            return "No matches found in the entire document."

        # Format the output as HTML to ensure scrolling and proper rendering
        import html
        header_html = [
            f"<h3 style='margin-bottom: 0px;'>SEARCH RESULTS FOR: '{html.escape(text)}'</h3>",
            f"<b>Total occurrences: {len(found_lines)} matching lines found.</b><br>",
            "<hr>",
            ""
        ]
        
        body_html = []
        for idx in sorted(found_lines.keys()):
            # Use <br> for line breaks to ensure the scrollbar appears in HTML mode
            line_content = html.escape(found_lines[idx])
            body_html.append(f"Line {idx}: {line_content}<br>")
            
        return "\n".join(header_html + body_html)
