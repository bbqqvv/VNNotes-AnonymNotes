import logging
from src.core.storage import StorageManager

class NoteService:
    """
    Service layer for managing Note data logic.
    Interfaces directly with the SQLite DAO StorageManager.
    """
    def __init__(self, storage_manager=None):
        self.storage = storage_manager or StorageManager()
        self._notes = [] # Cache of metadata
        self._is_loaded = False

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

    def add_note(self, title="New Note", content="", folder="General", tags=None):
        """Adds a new note entity directly to the DB."""
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
            "is_open": 1 # New notes start open
        }
        
        # Insert to DB
        self.storage.upsert_note_metadata(note)
        self.storage.save_note_content(note["obj_name"], content)
        
        # Refresh Cache
        self._notes.append(note)
        return note

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
        
        # Refresh metadata cache from DB
        self._notes = self.storage.get_all_notes()
        return True

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
            "content": "Welcome to VNNotes! <br> Lightning fast SQLite FTS5 search enables instant finding.",
            "folder": "General",
            "pinned": 0,
            "tags": []
        }
        
    def get_folders(self):
        return sorted(list(set(n.get("folder", "General") for n in self._notes)))

    def move_note(self, note_obj_name, new_folder):
        """Moves a note to a different folder in DB."""
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
            note["title"] = new_title
            self.storage.upsert_note_metadata(note)
            self._notes = self.storage.get_all_notes()
            return True
        return False

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
        return self.storage.search_notes_fts(query)
