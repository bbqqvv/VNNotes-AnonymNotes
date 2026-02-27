import logging
import re
from typing import List, Optional, Dict, Any
from src.domain.interfaces import IStorage
from src.domain.models import Note, Folder
from src.infrastructure.storage import StorageManager

class NoteService:
    """
    Service layer for managing Note data logic.
    Interfaces with the IStorage abstraction for enterprise readiness.
    """
    def __init__(self, storage_manager: Optional[IStorage] = None):
        self.storage = storage_manager or StorageManager()
        self._notes: List[Note] = [] # Cache of Note models
        self._folders: List[Folder] = [] # Cache of Folder models
        self._is_loaded = False

    def load_notes(self) -> List[Note]:
        """
        Loads notes and folders from storage. 
        Returns ONLY open notes for session restoration.
        """
        self._notes = self.storage.get_all_notes(only_open=False)
        self._folders = self.storage.get_folders()
        
        if not self._notes:
            default_note_data = self.create_default_note_data()
            default_note = Note.from_dict(default_note_data)
            self.storage.upsert_note_metadata(default_note)
            self.storage.save_note_content(default_note.obj_name, default_note_data.pop("content"))
            self._notes = self.storage.get_all_notes(only_open=False)
            self._folders = self.storage.get_folders()
            
        self._is_loaded = True
        return [n for n in self._notes if n.is_open]

    def get_notes(self) -> List[Note]:
        return self._notes

    def get_pinned_notes(self) -> List[Note]:
        """Returns all notes currently pinned."""
        return [n for n in self._notes if n.pinned]

    def add_note(self, title="New Note", content="", folder="General", pinned=False, is_open=True, is_placeholder=False) -> Note:
        """Adds a new note entity via the model layer."""
        title = self._get_unique_title(title, folder)
        
        # Find max ID for local naming
        max_id = 0
        for note in self._notes:
             if note.obj_name.startswith("NoteDock_"):
                 try:
                     nid = int(note.obj_name.split("_")[1])
                     if nid > max_id: max_id = nid
                 except ValueError: pass
                       
        new_id = max_id + 1
        new_note = Note(
            obj_name=f"NoteDock_{new_id}",
            title=title,
            folder=folder,
            pinned=pinned,
            is_open=is_open,
            is_placeholder=is_placeholder
        )
        
        # Persistent storage
        self.storage.upsert_note_metadata(new_note)
        self.storage.save_note_content(new_note.obj_name, content)
        
        # Refresh Cache
        self._notes.append(new_note)
        self._folders = self.storage.get_folders()
        return new_note

    def _get_unique_title(self, title: str, folder_name: str, exclude_obj_name: Optional[str] = None) -> str:
        """Ensures title is unique within a folder (Enterprise logic)."""
        target_folder = folder_name.strip() if folder_name else "General"
        existing_titles = [
            n.title.lower().strip() for n in self._notes 
            if n.folder.strip() == target_folder 
            and n.obj_name != exclude_obj_name
            and not n.is_placeholder
        ]
        
        if title.lower() not in existing_titles:
            return title
            
        base_title = title
        counter = 2
        match = re.search(r" \((\d+)\)$", title)
        if match:
            base_title = title[:match.start()]
            counter = int(match.group(1)) + 1
        
        new_title = f"{base_title} ({counter})"
        while new_title.lower() in existing_titles:
            counter += 1
            new_title = f"{base_title} ({counter})"
        return new_title

    def sync_to_storage(self, current_notes_data: List[Dict[str, Any]]) -> bool:
        """
        Syncs the current UI state (dicts from QT) into Domain Models and Persistance.
        """
        if not self._is_loaded: return False

        # Close all first for session sync
        if hasattr(self.storage, 'set_all_notes_closed'):
            self.storage.set_all_notes_closed()

        for ui_note_dict in current_notes_data:
            obj_name = ui_note_dict["obj_name"]
            content = ui_note_dict.pop("content", None)
            
            # Retrieve or Create model
            note = self.get_note_by_id(obj_name)
            if note:
                # Update model from UI dict
                note.title = ui_note_dict.get("title", note.title)
                note.folder = ui_note_dict.get("folder", note.folder)
                note.pinned = bool(ui_note_dict.get("pinned", note.pinned))
                note.is_open = True # Currently in UI means it's open
            else:
                # Defensive: Should theoretically exists in cache if UI has it
                note = Note.from_dict(ui_note_dict)
                note.is_open = True
            
            self.storage.upsert_note_metadata(note)
            if content is not None:
                self.storage.save_note_content(obj_name, content)
                # Link Graph update
                target_links = self.extract_internal_links(content)
                if hasattr(self.storage, 'update_note_links'):
                    self.storage.update_note_links(obj_name, target_links)
        
        self._notes = self.storage.get_all_notes()
        return True

    def extract_internal_links(self, html: str) -> List[str]:
        if not html: return []
        pattern = r'href=["\']vnnote://(NoteDock_\d+)["\']'
        matches = re.findall(pattern, html)
        return list(set(matches))

    def get_note_content(self, obj_name: str) -> str:
        return self.storage.load_note_content(obj_name)

    def save_to_disk(self):
        """
        Manually trigger storage persistence. 
        In current SQLite implementation, this is largely handled per-op,
        but provides an enterprise hook for manual flushing.
        """
        if hasattr(self.storage, 'save_to_disk'):
            self.storage.save_to_disk()

    def create_default_note_data(self) -> Dict[str, Any]:
        return {
            "obj_name": "NoteDock_1",
            "title": "Welcome Note",
            "content": "Welcome to VNNotes!",
            "folder": "General",
            "pinned": 0
        }
        
    def get_folders(self) -> List[str]:
        return sorted([f.name for f in self._folders])

    def move_note(self, note_obj_name: str, new_folder: str) -> bool:
        if self.is_folder_locked(new_folder): return False
            
        note = self.get_note_by_id(note_obj_name)
        if note:
            note.folder = new_folder
            self.storage.upsert_note_metadata(note)
            self._notes = self.storage.get_all_notes()
            self._folders = self.storage.get_folders()
            return True
        return False

    def rename_note(self, note_obj_name: str, new_title: str) -> Optional[str]:
        note = self.get_note_by_id(note_obj_name)
        if note:
            new_title = self._get_unique_title(new_title, note.folder, exclude_obj_name=note_obj_name)
            note.title = new_title
            self.storage.upsert_note_metadata(note)
            self._notes = self.storage.get_all_notes()
            self._folders = self.storage.get_folders()
            return new_title
        return None

    def delete_note(self, note_obj_name: str) -> bool:
        if self.storage.delete_note(note_obj_name):
            self._notes = self.storage.get_all_notes()
            return True
        return False

    def toggle_pin(self, note_obj_name: str) -> bool:
        note = self.get_note_by_id(note_obj_name)
        if note:
            note.pinned = not note.pinned
            self.storage.upsert_note_metadata(note)
            self._notes = self.storage.get_all_notes()
            return note.pinned
        return False

    def rename_folder(self, old_name: str, new_name: str) -> bool:
        if not new_name or new_name == old_name: return False
        if self.storage.rename_folder(old_name, new_name):
            self._notes = self.storage.get_all_notes()
            self._folders = self.storage.get_folders()
            return True
        return False

    def get_note_by_id(self, note_obj_name: str) -> Optional[Note]:
        for note in self._notes:
            if note.obj_name == note_obj_name:
                return note
        return None

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        results = self.storage.search_notes_fts(query)
        filtered_results = []
        for r in results:
            note_meta_dict = r.get("note", {})
            folder_name = note_meta_dict.get("folder", "General")
            if not self.is_folder_locked(folder_name):
                filtered_results.append(r)
        return filtered_results

    def is_folder_locked(self, folder_name: str) -> bool:
        for f in self._folders:
            if f.name == folder_name:
                return f.is_locked
        return False

    def lock_folder(self, folder_name: str, password: str) -> bool:
        import hashlib
        if folder_name not in self.get_folders(): return False
        pwd_hash = hashlib.sha256(folder_name.encode() + password.encode()).hexdigest()
        if self.storage.set_folder_lock(folder_name, True, pwd_hash):
            self._folders = self.storage.get_folders()
            return True
        return False

    def unlock_folder(self, folder_name, password: str) -> bool:
        import hashlib
        target_f = next((f for f in self._folders if f.name == folder_name), None)
        if not target_f or not target_f.is_locked: return False
        pwd_hash = hashlib.sha256(folder_name.encode() + password.encode()).hexdigest()
        if pwd_hash == target_f.password_hash:
            if self.storage.set_folder_lock(folder_name, False):
                self._folders = self.storage.get_folders()
                return True
        return False

    def lock_note(self, obj_name: str, password: str) -> bool:
        import hashlib
        note = self.get_note_by_id(obj_name)
        if not note: return False
        pwd_hash = hashlib.sha256(obj_name.encode() + password.encode()).hexdigest()
        note.is_locked = True
        note.password_hash = pwd_hash
        self.storage.upsert_note_metadata(note)
        self._notes = self.storage.get_all_notes()
        return True

    def unlock_note(self, obj_name: str, password: str) -> bool:
        import hashlib
        note = self.get_note_by_id(obj_name)
        if not note or not note.is_locked: return False
        pwd_hash = hashlib.sha256(obj_name.encode() + password.encode()).hexdigest()
        if pwd_hash == note.password_hash:
            note.is_locked = False
            self.storage.upsert_note_metadata(note)
            self._notes = self.storage.get_all_notes()
            return True
        return False

    def delete_notes_in_folder(self, folder_name: str) -> List[str]:
        """Bulk deletes all notes in a folder and returns their obj_names."""
        notes_to_delete = [n for n in self._notes if n.folder == folder_name]
        obj_names = [n.obj_name for n in notes_to_delete]
        for obj_name in obj_names:
            self.storage.delete_note(obj_name)
        self._notes = self.storage.get_all_notes()
        return obj_names
