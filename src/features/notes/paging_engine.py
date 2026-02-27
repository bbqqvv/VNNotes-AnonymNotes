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
        self._is_loading = False # Plan v12.3: Recursive loading guard

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
        
        # Plan v12.3: Use a pre-compiled, optimized pattern. 
        # Limit to 500k lines to prevent indexing-induced memory crashes.
        split_pattern = re.compile(r'<(?:br|p|div|li)[^>]*>|\n', re.IGNORECASE)
        self._line_offsets = [0]
        for i, match in enumerate(split_pattern.finditer(html)):
            self._line_offsets.append(match.end())
            if i > 500000:
                logging.warning("PagingEngine: Document exceeds 500k lines. Truncating index.")
                break
        
        logging.info(f"PagingEngine: Indexed {len(self._line_offsets)} lines.")

    def count_occurrences(self, text, case_sensitive=False, whole_words=False):
        """Memory-efficient occurrence count on the full buffer."""
        full_html = self._full_content_html or self._deferred_content or ""
        if not full_html or not text: return 0
        
        flags = re.IGNORECASE if not case_sensitive else 0
        pattern_str = re.escape(text)
        if whole_words:
            pattern_str = rf"\b{pattern_str}\b"
        
        # Plan v12.2: Use generator expression with sum() for O(1) space counting
        try:
            return sum(1 for _ in re.finditer(pattern_str, full_html, flags=flags))
        except Exception as e:
            logging.error(f"Search Count Failed: {e}")
            return 0

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
        if self._loaded_length >= len(full_html) or self._is_loading:
            return

        self._is_loading = True
        try:
            remaining = full_html[self._loaded_length:]
            next_limit = min(len(remaining), self.page_size)
            chunk = self._extract_safe_chunk(remaining, next_limit)
            
            self._loaded_length += len(chunk)
            
            # Append to editor - signals are blocked inside append_html_chunk
            self.editor.append_html_chunk(chunk)
            
            if self._loaded_length >= len(full_html):
                from src.ui.style_registry import StyleRegistry
                self.editor.append_html_chunk(StyleRegistry.PAGING_END_MESSAGE)
        finally:
            # Plan v12.3: Use a short timer to release the lock. 
            # This ensures that any pending scroll events triggered by the insertion
            # have finished processing before we allow the next chunk to be loaded.
            QTimer.singleShot(100, self._release_loading_lock)

    def _release_loading_lock(self):
        self._is_loading = False


    def load_deferred(self):
        if self._deferred_content is not None:
            content = self._deferred_content
            self._deferred_content = None
            self.editor.set_html_safe(content)
            return True
        return False

    def is_paged(self):
        """Returns True if the document is large enough to trigger paging."""
        full_html = self._full_content_html or self._deferred_content or ""
        return len(full_html) > self.page_size

    def is_fully_loaded(self):
        """Returns True if all chunks have been loaded into the editor."""
        full_html = self._full_content_html or ""
        return self._loaded_length >= len(full_html)

    def get_line_for_match(self, text, backward=False, case_sensitive=False, whole_words=False, start_char_pos=0):
        """
        Scans the full HTML buffer for occurrences of 'text'.
        Returns (line_number, abs_char_pos) or (-1, -1).
        Plan v12.2: Memory-safe sequential search using re.search with pos/endpos.
        """
        full_html = self._full_content_html or self._deferred_content or ""
        if not full_html or not text: return -1, -1
        
        import bisect
        flags = re.IGNORECASE if not case_sensitive else 0
        pattern_str = re.escape(text)
        if whole_words:
            pattern_str = rf"\b{pattern_str}\b"
        
        regex = re.compile(pattern_str, flags=flags)
        
        target_match = None
        if backward:
            # re.search doesn't support backward search natively on the whole string.
            # However, we can search in the substring [0, start_char_pos] and take the LAST match.
            # To stay memory-safe, we iterate matches up to start_char_pos.
            for m in regex.finditer(full_html, endpos=max(0, start_char_pos)):
                target_match = m
        else:
            # Forward search is easy with re.search(pos=...)
            target_match = regex.search(full_html, pos=max(0, start_char_pos))
            
        if not target_match:
            return -1, -1
            
        target_pos = target_match.start()
        # Map target_pos back to line number using binary search on pre-indexed offsets
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
        max_summary_items = 500 # Plan v12.2: Safety limit to prevent summary OOM
        for i, idx in enumerate(sorted(found_lines.keys())):
            if i >= max_summary_items:
                body_html.append(f"<b>... and {len(found_lines) - max_summary_items} more results.</b>")
                break
            line_content = html.escape(found_lines[idx])
            body_html.append(f"Line {idx}: {line_content}<br>")
            
        return "\n".join(header_html + body_html)
