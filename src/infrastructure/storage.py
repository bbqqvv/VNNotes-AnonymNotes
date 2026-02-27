import os
import logging
from PyQt6.QtCore import QObject
from src.infrastructure.database import DatabaseManager
from src.domain.interfaces import IStorage
from src.domain.models import Note, Folder
from PyQt6 import sip
from abc import ABCMeta

class StorageMeta(sip.wrappertype, ABCMeta):
    """Unified metaclass for QObject and ABCMeta compatibility."""
    pass

class StorageManager(QObject, IStorage, metaclass=StorageMeta):
    """
    Concrete implementation of IStorage using SQLite.
    Inherits from QObject for signal/slot capabilities.
    """
    def __init__(self):
        super().__init__()
        
        # Auto-Migrate legacy JSON users to SQLite FTS5 silently on startup
        try:
            import sys
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
            import migrate_to_sqlite
            migrate_to_sqlite.migrate()
        except ImportError:
            pass # Script not found, assuming fresh install or already migrated
        except Exception as e:
            logging.error(f"StorageManager: Legacy Migration Hook Failed: {e}")
            
        self.db = DatabaseManager()
        logging.info("StorageManager initialized with SQLite Database Backend.")

    def get_all_notes(self, only_open=False, include_placeholders=False):
        """Fetches notes metadata from the database as a list of Note objects."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            sql = """
            SELECT 
                n.id, n.obj_name, n.title, n.folder_id, n.pinned, 
                n.is_open, n.is_locked, n.is_placeholder, n.password_hash, 
                n.created_at, n.updated_at,
                f.name as folder 
            FROM notes n
            LEFT JOIN folders f ON f.id = n.folder_id
            """
            conditions = []
            if only_open:
                conditions.append("n.is_open = 1")
            if not include_placeholders:
                conditions.append("n.is_placeholder = 0")
            
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            sql += " ORDER BY n.pinned DESC, n.updated_at DESC"
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [Note.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logging.error(f"StorageManager.get_all_notes Error: {e}")
            return []

    def get_note_by_obj_name(self, obj_name):
        """Fetches a single note by object name."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    n.id, n.obj_name, n.title, n.folder_id, n.pinned, 
                    n.is_open, n.is_locked, n.is_placeholder, n.password_hash, 
                    n.created_at, n.updated_at,
                    f.name as folder 
                FROM notes n
                LEFT JOIN folders f ON f.id = n.folder_id
                WHERE n.obj_name = ?
            """, (obj_name,))
            row = cursor.fetchone()
            return Note.from_dict(dict(row)) if row else None
        except Exception as e:
            logging.error(f"StorageManager.get_note_by_obj_name Error: {e}")
            return None

    def upsert_note_metadata(self, note: Note):
        """Inserts or updates note metadata using a Note model."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN;")
            
            # Resolve Folder ID
            folder_name = note.folder or "General"
            cursor.execute("INSERT OR IGNORE INTO folders (name) VALUES (?)", (folder_name,))
            cursor.execute("SELECT id FROM folders WHERE name = ?", (folder_name,))
            folder_id = cursor.fetchone()[0]

            # Check if exists
            cursor.execute("SELECT id FROM notes WHERE obj_name = ?", (note.obj_name,))
            existing = cursor.fetchone()

            if existing: # Update
                cursor.execute("""
                    UPDATE notes 
                    SET title = ?, folder_id = ?, pinned = ?, is_open = ?, is_locked = ?, is_placeholder = ?, password_hash = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE obj_name = ?
                """, (note.title, folder_id, 1 if note.pinned else 0, 1 if note.is_open else 0, 
                      1 if note.is_locked else 0, 1 if note.is_placeholder else 0, note.password_hash, note.obj_name))
            else: # Insert
                cursor.execute("""
                    INSERT INTO notes (obj_name, title, folder_id, pinned, is_open, is_locked, is_placeholder, password_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (note.obj_name, note.title, folder_id, 1 if note.pinned else 0, 1 if note.is_open else 0, 
                      1 if note.is_locked else 0, 1 if note.is_placeholder else 0, note.password_hash))
            
            cursor.execute("COMMIT;")
            return True
        except Exception as e:
            conn.execute("ROLLBACK;")
            logging.error(f"StorageManager.upsert_note_metadata Error: {e}")
            return False

    def get_app_setting(self, key, default_value=None):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default_value
        except Exception as e:
            logging.error(f"StorageManager.get_app_setting Error: {e}")
            return default_value

    def set_app_setting(self, key, value):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1 FROM app_settings WHERE key = ?", (key,))
            if cursor.fetchone():
                cursor.execute("UPDATE app_settings SET value = ? WHERE key = ?", (value, key))
            else:
                cursor.execute("INSERT INTO app_settings (key, value) VALUES (?, ?)", (key, value))
            return True
        except Exception as e:
            logging.error(f"StorageManager.set_app_setting Error: {e}")
            return False

    def delete_note(self, obj_name):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM notes WHERE obj_name = ?", (obj_name,))
            return True
        except Exception as e:
            logging.error(f"StorageManager.delete_note Error: {e}")
            return False

    def save_note_content(self, obj_name, content):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN;")
            cursor.execute("SELECT id FROM notes WHERE obj_name = ?", (obj_name,))
            note_row = cursor.fetchone()
            if not note_row:
                cursor.execute("ROLLBACK;")
                return False
            note_id = note_row[0]

            cursor.execute("SELECT 1 FROM notes_content WHERE note_id = ?", (note_id,))
            if cursor.fetchone():
                cursor.execute("UPDATE notes_content SET content = ? WHERE note_id = ?", (content, note_id))
            else:
                cursor.execute("INSERT INTO notes_content (note_id, content) VALUES (?, ?)", (note_id, content))
                
            cursor.execute("UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (note_id,))
            cursor.execute("COMMIT;")
            return True
        except Exception as e:
            conn.execute("ROLLBACK;")
            logging.error(f"StorageManager.save_note_content Error: {e}")
            return False

    def load_note_content(self, obj_name):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT c.content FROM notes_content c JOIN notes n ON n.id = c.note_id WHERE n.obj_name = ?
            """, (obj_name,))
            row = cursor.fetchone()
            return row['content'] if row and row['content'] else ""
        except Exception as e:
            logging.error(f"StorageManager.load_note_content Error: {e}")
            return ""

    def get_folders(self):
        """Retrieves all folders as Folder objects."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM folders ORDER BY name ASC")
            rows = cursor.fetchall()
            return [Folder.from_dict(dict(row)) for row in rows]
        except Exception as e:
            logging.error(f"StorageManager.get_folders Error: {e}")
            return []

    def rename_folder(self, old_name, new_name):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE folders SET name = ? WHERE name = ?", (new_name, old_name))
            return True
        except Exception as e:
            logging.error(f"StorageManager.rename_folder Error: {e}")
            return False

    def set_folder_lock(self, name, is_locked, password_hash=None):
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE folders SET is_locked = ?, password_hash = ? WHERE name = ?
            """, (1 if is_locked else 0, password_hash, name))
            return True
        except Exception as e:
            logging.error(f"StorageManager.set_folder_lock Error: {e}")
            return False

    def search_notes_fts(self, query):
        """FTS5 search, return data formatted for UI integration."""
        query = query.strip()
        if not query: return []
        conn = self.db.get_connection()
        cursor = conn.cursor()
        import string
        words = query.translate(str.maketrans('', '', string.punctuation)).split()
        if not words: return []
        fts_query = " AND ".join(f'"{word}"*' for word in words if word)
        
        try:
            sql = """
            SELECT 
                fts.rowid, n.obj_name, n.title, f.name as folder, n.pinned,
                snippet(notes_fts, 1, '<mark>', '</mark>', '...', 15) as content_snippet
            FROM notes_fts fts
            JOIN notes n ON n.id = fts.rowid
            JOIN folders f ON f.id = n.folder_id
            WHERE notes_fts MATCH ?
            ORDER BY rank LIMIT 50;
            """
            cursor.execute(sql, (fts_query,))
            rows = cursor.fetchall()
            
            matches = []
            for row in rows:
                note_data = {
                    "obj_name": row["obj_name"],
                    "title": row["title"],
                    "folder": row["folder"],
                    "pinned": bool(row["pinned"])
                }
                note_matches = []
                if query.lower() in row["title"].lower():
                    note_matches.append({"type": "title", "text": row["title"]})
                if row["content_snippet"]:
                    import re
                    clean_snippet = re.sub(r'<(?!/?mark>)[^>]+>', '', row["content_snippet"])
                    note_matches.append({"type": "content", "line": 0, "text": clean_snippet})
                
                if note_matches:
                    matches.append({"note": note_data, "matches": note_matches})
            return matches
        except Exception as e:
            logging.error(f"StorageManager FTS5 Search Error: {e}")
            return []

    def save_to_disk(self):
        """No-op for SQLite implementation as changes are persisted per-operation."""
        pass

    def flush(self):
        """Satisfy SessionManager's call to flush. Same as save_to_disk for SQLite."""
        self.save_to_disk()

    # â”€â”€ Non-Interface Helper Methods â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def set_all_notes_closed(self):
        conn = self.db.get_connection()
        try:
            conn.execute("UPDATE notes SET is_open = 0")
            return True
        except Exception as e:
            logging.error(f"StorageManager.set_all_notes_closed Error: {e}")
            return False

    def update_note_links(self, source_obj_name, target_obj_names):
        conn = self.db.get_connection()
        try:
            conn.execute("BEGIN;")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM notes WHERE obj_name = ?", (source_obj_name,))
            source_row = cursor.fetchone()
            if not source_row:
                conn.execute("ROLLBACK;")
                return False
            source_id = source_row[0]
            conn.execute("DELETE FROM note_links WHERE source_id = ?", (source_id,))
            for t_obj_name in target_obj_names:
                cursor.execute("SELECT id FROM notes WHERE obj_name = ?", (t_obj_name,))
                target_row = cursor.fetchone()
                if target_row:
                    conn.execute("INSERT OR IGNORE INTO note_links (source_id, target_id) VALUES (?, ?)", (source_id, target_row[0]))
            conn.execute("COMMIT;")
            return True
        except Exception as e:
            conn.execute("ROLLBACK;")
            logging.error(f"StorageManager.update_note_links Error: {e}")
            return False

    def get_all_browsers(self) -> List[Dict[str, Any]]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT obj_name, title, url FROM browsers ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"StorageManager.get_all_browsers Error: {e}")
            return []

    def delete_all_browsers(self) -> bool:
        conn = self.db.get_connection()
        try:
            conn.execute("DELETE FROM browsers")
            return True
        except Exception as e:
            logging.error(f"StorageManager.delete_all_browsers Error: {e}")
            return False

    def upsert_browser_metadata(self, browser: Dict[str, Any]) -> bool:
        conn = self.db.get_connection()
        try:
            conn.execute("""
                INSERT INTO browsers (obj_name, title, url, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(obj_name) DO UPDATE SET
                    title = excluded.title,
                    url = excluded.url,
                    updated_at = CURRENT_TIMESTAMP
            """, (browser["obj_name"], browser["title"], browser["url"]))
            return True
        except Exception as e:
            logging.error(f"StorageManager.upsert_browser_metadata Error: {e}")
            return False
