from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Note:
    """Type-safe model for a Note entity."""
    obj_name: str
    title: str
    folder: str = "General"
    pinned: bool = False
    is_open: bool = True
    is_locked: bool = False
    is_placeholder: bool = False
    password_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    content: Optional[str] = None

    def __getitem__(self, key):
        """Backward compatibility for dictionary-style access."""
        return getattr(self, key)

    def get(self, key, default=None):
        """Backward compatibility for dictionary-style get."""
        val = getattr(self, key, default)
        return val if val is not None else default

    @classmethod
    def from_dict(cls, data: dict):
        """Factory method to create a Note instance from a dictionary."""
        if not data: return None
        return cls(
            obj_name=data.get("obj_name"),
            title=data.get("title"),
            folder=data.get("folder", "General"),
            pinned=bool(data.get("pinned", 0)),
            is_open=bool(data.get("is_open", 1)),
            is_locked=bool(data.get("is_locked", 0)),
            is_placeholder=bool(data.get("is_placeholder", 0)),
            password_hash=data.get("password_hash"),
            content=data.get("content")
        )

    def to_dict(self):
        """Converts model back to dictionary for legacy compatibility or storage."""
        return {
            "obj_name": self.obj_name,
            "title": self.title,
            "folder": self.folder,
            "pinned": 1 if self.pinned else 0,
            "is_open": 1 if self.is_open else 0,
            "is_locked": 1 if self.is_locked else 0,
            "is_placeholder": 1 if self.is_placeholder else 0,
            "password_hash": self.password_hash
        }

@dataclass
class Folder:
    """Type-safe model for a Folder entity."""
    name: str
    is_locked: bool = False
    password_hash: Optional[str] = None

    def __getitem__(self, key):
        return getattr(self, key)

    def get(self, key, default=None):
        val = getattr(self, key, default)
        return val if val is not None else default

    @classmethod
    def from_dict(cls, data: dict):
        if not data: return None
        return cls(
            name=data.get("name"),
            is_locked=bool(data.get("is_locked", 0)),
            password_hash=data.get("password_hash")
        )
