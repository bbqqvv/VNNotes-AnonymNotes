from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .models import Note, Folder

class IStorage(ABC):
    """Abstract Base Class for all storage implementations."""

    @abstractmethod
    def get_all_notes(self, only_open: bool = False, include_placeholders: bool = False) -> List[Note]:
        pass

    @abstractmethod
    def get_note_by_obj_name(self, obj_name: str) -> Optional[Note]:
        pass

    @abstractmethod
    def upsert_note_metadata(self, note: Note) -> bool:
        pass

    @abstractmethod
    def save_note_content(self, obj_name: str, content: str) -> bool:
        pass

    @abstractmethod
    def load_note_content(self, obj_name: str) -> str:
        pass

    @abstractmethod
    def delete_note(self, obj_name: str) -> bool:
        pass

    @abstractmethod
    def get_folders(self) -> List[Folder]:
        pass

    @abstractmethod
    def rename_folder(self, old_name: str, new_name: str) -> bool:
        pass

    @abstractmethod
    def set_folder_lock(self, name: str, is_locked: bool, password_hash: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def get_app_setting(self, key: str, default_value: Any = None) -> Any:
        pass

    @abstractmethod
    def set_app_setting(self, key: str, value: Any) -> bool:
        pass
        
    @abstractmethod
    def search_notes_fts(self, query: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_all_browsers(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete_all_browsers(self) -> bool:
        pass

    @abstractmethod
    def upsert_browser_metadata(self, browser: Dict[str, Any]) -> bool:
        pass
