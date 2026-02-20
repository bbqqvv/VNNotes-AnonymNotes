import os
from PyQt6.QtCore import QSettings

class ConfigManager:
    """
    Manages application configuration using QSettings (INI format).
    """
    
    def __init__(self, app_name="VNNotes"):
        self.settings = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "vtechdigitalsolution", app_name)
    
    def get_value(self, key, default=None):
        return self.settings.value(key, default)
    
    def set_value(self, key, value):
        self.settings.setValue(key, value)
        
    def get_window_geometry(self):
        return self.settings.value("window/geometry")
        
    def set_window_geometry(self, geometry):
        self.settings.setValue("window/geometry", geometry)
        
    def get_window_state(self):
        return self.settings.value("window/state")
        
    def set_window_state(self, state):
        self.settings.setValue("window/state", state)
