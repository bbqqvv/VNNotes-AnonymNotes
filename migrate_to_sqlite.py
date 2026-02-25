import os
import sys
import json
import logging
import sqlite3
import shutil
from PyQt6.QtCore import QStandardPaths, QCoreApplication

def migrate():
    """Migrates data.json to vnnotes.db for existing users."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    from PyQt6.QtCore import QCoreApplication
    if not QCoreApplication.instance():
        app = QCoreApplication(sys.argv)
    base_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    json_path = os.path.join(base_path, "data.json")
    db_path = os.path.join(base_path, "vnnotes.db")
    notes_dir = os.path.join(base_path, "notes")

    if not os.path.exists(json_path):
        logging.info("No data.json found. No migration needed.")
        return

    if os.path.exists(db_path):
        logging.warning("vnnotes.db already exists. Ensure you aren't overwriting newer data.")
        # We proceed anyway, upserting data to be safe.

    logging.info(f"Starting Migration from JSON to SQLite FTS5 for {json_path}")
    
    # 1. Initialize SQLite
    from src.core.database import DatabaseManager
    # Initialize schema
    db = DatabaseManager(filename="vnnotes.db")
    conn = db.get_connection()

    # 2. Read JSON
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Failed to read data.json: {e}")
        return

    notes = data.get("notes", [])
    logging.info(f"Found {len(notes)} notes in data.json to migrate.")

    conn.execute("BEGIN;")
    try:
        cursor = conn.cursor()
        
        for note in notes:
            obj_name = note.get("obj_name")
            title = note.get("title", "Untitled")
            folder = note.get("folder", "General")
            pinned = note.get("pinned", 0)
            
            # Upsert Metadata
            cursor.execute("SELECT id FROM notes WHERE obj_name = ?", (obj_name,))
            if cursor.fetchone():
                cursor.execute("UPDATE notes SET title=?, folder=?, pinned=? WHERE obj_name=?", (title, folder, pinned, obj_name))
            else:
                cursor.execute("INSERT INTO notes (obj_name, title, folder, pinned) VALUES (?, ?, ?, ?)", (obj_name, title, folder, pinned))
            
            # Migrate Content (File to DB)
            note_file = os.path.join(notes_dir, f"{obj_name}.html")
            content = ""
            if note.get("content"):
                 content = note["content"]
            elif os.path.exists(note_file):
                 with open(note_file, 'r', encoding='utf-8') as f:
                     content = f.read()
            
            if content:
                # get note_id
                cursor.execute("SELECT id FROM notes WHERE obj_name = ?", (obj_name,))
                note_id = cursor.fetchone()[0]
                
                cursor.execute("SELECT 1 FROM notes_content WHERE note_id = ?", (note_id,))
                if cursor.fetchone():
                    cursor.execute("UPDATE notes_content SET content=? WHERE note_id=?", (content, note_id))
                else:
                    cursor.execute("INSERT INTO notes_content (note_id, content) VALUES (?, ?)", (note_id, content))
        
        conn.execute("COMMIT;")
        logging.info("Migration successful. All Notes inserted into SQLite FTS5 Virtual Tables.")
        
        # 3. Rename JSON to prevent double-migration
        backup_path = json_path + ".migrated"
        shutil.move(json_path, backup_path)
        logging.info(f"Renamed data.json to {backup_path}")
        
    except Exception as e:
        conn.execute("ROLLBACK;")
        logging.error(f"Migration Failed, rolled back database. Error: {e}")

if __name__ == "__main__":
    migrate()
