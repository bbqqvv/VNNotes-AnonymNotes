from src.domain.services.note_service import NoteService
from src.domain.services.browser_service import BrowserService
from src.core.config import ConfigManager
from src.infrastructure.storage import StorageManager

class ServiceContext:
    """
    Central hub for all application services (Service Locator pattern).
    This ensures that any component can access services without tight coupling
    to MainWindow.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceContext, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        # Core Infrastructure
        self.config = ConfigManager()
        self.storage = StorageManager()
        
        # Business Services
        self.notes = NoteService(self.storage)
        self.browser = BrowserService(self.storage)
        
        # Future SaaS Services
        # self.auth = AuthService()
        # self.sync = SyncService()
        
        self._initialized = True

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls()
        return cls._instance
