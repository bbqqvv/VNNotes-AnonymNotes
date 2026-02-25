import os
import logging
from PyQt6.QtCore import QObject
from src.core.database import DatabaseManager

class StorageManager(QObject):
    """
    Data Access Object (DAO) for the SQLite database.
    Replaces the legacy JSON JSON file system.
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

    def get_all_notes(self, only_open=False):
        """Fetches notes metadata from the database as a list of dicts. Optional session filtering."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            sql = "SELECT * FROM notes"
            params = []
            if only_open:
                sql += " WHERE is_open = 1"
            
            sql += " ORDER BY pinned DESC, updated_at DESC"
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"StorageManager.get_all_notes Error: {e}")
            return []

    def get_note_by_obj_name(self, obj_name):
        """Fetches a single note metadata by object name."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM notes WHERE obj_name = ?", (obj_name,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logging.error(f"StorageManager.get_note_by_obj_name Error: {e}")
            return None

    def upsert_note_metadata(self, note_dict):
        """Inserts or updates note metadata in the DB."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            obj_name = note_dict.get("obj_name")
            title = note_dict.get("title", "")
            folder = note_dict.get("folder", "General")
            pinned = note_dict.get("pinned", 0)
            # Default to current value if not provided in dict, to prevent accidental closure
            is_open = note_dict.get("is_open", 1) 

            # Check if exists
            cursor.execute("SELECT id FROM notes WHERE obj_name = ?", (obj_name,))
            existing = cursor.fetchone()

            if existing: # Update
                cursor.execute("""
                    UPDATE notes 
                    SET title = ?, folder = ?, pinned = ?, is_open = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE obj_name = ?
                """, (title, folder, pinned, is_open, obj_name))
            else: # Insert
                cursor.execute("""
                    INSERT INTO notes (obj_name, title, folder, pinned, is_open)
                    VALUES (?, ?, ?, ?, ?)
                """, (obj_name, title, folder, pinned, is_open))
            
            return True
        except Exception as e:
            logging.error(f"StorageManager.upsert_note_metadata Error: {e}")
            return False

    def set_all_notes_closed(self):
        """Sets is_open=0 for all notes in the database. Used during session sync."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE notes SET is_open = 0")
            return True
        except Exception as e:
            logging.error(f"StorageManager.set_all_notes_closed Error: {e}")
            return False

    def set_note_open_status(self, obj_name, is_open):
        """Explicitly sets the session visibility of a single note."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE notes SET is_open = ? WHERE obj_name = ?", (1 if is_open else 0, obj_name))
            return True
        except Exception as e:
            logging.error(f"StorageManager.set_note_open_status Error: {e}")
            return False

    def delete_note(self, obj_name):
        """Deletes a note entirely (cascades to content via FK)."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM notes WHERE obj_name = ?", (obj_name,))
            return True
        except Exception as e:
            logging.error(f"StorageManager.delete_note Error: {e}")
            return False

    def save_note_content(self, obj_name, content):
        """Atomically saves a note's HTML content. The FTS5 trigger handles the search index."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try: # Use transaction around content upsert
            cursor.execute("BEGIN;")
            cursor.execute("SELECT id FROM notes WHERE obj_name = ?", (obj_name,))
            note_row = cursor.fetchone()
            if not note_row:
                cursor.execute("ROLLBACK;")
                logging.warning(f"Attempted to save content for nonexistent metadata obj_name: {obj_name}")
                return False
            note_id = note_row[0]

            # Check existing content
            cursor.execute("SELECT 1 FROM notes_content WHERE note_id = ?", (note_id,))
            exists = cursor.fetchone()

            if exists:
                cursor.execute("UPDATE notes_content SET content = ? WHERE note_id = ?", (content, note_id))
            else:
                cursor.execute("INSERT INTO notes_content (note_id, content) VALUES (?, ?)", (note_id, content))
                
            # Update the notes table updated_at
            cursor.execute("UPDATE notes SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (note_id,))
            cursor.execute("COMMIT;")
            return True
        except Exception as e:
            conn.execute("ROLLBACK;")
            logging.error(f"StorageManager.save_note_content Error: {e}")
            return False

    def load_note_content(self, obj_name):
        """Loads a note's HTML content from DB."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT c.content 
                FROM notes_content c
                JOIN notes n ON n.id = c.note_id
                WHERE n.obj_name = ?
            """, (obj_name,))
            row = cursor.fetchone()
            if row and row['content']:
                return row['content']
            return ""
        except Exception as e:
            logging.error(f"StorageManager.load_note_content Error: {e}")
            return ""

    # ── Browser DAO (Plan v8.1) ───────────────────────────────────────

    def get_all_browsers(self):
        """Fetches all saved browser sessions."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM browsers ORDER BY updated_at ASC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"StorageManager.get_all_browsers Error: {e}")
            return []

    def upsert_browser_metadata(self, browser_dict):
        """Atomically saves or updates a browser session."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            obj_name = browser_dict.get("obj_name")
            title = browser_dict.get("title", "Mini Browser")
            url = browser_dict.get("url", "https://google.com")

            cursor.execute("SELECT id FROM browsers WHERE obj_name = ?", (obj_name,))
            existing = cursor.fetchone()

            if existing: # Update
                cursor.execute("""
                    UPDATE browsers 
                    SET title = ?, url = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE obj_name = ?
                """, (title, url, obj_name))
            else: # Insert
                cursor.execute("""
                    INSERT INTO browsers (obj_name, title, url)
                    VALUES (?, ?, ?)
                """, (obj_name, title, url))
            
            return True
        except Exception as e:
            logging.error(f"StorageManager.upsert_browser_metadata Error: {e}")
            return False

    def delete_all_browsers(self):
        """Wipes all browser sessions from DB. Used during UI sync."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM browsers")
            return True
        except Exception as e:
            logging.error(f"StorageManager.delete_all_browsers Error: {e}")
            return False

    def flush(self):
        """Legacy compatibility hook. SQLite persists immediately, so flush is a no-op."""
        pass
        
    def search_notes_fts(self, query):
        """
        Executes a blazing fast Full-Text Search via the SQLite FTS5 engine.
        Returns matching notes formatting identical to the previous NoteService format
        so the UI can remain completely oblivious to the database transition.
        """
        query = query.strip()
        if not query: return []
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # We want to support prefix matching so searching "logi" finds "login"
        # We split the query into words and append the * wildcard to each.
        import string
        words = query.translate(str.maketrans('', '', string.punctuation)).split()
        if not words: return []
        
        # Format for FTS5: each word prefix matched, e.g. "hello*" AND "world*"
        fts_query = " AND ".join(f'"{word}"*' for word in words if word)
        
        try:
            # The heart of the implementation: The FTS5 MATCH clause combined with snippet()
            # snippet(table, colIdx, preMatch, postMatch, overflow, maxTokens)
            sql = """
            SELECT 
                fts.rowid,
                n.obj_name,
                n.title,
                n.folder,
                n.pinned,
                snippet(notes_fts, 1, '<mark>', '</mark>', '...', 15) as content_snippet
            FROM notes_fts fts
            JOIN notes n ON n.id = fts.rowid
            WHERE notes_fts MATCH ?
            ORDER BY rank
            LIMIT 50;
            """
            cursor.execute(sql, (fts_query,))
            rows = cursor.fetchall()
            
            matches = []
            for row in rows:
                note = {
                    "obj_name": row["obj_name"],
                    "title": row["title"],
                    "folder": row["folder"],
                    "pinned": row["pinned"]
                }
                
                note_matches = []
                
                # Check if it hit the title
                if query.lower() in row["title"].lower():
                     note_matches.append({"type": "title", "text": row["title"]})
                     
                # Add snippet
                snippet = row["content_snippet"]
                if snippet:
                     # Remove HTML tags except our <mark> from snippet
                     import re
                     # First strip all tags except mark
                     # This is a basic strip, letting the UI handle the mark highlighting
                     clean_snippet = re.sub(r'<(?!/?mark>)[^>]+>', '', snippet)
                     note_matches.append({"type": "content", "line": 0, "text": clean_snippet})
                
                if note_matches:
                    matches.append({
                        "note": note,
                        "matches": note_matches
                    })
            
            return matches
        except Exception as e:
            logging.error(f"StorageManager FTS5 Search Error: {e}")
            return []

    def load_data(self):
        """Legacy compatibility hook."""
        return {"notes": self.get_all_notes()}
        
    def save_data(self, data, async_save=True):
        """Legacy compatibility hook for monolithic save. Ignored as everything goes via upsert_note_metadata."""
        return True
