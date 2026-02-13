import json
import os
import logging
from PyQt6.QtCore import QStandardPaths

class StorageManager:
    """
    Manages application data persistence using JSON files.
    Use this for large data structures like Notes content.
    """
    
    def __init__(self, filename="data.json"):
        # Get AppData location
        # e.g., C:/Users/User/AppData/Local/VTechStudio/StealthAssist/
        base_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        
        # Ensure directory exists
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            
        self.file_path = os.path.join(base_path, filename)
        
    def save_data(self, data):
        """
        Saves data dictionary to JSON file.
        """
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"StorageManager Save Error: {e}", exc_info=True)
            return False
            
    def load_data(self):
        """
        Loads data from JSON file. Returns empty dict if file doesn't exist or error.
        """
        if not os.path.exists(self.file_path):
            return {}
            
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"StorageManager Load Error: {e}", exc_info=True)
            return {}
