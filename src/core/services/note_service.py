import logging
from src.core.storage import StorageManager

class NoteService:
    """
    Service layer for managing Note data logic.
    Decoupled from PyQt UI components.
    """
    def __init__(self, storage_manager=None):
        self.storage = storage_manager or StorageManager()
        self._notes = [] # Internal list of note entities (dicts)
        self._is_loaded = False # Data integrity guard

    def load_notes(self):
        """Loads notes from storage into memory."""
        data = self.storage.load_data()
        if data is None:
             logging.error("NoteService: CRITICAL - Storage load failed. notes initialized in SAFE MODE (No saving allowed).")
             self._is_loaded = False
             return []
             
        self._notes = data.get("notes", [])
        if not self._notes:
            self._notes = [self.create_default_note_data()]
            
        self.sanitize_ids()
        self._is_loaded = True
        return self._notes

    def sanitize_ids(self):
        """Ensures all notes have unique object names."""
        seen_ids = set()
        max_id = 0
        
        # simple pass to find max id
        for note in self._notes:
             obj_name = note.get("obj_name", "")
             if obj_name.startswith("NoteDock_"):
                 try:
                     nid = int(obj_name.split("_")[1])
                     if nid > max_id: max_id = nid
                 except ValueError:
                     pass
        
        # second pass to fix duplicates
        for note in self._notes:
            obj_name = note.get("obj_name", "")
            if not obj_name or obj_name in seen_ids:
                max_id += 1
                new_name = f"NoteDock_{max_id}"
                note["obj_name"] = new_name
                obj_name = new_name
            seen_ids.add(obj_name)

    def get_notes(self):
        return self._notes

    def add_note(self, title="New Note", content="", folder="General", tags=None):
        """Adds a new note entity."""
        # Find max ID
        max_id = 0
        for note in self._notes:
             obj_name = note.get("obj_name", "")
             if obj_name.startswith("NoteDock_"):
                 try:
                     nid = int(obj_name.split("_")[1])
                     if nid > max_id: max_id = nid
                 except ValueError:
                     pass
                     
        new_id = max_id + 1
        note = {
            "obj_name": f"NoteDock_{new_id}",
            "title": title,
            "content": content,
            "folder": folder,
            "tags": tags or []
        }
        self._notes.append(note)
        return note

    def sync_to_storage(self, current_notes_data):
        """
        Syncs the current UI state of notes to persistent storage.
        Merges `current_notes_data` (open notes) into `self._notes`.
        """
        if not self._is_loaded:
            logging.warning("NoteService: sync_to_storage BLOCKED - Service not initialized correctly.")
            return False

        # 1. Create a lookup for existing notes
        existing_map = {n["obj_name"]: n for n in self._notes}
        
        # 2. Update or Add notes from UI
        for ui_note in current_notes_data:
            obj_name = ui_note["obj_name"]
            if obj_name in existing_map:
                # Update existing (keep folder/tags if UI doesn't provide them)
                existing_map[obj_name]["title"] = ui_note.get("title", existing_map[obj_name]["title"])
                existing_map[obj_name]["content"] = ui_note.get("content", existing_map[obj_name].get("content", ""))
            else:
                # New Note (should have been added via add_note, but safety first)
                if "folder" not in ui_note: ui_note["folder"] = "General"
                if "tags" not in ui_note: ui_note["tags"] = []
                self._notes.append(ui_note)
        
        # 3. Save to Disk (ASYNC)
        # self.storage.save_data(data) <- REMOVE SYNC SAVE
        self.save_to_disk()
        return True

    def save_to_disk(self):
        """Persists current state to disk asynchronously."""
        if not self._is_loaded:
             logging.error("NoteService: save_to_disk BLOCKED - Internal state was never safely loaded.")
             return

        data = self.storage.load_data() 
        if data is None:
            logging.error("NoteService: Aborting save_to_disk because storage load failed (lock or error).")
            return
            
        data["notes"] = self._notes
        self.storage.save_data(data, async_save=True)

    def create_default_note_data(self):
        return {
            "obj_name": "NoteDock_1",
            "title": "Welcome Note",
            "content": "Welcome to VNNotes! <br> organizing your thoughts...",
            "folder": "General",
            "tags": ["welcome"]
        }
        
    def get_folders(self):
        """Returns a set of all unique folders."""
        return sorted(list(set(n.get("folder", "General") for n in self._notes)))

    def move_note(self, note_obj_name, new_folder):
        """Moves a note to a different folder."""
        for note in self._notes:
            if note["obj_name"] == note_obj_name:
                note["folder"] = new_folder
                return True
        return False

    def rename_note(self, note_obj_name, new_title):
        """Renames a note."""
        for note in self._notes:
            if note["obj_name"] == note_obj_name:
                note["title"] = new_title
                return True
    def delete_note(self, note_obj_name):
        """Deletes a note."""
        for i, note in enumerate(self._notes):
            if note["obj_name"] == note_obj_name:
                del self._notes[i]
                return True
        return False

    def rename_folder(self, old_name, new_name):
        """Renames a folder by updating all notes within it."""
        if not new_name or new_name == old_name: return False
        
        updated = False
        for note in self._notes:
            if note.get("folder") == old_name:
                note["folder"] = new_name
                updated = True
        
        return updated

    def get_note_by_id(self, note_obj_name):
        """Retrieves a note dict by its object name."""
        for note in self._notes:
            if note["obj_name"] == note_obj_name:
                return note
        return None

    def search_notes(self, query):
        """
        Searches notes for query string in title or content.
        Returns a list of matching note objects.
        Case-insensitive.
        """
        query = query.lower().strip()
        if not query:
            return self._notes

        matches = []
        import re
        import html as html_module # Avoid conflict with html variable name if used
        
        # Robust HTML content extractor
        def get_text_content(html_content):
            if not html_content: return ""
            # 1. Remove style and script blocks (non-greedy, dotall)
            text = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            # 2. Remove HTML tags
            text = re.sub(r'<[^<]+?>', '', text)
            # 3. Decode HTML entities (e.g. &nbsp; -> space, &lt; -> <)
            text = html_module.unescape(text)
            return text

        for note in self._notes:
            note_matches = []
            title = note.get("title", "").strip()
            content_html = note.get("content", "")
            content_text = get_text_content(content_html)
            
            # 1. Title Match
            if query in title.lower():
                 note_matches.append({"type": "title", "text": title})
            
            # 2. Content Match (Find all occurrences)
            lines = content_text.split('\n')
            for i, line in enumerate(lines):
                line_stripped = line.strip() # Remove excessive whitespace in line check
                if query in line.lower():
                    # Extract snippet
                    idx = line.lower().find(query)
                    
                    # Improve snippet extraction to be around the match
                    start = max(0, idx - 30)
                    end = min(len(line), idx + len(query) + 30)
                    
                    snippet = line[start:end].strip()
                    if start > 0: snippet = "..." + snippet
                    if end < len(line): snippet = snippet + "..."
                    
                    # Only add if relevant (avoid empty lines that somehow matched??)
                    if snippet:
                        note_matches.append({"type": "content", "line": i + 1, "text": snippet})
            
            if note_matches:
                matches.append({
                    "note": note,
                    "matches": note_matches
                })
        
        return matches
