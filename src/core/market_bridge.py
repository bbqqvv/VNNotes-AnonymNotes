from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
import logging
import json

logger = logging.getLogger(__name__)

class MarketBridge(QObject):
    """
    Bridge class for QWebChannel to allow JavaScript in the Marketplace 
    to interact with the VNNotes desktop application.
    """
    installation_status = pyqtSignal(str, bool, str) # plugin_id, success, message

    def __init__(self, plugin_manager, main_window):
        super().__init__()
        self.plugin_manager = plugin_manager
        self.main_window = main_window

    @pyqtSlot(str, str)
    def install_plugin(self, plugin_id, download_url):
        """Called from JS to install a plugin."""
        logger.info(f"MarketBridge: Request to install plugin {plugin_id} from {download_url}")
        
        # Show a status message in the app
        self.main_window.statusBar().showMessage(f"Installing {plugin_id}...", 5000)
        
        # Perform installation
        success, message = self.plugin_manager.install_plugin_from_url(download_url)
        
        if success:
            logger.info(f"MarketBridge: Successfully installed {plugin_id}")
            self.main_window.statusBar().showMessage(f"Successfully installed {plugin_id}!", 3000)
        else:
            logger.error(f"MarketBridge: Failed to install {plugin_id}: {message}")
            self.main_window.statusBar().showMessage(f"Failed to install {plugin_id}: {message}", 5000)
            
        # Notify JS of status
        self.installation_status.emit(plugin_id, success, message)

    @pyqtSlot(result=str)
    def get_installed_plugins(self):
        """Returns a JSON list of installed plugin IDs."""
        return json.dumps(list(self.plugin_manager.plugins.keys()))
        
    @pyqtSlot(str)
    def uninstall_plugin(self, plugin_id):
        """Called from JS to uninstall a plugin."""
        logger.info(f"MarketBridge: Request to uninstall plugin {plugin_id}")
        success, message = self.plugin_manager.uninstall_plugin(plugin_id)
        if success:
            logger.info(f"MarketBridge: Successfully uninstalled {plugin_id}")
            self.main_window.statusBar().showMessage(f"Successfully uninstalled {plugin_id}!", 3000)
            self.installation_status.emit(plugin_id, False, "Uninstalled") # False used as 'removed' flag
        else:
            logger.error(f"MarketBridge: Failed to uninstall {plugin_id}: {message}")
            self.main_window.statusBar().showMessage(f"Failed to uninstall {plugin_id}: {message}", 5000)
