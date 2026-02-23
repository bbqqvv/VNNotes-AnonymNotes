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
            
        # Migration Check: If notes in data.json still contain content, move it to files
        self._migrate_monolithic_to_distributed()
            
        self.sanitize_ids()
        self.sanitize_folders()
        self._is_loaded = True
        return self._notes

    def _migrate_monolithic_to_distributed(self):
        """
        Surgically moves note content from data.json to individual files if found.
        Cleans up memory immediately after migration.
        """
        migrated = False
        for note in self._notes:
            content = note.get("content")
            if content is not None:
                # Save to separate file
                self.storage.save_note_content(note["obj_name"], content)
                # Remove content from memory structure
                del note["content"]
                migrated = True
        
        if migrated:
            logging.info("NoteService: Migration to distributed storage complete.")
            self.save_to_disk() # Save the now-empty content list to data.json

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

    def sanitize_folders(self):
        """Removes trailing counts from folder names that were accidentally saved."""
        import re
        pattern = r"(\s\(\d+\))+$"
        changed = False
        for note in self._notes:
            folder = note.get("folder", "General")
            clean_name = re.sub(pattern, "", folder)
            if clean_name != folder:
                note["folder"] = clean_name
                changed = True
        if changed:
            logging.info("NoteService: Sanitized corrupted folder names in note data.")
            self.save_to_disk()

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
            "folder": folder
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
            content = ui_note.pop("content", None) # Extract content for separate saving
            
            if obj_name in existing_map:
                # Update existing metadata (title, folder, pinned, etc.)
                existing_map[obj_name].update(ui_note)
            else:
                # New Note
                if "folder" not in ui_note: ui_note["folder"] = "General"
                self._notes.append(ui_note)
            
            # Save content to its own file if provided
            if content is not None:
                self.storage.save_note_content(obj_name, content)
        
        # 3. Save Metadata to Disk (ASYNC)
        self.save_to_disk()
        return True

    def get_note_content(self, obj_name):
        """Retrieves content from individual file storage."""
        content = self.storage.load_note_content(obj_name)
        logging.info(f"NoteService: Loaded content for {obj_name} (len={len(content)})")
        return content

    def _extract_tags_from_note(self, note):
        """Regex to find #tag patterns in note content."""
        import re
        import html
        content = note.get("content", "")
        # Strip HTML for tagging search
        text = re.sub(r'<[^<]+?>', '', content)
        text = html.unescape(text)
        
        # Find tags: # followed by word characters, must be preceded by space or start of line
        tags = re.findall(r'(?:^|\s)#([\w\d]+)', text)
        note["tags"] = sorted(list(set(tags))) # Unique sorted tags

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
        """Deletes a note and its physical content file."""
        for i, note in enumerate(self._notes):
            if note["obj_name"] == note_obj_name:
                del self._notes[i]
                self.storage.delete_note_content(note_obj_name)
                return True
        return False

    def delete_notes_in_folder(self, folder_name):
        """Deletes all notes in a specific folder. Returns list of deleted obj_names."""
        to_delete = [n["obj_name"] for n in self._notes if n.get("folder") == folder_name]
        deleted_ids = []
        for obj_name in to_delete:
            if self.delete_note(obj_name):
                deleted_ids.append(obj_name)
        return deleted_ids

    def toggle_pin(self, note_obj_name):
        """Toggles the pinned status of a note."""
        for note in self._notes:
            if note["obj_name"] == note_obj_name:
                note["is_pinned"] = not note.get("is_pinned", False)
                return note["is_pinned"]
        return False

    def get_pinned_notes(self):
        """Returns all pinned notes."""
        return [n for n in self._notes if n.get("is_pinned", False)]

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

    def search_notes(self, query, cancel_check=None):
        """
        Searches notes for query string in title or content.
        Returns a list of matching note objects.
        Case-insensitive.
        cancel_check: optional callable returning True to abort early.
        """
        query = query.lower().strip()
        if not query:
            return self._notes

        matches = []
        import re
        import html as html_module
        
        # Robust HTML content extractor
        tag_re = re.compile(r'<[^<]+?>')
        script_re = re.compile(r'<(style|script)[^>]*>.*?</\1>', flags=re.DOTALL | re.IGNORECASE)

        def get_text_content(html_content):
            if not html_content: return ""
            # Convert common line-breaking tags to newlines before stripping
            text = re.sub(r'<(br|p|div|li|h[1-6])[^>]*>', '\n', html_content, flags=re.IGNORECASE)
            text = script_re.sub('', text)
            text = tag_re.sub('', text)
            return html_module.unescape(text)

        for note in self._notes:
            if cancel_check and cancel_check():
                return matches  # Early exit on cancellation
            note_matches = []
            title = note.get("title", "").strip()
            content_html = note.get("content", "")
            
            # DECENTRALIZED SEARCH: If content isn't in memory, pull it from disk for searching
            if not content_html:
                content_html = self.get_note_content(note["obj_name"])
            
            # FAST CHECK: If query isn't in raw title or raw HTML, definitely skip
            if query not in title.lower() and query not in content_html.lower():
                continue

            # 1. Title Match
            if query in title.lower():
                 note_matches.append({"type": "title", "text": title})
            
            # 2. Content Match (Only do expensive text stripping if found in raw HTML)
            if query in content_html.lower():
                content_text = get_text_content(content_html)
                if query in content_text.lower():
                    lines = content_text.split('\n')
                    match_count = 0
                    for i, line in enumerate(lines):
                        if query in line.lower():
                            idx = line.lower().find(query)
                            start = max(0, idx - 30)
                            end = min(len(line), idx + len(query) + 30)
                            snippet = line[start:end].strip()
                            if start > 0: snippet = "..." + snippet
                            if end < len(line): snippet = snippet + "..."
                            if snippet:
                                note_matches.append({"type": "content", "line": i + 1, "text": snippet})
                                match_count += 1
                                if match_count >= 20: # Limit snippets for massive notes
                                    note_matches.append({"type": "status", "text": "... and more found"})
                                    break
            
            if note_matches:
                matches.append({
                    "note": note,
                    "matches": note_matches
                })
        
        return matches
