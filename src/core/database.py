import sqlite3
import os
import logging
from PyQt6.QtCore import QStandardPaths

class DatabaseManager:
    """
    Core SQLite Database Engine for VNNotes.
    Handles connections, schema migrations, and FTS5 initialization.
    """
    def __init__(self, filename="vnnotes.db"):
        from typing import Optional
        base_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if not os.path.exists(base_path):
            os.makedirs(base_path, exist_ok=True)
        self.db_path = os.path.join(base_path, filename)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def get_connection(self):
        """Returns a thread-local database connection."""
        # SQLite objects created in a thread can only be used in that same thread.
        # Since GUI tasks and background saves might operate across threads,
        # we generate a new connection per call, or use check_same_thread=False
        # For simplicity and thread-safety with WAL mode, we'll open a fresh connection
        # per transaction block and close it, or use a robust pattern.
        # For optimum performance in desktop apps, sharing a connection with check_same_thread=False 
        # is permissible provided we use exclusive locks or WAL.
        if self.conn is None:
            conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                isolation_level=None # Autocommit mode, we manage explicit BEGIN/COMMIT
            )
            conn.row_factory = sqlite3.Row # Dictionary-like cursor results
            
            # Performance Pragmas
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA cache_size=-64000;") # 64MB cache
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA temp_store=MEMORY;")
            conn.execute("PRAGMA busy_timeout=5000;") # Wait 5s if locked
            self.conn = conn
            
        assert self.conn is not None
        return self.conn

    def _init_db(self):
        """Initializes tables and indexes if they do not exist."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Start Transaction
            cursor.execute("BEGIN;")

            # 1. Application Settings (Key-Value Key/JSON)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

            # 2. Notes Metadata Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obj_name TEXT UNIQUE NOT NULL,
                title TEXT,
                folder TEXT DEFAULT 'General',
                pinned INTEGER DEFAULT 0,
                is_open INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Migration: Add is_open if it doesn't exist (Plan v8.1)
            cursor.execute("PRAGMA table_info(notes);")
            columns = [col[1] for col in cursor.fetchall()]
            if "is_open" not in columns:
                logging.info("DatabaseManager: Migrating schema - adding 'is_open' to 'notes' table.")
                cursor.execute("ALTER TABLE notes ADD COLUMN is_open INTEGER DEFAULT 1;")

            # 3. Notes Content Table (BLOB/HTML)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes_content (
                note_id INTEGER PRIMARY KEY,
                content TEXT,
                FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
            );
            """)

            # 4. View to join Metadata and Content for FTS5 snippets
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_notes_content AS 
            SELECT c.note_id as rowid, n.title, c.content 
            FROM notes_content c 
            JOIN notes n ON n.id = c.note_id;
            """)

            # 5. Global Search Virtual Table (FTS5)
            # content='v_notes_content' allows FTS to mirror the View for snippet() perfectly
            # Plan v12.5: REMOVED DROP TABLE. We only create if not exists to avoid 12MB index rebuild on every boot.
            
            cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                title, 
                content,
                content='v_notes_content', 
                content_rowid='rowid',
                tokenize='unicode61'
            );
            """)
            
            # Repopulate the FTS5 index immediately from the View
            cursor.execute("INSERT INTO notes_fts(notes_fts) VALUES('rebuild');")

            # Triggers to keep FTS5 synchronized automatically!
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes_content BEGIN
              INSERT INTO notes_fts(rowid, title, content) 
              VALUES (new.note_id, (SELECT title FROM notes WHERE id = new.note_id), new.content);
            END;
            """)
            
            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes_content BEGIN
              INSERT INTO notes_fts(notes_fts, rowid, title, content) 
              VALUES ('delete', old.note_id, (SELECT title FROM notes WHERE id = old.note_id), old.content);
            END;
            """)

            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes_content BEGIN
              INSERT INTO notes_fts(notes_fts, rowid, title, content) 
              VALUES ('delete', old.note_id, (SELECT title FROM notes WHERE id = old.note_id), old.content);
              INSERT INTO notes_fts(rowid, title, content) 
              VALUES (new.note_id, (SELECT title FROM notes WHERE id = new.note_id), new.content);
            END;
            """)

            cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS notes_title_au AFTER UPDATE OF title ON notes BEGIN
              INSERT INTO notes_fts(notes_fts, rowid, title, content) 
              VALUES ('delete', old.id, old.title, (SELECT content FROM notes_content WHERE note_id = old.id));
              INSERT INTO notes_fts(rowid, title, content) 
              VALUES (new.id, new.title, (SELECT content FROM notes_content WHERE note_id = new.id));
            END;
            """)

            # 6. Browser Sessions Table (Plan v8.1 fix)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS browsers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                obj_name TEXT UNIQUE NOT NULL,
                title TEXT,
                url TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cursor.execute("COMMIT;")
            logging.info(f"DatabaseManager: Initialized schema at {self.db_path} successfully.")

        except Exception as e:
            if self.conn:
                self.conn.execute("ROLLBACK;")
            logging.error(f"DatabaseManager: Schema Intialization Error: {e}")
            raise

    def close(self):
        """Closes the connection cleanly."""
        current_conn = self.conn
        if current_conn is not None:
            current_conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            current_conn.close()
            self.conn = None
