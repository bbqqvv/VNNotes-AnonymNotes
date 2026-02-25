import logging
from src.core.storage import StorageManager

class NoteService:
    """
    Service layer for managing Note data logic.
    Interfaces directly with the SQLite DAO StorageManager.
    """
    def __init__(self, storage_manager=None):
        import json
        self.storage = storage_manager or StorageManager()
        self._notes = [] # Cache of metadata
        self._is_loaded = False
        
        # Load true folder lock state from DB app_settings
        locked_json = self.storage.get_app_setting("locked_folders", "{}")
        try:
            self.locked_folders = json.loads(locked_json)
        except:
            self.locked_folders = {}

    def load_notes(self):
        """
        Loads notes from SQLite. 
        Returns ONLY open notes for session restoration, but caches ALL for sidebar.
        """
        all_notes = self.storage.get_all_notes(only_open=False)
        self._notes = all_notes # Sidebar cache always has everything
        
        if not self._notes:
            default_note = self.create_default_note_data()
            self.storage.upsert_note_metadata(default_note)
            self.storage.save_note_content(default_note["obj_name"], default_note.pop("content"))
            self._notes = [default_note]
            
        self._is_loaded = True
        
        # Return only the ones that should be open as tabs
        return [n for n in self._notes if n.get("is_open", 1)]

    def get_notes(self):
        return self._notes

    def add_note(self, title="New Note", content="", folder="General", tags=None, is_open=1, is_placeholder=0):
        """Adds a new note entity directly to the DB."""
        # Plan v12.7: Automatic Unique Title numbering
        title = self._get_unique_title(title, folder)
        
        # Find max ID from DB or Cache
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
            "folder": folder,
            "pinned": 0,
            "is_open": is_open,
            "is_placeholder": is_placeholder,
            "is_locked": 0
        }
        
        # Insert to DB
        self.storage.upsert_note_metadata(note)
        self.storage.save_note_content(note["obj_name"], content)
        
        # Refresh Cache
        self._notes.append(note)
        return note

    def _get_unique_title(self, title, folder, exclude_obj_name=None):
        """Ensures title is unique within a folder by appending (N)."""
        target_folder = folder.strip() if folder else "General"
        existing_titles = [
            n["title"].lower().strip() for n in self._notes 
            if n.get("folder", "General").strip() == target_folder 
            and n["obj_name"] != exclude_obj_name
            and not n.get("is_placeholder") # Fix: Placeholders don't claim titles
        ]
        
        if title.lower() not in existing_titles:
            return title
            
        base_title = title
        counter = 2
        # Check if title already ends with (N)
        import re
        match = re.search(r" \((\d+)\)$", title)
        if match:
            base_title = title[:match.start()]
            counter = int(match.group(1)) + 1
        
        new_title = f"{base_title} ({counter})"
        while new_title.lower() in existing_titles:
            counter += 1
            new_title = f"{base_title} ({counter})"
        return new_title

    def sync_to_storage(self, current_notes_data):
        """
        Syncs the current UI state of notes to persistent storage.
        Merges `current_notes_data` (open notes) into DB.
        """
        if not self._is_loaded:
            return False

        # Plan v8.1: Reset all to closed first, then 'open' the ones currently in the UI
        self.storage.set_all_notes_closed()

        for ui_note in current_notes_data:
            obj_name = ui_note["obj_name"]
            content = ui_note.pop("content", None) # Extract content
            
            # Mark as open since it's in current_notes_data
            ui_note["is_open"] = 1
            
            # Upsert DB
            self.storage.upsert_note_metadata(ui_note)
            if content is not None:
                self.storage.save_note_content(obj_name, content)
                
                # Plan v12.6: Extract and update links (The Knowledge Graph)
                target_links = self.extract_internal_links(content)
                self.storage.update_note_links(obj_name, target_links)
        
        # Refresh metadata cache from DB
        self._notes = self.storage.get_all_notes()
        return True

    def extract_internal_links(self, html):
        """Extracts all vnnote://NoteDock_ID links from HTML content."""
        import re
        if not html: return []
        # Pattern to match vnnote://NoteDock_123 in href
        pattern = r'href=["\']vnnote://(NoteDock_\d+)["\']'
        matches = re.findall(pattern, html)
        return list(set(matches)) # Unique links only

    def get_note_content(self, obj_name):
        """Retrieves content from DB storage."""
        return self.storage.load_note_content(obj_name)

    def save_to_disk(self):
        """Legacy API - SQLite handles immediate persistence on sync_to_storage."""
        pass

    def create_default_note_data(self):
        return {
            "obj_name": "NoteDock_1",
            "title": "Welcome Note",
            "content": "Welcome to VNNotes!",
            "folder": "General",
            "pinned": 0,
            "tags": []
        }
        
    def get_folders(self):
        return sorted(list(set(n.get("folder", "General") for n in self._notes)))

    def move_note(self, note_obj_name, new_folder):
        """Moves a note to a different folder in DB."""
        if self.is_folder_locked(new_folder):
            return False # Prevent moving notes into a locked vault
            
        note = self.get_note_by_id(note_obj_name)
        if note:
            note["folder"] = new_folder
            self.storage.upsert_note_metadata(note)
            self._notes = self.storage.get_all_notes()
            return True
        return False

    def rename_note(self, note_obj_name, new_title):
        note = self.get_note_by_id(note_obj_name)
        if note:
            # Plan v12.7: Unique Title numbering on rename
            new_title = self._get_unique_title(new_title, note.get("folder"), exclude_obj_name=note_obj_name)
            note["title"] = new_title
            self.storage.upsert_note_metadata(note)
            self._notes = self.storage.get_all_notes()
            return new_title
        return None

    def delete_note(self, note_obj_name):
        """Deletes note from DB (Cascades)."""
        if self.storage.delete_note(note_obj_name):
            self._notes = self.storage.get_all_notes()
            return True
        return False

    def delete_notes_in_folder(self, folder_name):
        to_delete = [n["obj_name"] for n in self._notes if n.get("folder") == folder_name]
        for obj_name in to_delete:
            self.delete_note(obj_name)
        return to_delete

    def toggle_pin(self, note_obj_name):
        note = self.get_note_by_id(note_obj_name)
        if note:
            note["pinned"] = 0 if note.get("pinned", 0) else 1
            self.storage.upsert_note_metadata(note)
            self._notes = self.storage.get_all_notes()
            return bool(note["pinned"])
        return False

    def get_pinned_notes(self):
        return [n for n in self._notes if n.get("pinned", 0)]

    def rename_folder(self, old_name, new_name):
        if not new_name or new_name == old_name: return False
        updated = False
        for note in self._notes:
            if note.get("folder") == old_name:
                note["folder"] = new_name
                self.storage.upsert_note_metadata(note)
                updated = True
        
        if updated:
            self._notes = self.storage.get_all_notes()
        return updated

    def get_note_by_id(self, note_obj_name):
        for note in self._notes:
            if note["obj_name"] == note_obj_name:
                return note
        return None

    def search_notes(self, query, cancel_check=None):
        """
        Delegates search to SQLite's ultra-fast FTS5 engine.
        Bypasses python loops and regex entirely.
        """
        results = self.storage.search_notes_fts(query)
        # Filter out results from locked folders
        filtered_results = []
        for r in results:
            if not self.is_folder_locked(r.get("folder", "General")):
                filtered_results.append(r)
        return filtered_results

    def lock_note(self, note_obj_name, password):
        """Locks a note with a hashed password."""
        import hashlib
        note = self.get_note_by_id(note_obj_name)
        if note:
            # We use a simple SHA256 with note's own obj_name as salt for local security
            salt = note_obj_name.encode()
            pwd_hash = hashlib.sha256(salt + password.encode()).hexdigest()
            
            note["is_locked"] = 1
            note["password_hash"] = pwd_hash
            self.storage.upsert_note_metadata(note)
            self._notes = self.storage.get_all_notes()
            return True
        return False

    def unlock_note(self, note_obj_name, password):
        """Checks password and unlocks a note."""
        import hashlib
        note = self.get_note_by_id(note_obj_name)
        if note and note.get("is_locked"):
            salt = note_obj_name.encode()
            pwd_hash = hashlib.sha256(salt + password.encode()).hexdigest()
            
            if pwd_hash == note.get("password_hash"):
                note["is_locked"] = 0
                note["password_hash"] = None
                self.storage.upsert_note_metadata(note)
                self._notes = self.storage.get_all_notes()
                return True
        return False

    def verify_note_password(self, note_obj_name, password):
        """Verifies if the password matches without unlocking."""
        import hashlib
        note = self.get_note_by_id(note_obj_name)
        if note and note.get("is_locked"):
            salt = note_obj_name.encode()
            pwd_hash = hashlib.sha256(salt + password.encode()).hexdigest()
            return pwd_hash == note.get("password_hash")
        return False

    def is_folder_locked(self, folder_name):
        """Checks if the folder is tracked in the secure vault list."""
        return folder_name in self.locked_folders

    def lock_folder(self, folder_name, password):
        """Secures a folder by adding it to the persistent vault list."""
        import hashlib
        import json
        
        # Check if the folder exists or has notes (basic sanity check)
        folder_exists = any(n.get("folder", "General") == folder_name for n in self._notes)
        if not folder_exists:
            return False
            
        salt = folder_name.encode()
        pwd_hash = hashlib.sha256(salt + password.encode()).hexdigest()
        
        self.locked_folders[folder_name] = pwd_hash
        self.storage.set_app_setting("locked_folders", json.dumps(self.locked_folders))
        return True

    def unlock_folder(self, folder_name, password):
        """Removes a folder from the secure vault list if password matches."""
        import hashlib
        import json
        
        if folder_name not in self.locked_folders:
            return False
            
        salt = folder_name.encode()
        pwd_hash = hashlib.sha256(salt + password.encode()).hexdigest()
        
        if pwd_hash == self.locked_folders[folder_name]:
            del self.locked_folders[folder_name]
            self.storage.set_app_setting("locked_folders", json.dumps(self.locked_folders))
            return True
            
        return False
