import json
import os
import copy
import logging
import threading
import hashlib
import shutil
from PyQt6.QtCore import QStandardPaths, QObject, QTimer, pyqtSlot

class StorageManager(QObject):
    """
    Manages application data persistence using JSON files.
    Optimized with background saving, dirty checking, and batch throttling.
    """
    
    def __init__(self, filename="data.json"):
        super().__init__()
        base_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.file_path = os.path.join(base_path, filename)
        
        # New: Notes directory for distributed storage
        self.notes_dir = os.path.join(base_path, "notes")
        if not os.path.exists(self.notes_dir):
            os.makedirs(self.notes_dir)
            
        logging.info(f"StorageManager initialized. Data path: {self.file_path}")
        logging.info(f"Notes directory: {self.notes_dir}")
        self._last_save_hash = None
        self._save_lock = threading.Lock()
        self._data = None # Shared in-memory cache
        self._throttle_timer = None

    def _get_throttle_timer(self):
        """Lazy initialization of the timer to prevent startup crashes."""
        if self._throttle_timer is None:
            self._throttle_timer = QTimer(self)
            self._throttle_timer.setSingleShot(True)
            self._throttle_timer.setInterval(2000) # Increased to 2s
            self._throttle_timer.timeout.connect(self._on_throttle_timeout)
        return self._throttle_timer

    def _calculate_hash(self, data):
        """Calculates a simple MD5 hash of the data to detect changes."""
        try:
            json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
            return hashlib.md5(json_str.encode('utf-8')).hexdigest()
        except Exception:
            return None

    def save_data(self, data, async_save=True):
        """
        Saves data to JSON with throttling.
        Immediate in-memory update, delayed disk write.
        """
        self._data = data # Immediate consistency
        
        # Dirty Check
        current_hash = self._calculate_hash(data)
        if current_hash and current_hash == self._last_save_hash:
            return True
        
        if not async_save:
            self._get_throttle_timer().stop()
            payload = copy.deepcopy(data)
            return self._perform_save(payload)
            
        # Restart throttle timer (batching)
        self._get_throttle_timer().start()
        return True

    def flush(self):
        """Forces an immediate save of whatever is in the cache."""
        if self._data is not None:
            self._get_throttle_timer().stop()
            with self._save_lock:
                payload = copy.deepcopy(self._data)
            self._perform_save(payload)

    @pyqtSlot()
    def _on_throttle_timeout(self):
        """Triggered after the quiet period. Performs background write."""
        if self._data is not None:
            with self._save_lock:
                current_hash = self._calculate_hash(self._data)
                if current_hash != self._last_save_hash:
                    try:
                        payload = copy.deepcopy(self._data)
                    except Exception as e:
                        logging.error(f"StorageManager Copy Error: {e}")
                        return
                else:
                    return
            thread = threading.Thread(target=self._perform_save, args=(payload, current_hash), daemon=True)
            thread.start()

    def _perform_save(self, data, precomputed_hash=None):
        """Actual disk I/O operation."""
        try:
            current_hash = precomputed_hash or self._calculate_hash(data)
            
            with self._save_lock:
                temp_path = self.file_path + ".tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is flushed to disk before rename
                
                # Robust Atomic Replace with Retry
                # On Windows, use shutil.copy2 as fallback to avoid PermissionError
                import time
                for i in range(5):
                    try:
                        if os.path.exists(self.file_path):
                            try:
                                os.replace(temp_path, self.file_path)
                            except PermissionError:
                                # Fallback for Windows file lock: copy then delete temp
                                shutil.copy2(temp_path, self.file_path)
                                try:
                                    os.remove(temp_path)
                                except Exception:
                                    pass
                        else:
                            os.rename(temp_path, self.file_path)
                        break # Success
                    except (PermissionError, OSError) as e:
                        if i == 4: raise # Final attempt failed
                        time.sleep(0.1 * (i + 1)) # Exponential backoff
                
                self._last_save_hash = current_hash
                logging.debug(f"StorageManager: Atomic batched save complete.")
                return True
        except Exception as e:
            logging.error(f"StorageManager Save Error: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass
            return False
            
    def load_data(self):
        """
        Loads data from JSON file into shared cache.
        Robust to Windows file locks with retries.
        Auto-recovers from corrupt JSON by backing up and starting fresh.
        """
        if self._data is not None:
             return self._data
             
        if not os.path.exists(self.file_path):
            self._data = {}
            return self._data
            
        import time
        # Retry logic for reading (Windows handles locks poorly)
        for i in range(3):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        self._data = {}
                    else:
                        self._data = json.loads(content)
                    
                    self._last_save_hash = self._calculate_hash(self._data)
                    return self._data
            except (PermissionError, OSError) as e:
                logging.warning(f"StorageManager Load Retry {i+1}: {e}")
                if i == 2: break
                time.sleep(0.05 * (i + 1))
            except json.JSONDecodeError as e:
                logging.error(f"StorageManager JSON Corrupt: {e}")
                # AUTO-RECOVER: Backup the corrupt file and start fresh.
                # This prevents a one-time write corruption from permanently breaking the app.
                try:
                    corrupt_backup = self.file_path + ".corrupt"
                    shutil.copy2(self.file_path, corrupt_backup)
                    logging.warning(f"StorageManager: Corrupt data.json backed up to {corrupt_backup}. Starting fresh.")
                except Exception as backup_err:
                    logging.error(f"StorageManager: Could not backup corrupt file: {backup_err}")
                self._data = {}
                return self._data
            except Exception as e:
                logging.error(f"StorageManager Load Error: {e}", exc_info=True)
                return None
                
        return None # Indicate persistent failure

    # --- Distributed Storage Methods ---
    
    def get_note_path(self, obj_name):
        """Returns the absolute path for a specific note slug/id."""
        return os.path.join(self.notes_dir, f"{obj_name}.html")

    def save_note_content(self, obj_name, content):
        """
        Atomically saves a note's HTML content.
        Pattern: write .tmp → fsync → rename old → .bak → rename .tmp → target.
        If power is cut between steps, .bak always holds the last good version.
        """
        path = self.get_note_path(obj_name)
        tmp_path = path + ".tmp"
        bak_path = path + ".bak"
        try:
            # Step 1: Write to temp file and flush to OS buffer
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            # Step 2: Back up current file (last good version)
            if os.path.exists(path):
                try:
                    os.replace(bak_path, bak_path + '.old') if os.path.exists(bak_path) else None
                    os.replace(path, bak_path)
                except Exception as bak_err:
                    logging.warning(f"StorageManager: Could not create .bak for {obj_name}: {bak_err}")

            # Step 3: Atomically replace target with new content
            try:
                os.replace(tmp_path, path)  # Atomic on same filesystem
            except OSError:
                # Cross-device fallback (e.g. symlinked to another drive)
                import shutil
                shutil.move(tmp_path, path)

            logging.debug(f"StorageManager: Atomic save OK → {path}")
            return True
        except Exception as e:
            logging.error(f"StorageManager: Error saving note {obj_name}: {e}")
            # Cleanup orphan temp file
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            return False

    def load_note_content(self, obj_name):
        """
        Loads a note's HTML content from disk.
        - Unicode hardened: errors='replace' + null byte strip.
        - Crash recovery journal: if target is missing/empty but .bak exists,
          auto-restores from .bak (covers power cut mid-save).
        - Also detects leftover .tmp files from previous crash for logging.
        """
        path = self.get_note_path(obj_name)
        bak_path = path + ".bak"
        tmp_path = path + ".tmp"

        # Crash journal: alert if a .tmp file is leftover from a crash
        if os.path.exists(tmp_path):
            logging.warning(f"StorageManager: Found orphan .tmp for {obj_name} — previous session may have crashed during save.")

        # Determine which file to actually read
        use_bak = False
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            if os.path.exists(bak_path) and os.path.getsize(bak_path) > 0:
                logging.warning(f"StorageManager: Main file missing/empty for {obj_name}. Auto-restoring from .bak.")
                use_bak = True
            elif not os.path.exists(path):
                logging.warning(f"StorageManager: Note file not found: {path}")
                return ""

        read_path = bak_path if use_bak else path
        try:
            with open(read_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            # Strip null bytes — common artifact of corrupted/partial writes
            content = content.replace('\x00', '')
            if use_bak:
                # Commit backup as the canonical file so future saves are consistent
                try:
                    import shutil
                    shutil.copy2(bak_path, path)
                except Exception:
                    pass
            return content
        except Exception as e:
            logging.error(f"StorageManager: Error loading note {obj_name}: {e}")
            return ""

    def delete_note_content(self, obj_name):
        """Deletes the physical file associated with a note."""
        path = self.get_note_path(obj_name)
        if os.path.exists(path):
            try:
                os.remove(path)
                logging.info(f"StorageManager: Deleted note file {path}")
                return True
            except Exception as e:
                logging.error(f"StorageManager: Error deleting note file {obj_name}: {e}")
        return False
