import logging
from src.infrastructure.storage import StorageManager

class BrowserService:
    """
    Service layer for managing Browser session logic.
    Decoupled from PyQt UI components.
    """
    def __init__(self, storage_manager=None):
        self.storage = storage_manager or StorageManager()
        self._browsers = [] # Internal list of browser session dicts
        self._is_loaded = False # Integrity guard

    def load_browsers(self):
        """Loads browser state from SQLite via StorageManager."""
        self._browsers = self.storage.get_all_browsers()
        self._is_loaded = True
        return self._browsers

    def get_browsers(self):
        return self._browsers

    def add_browser(self, url="https://google.com"):
        """Adds a new browser session entity."""
        # Find max ID for unique naming
        max_id = 0
        for b in self._browsers:
            obj_name = b.get("obj_name", "")
            if obj_name.startswith("BrowserDock_"):
                try:
                    bid = int(obj_name.split("_")[1])
                    if bid > max_id: max_id = bid
                except (ValueError, IndexError):
                    pass
        
        new_id = max_id + 1
        browser = {
            "obj_name": f"BrowserDock_{new_id}",
            "title": "Mini Browser",
            "url": url
        }
        self._browsers.append(browser)
        self.save_to_disk()
        return browser

    def delete_browser(self, obj_name):
        """Deletes a browser session by its object name."""
        for i, browser in enumerate(self._browsers):
            if browser.get("obj_name") == obj_name:
                self._browsers.pop(i)
                self.save_to_disk()
                return True
        return False

    def sync_to_storage(self, current_browser_data):
        """
        Replaces current browser list with UI state and saves to SQLite.
        Atomic per-sync.
        """
        if not self._is_loaded:
             return False
             
        # Plan v8.1 fix: Clear and repopulate
        self.storage.delete_all_browsers()
        for browser in current_browser_data:
            self.storage.upsert_browser_metadata(browser)
            
        self._browsers = current_browser_data
        return True

    def save_to_disk(self):
        """Legacy compatibility hook. sync_to_storage handles immediate persistence."""
        pass
