import json
import os
import logging
import threading
import hashlib
from PyQt6.QtCore import QStandardPaths, QObject, QTimer, pyqtSlot

class StorageManager(QObject):
    """
    Manages application data persistence using JSON files.
    Optimized with background saving, dirty checking, and batch throttling.
    """
    
    def __init__(self, filename="data.json"):
        super().__init__()
        base_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            
        self.file_path = os.path.join(base_path, filename)
        logging.info(f"StorageManager initialized. Data path: {self.file_path}")
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
        except:
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
            # Deep copy on MAIN thread for safety
            payload = json.loads(json.dumps(data))
            return self._perform_save(payload)
            
        # Restart throttle timer (batching)
        self._get_throttle_timer().start()
        return True

    def flush(self):
        """Forces an immediate save of whatever is in the cache."""
        if self._data is not None:
            self._get_throttle_timer().stop()
            payload = json.loads(json.dumps(self._data))
            self._perform_save(payload)

    @pyqtSlot()
    def _on_throttle_timeout(self):
        """Triggered after the quiet period. Performs background write."""
        if self._data is not None:
            # Hash check again to be sure
            current_hash = self._calculate_hash(self._data)
            if current_hash != self._last_save_hash:
                # Deep copy on MAIN thread BEFORE starting thread
                try:
                    payload = json.loads(json.dumps(self._data))
                    thread = threading.Thread(target=self._perform_save, args=(payload,), daemon=True)
                    thread.start()
                except Exception as e:
                    logging.error(f"StorageManager Copy Error: {e}")

    def _perform_save(self, data):
        """Actual disk I/O operation."""
        try:
            current_hash = self._calculate_hash(data)
            
            with self._save_lock:
                temp_path = self.file_path + ".tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # Robust Atomic Replace with Retry (Windows handles locks poorly)
                import time
                for i in range(5):
                    try:
                        if os.path.exists(self.file_path):
                            os.replace(temp_path, self.file_path)
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
                # Corrupt file is a critical failure. 
                # We return None so the service doesn't overwrite it immediately.
                return None
            except Exception as e:
                logging.error(f"StorageManager Load Error: {e}", exc_info=True)
                return None
                
        return None # Indicate persistent failure


