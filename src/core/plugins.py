import os
import sys
import json
import logging
import importlib
import importlib.util
import zipfile
import shutil
import requests
import tempfile
from typing import Dict, List, Any, Type, Tuple, Union

logger = logging.getLogger(__name__)

class VNPlugin:
    """
    Base class for all VNNotes plugins.
    """
    def __init__(self, context: Any, main_window: Any):
        self.context = context
        self.main_window = main_window
        self.manifest = {}

    def activate(self):
        """Called when the plugin is activated."""
        pass

    def deactivate(self):
        """Called when the plugin is deactivated."""
        pass

class PluginManager:
    """
    Handles discovery and lifecycle of plugins.
    """
    def __init__(self, context: Any, main_window: Any):
        self.context = context
        self.main_window = main_window
        self.plugins: Dict[str, VNPlugin] = {}
        
        # Path to root plugins directory
        if getattr(sys, 'frozen', False):
            self.plugins_dir = os.path.join(os.path.dirname(sys.executable), "plugins")
        else:
            self.plugins_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "plugins")
            
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            logger.info(f"Created plugins directory: {self.plugins_dir}")

        # Ensure the plugins parent directory is in sys.path so we can import 'plugins.*'
        parent_dir = os.path.dirname(self.plugins_dir)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
            logger.debug(f"Added {parent_dir} to sys.path")

    def load_plugins(self):
        """Scans the plugins directory and loads all valid plugins."""
        if not os.path.exists(self.plugins_dir):
            return

        for folder_name in os.listdir(self.plugins_dir):
            folder_path = os.path.join(self.plugins_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue

            manifest_path = os.path.join(folder_path, "manifest.json")
            if not os.path.exists(manifest_path):
                continue

            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                plugin_id = manifest.get("id")
                entry_point = manifest.get("entry_point", "plugin.py")
                
                if not plugin_id:
                    logger.warning(f"Plugin in {folder_name} missing 'id' in manifest.")
                    continue

                plugin_file = os.path.join(folder_path, entry_point)
                if not os.path.exists(plugin_file):
                    logger.warning(f"Plugin {plugin_id} entry point not found: {plugin_file}")
                    continue

                self._load_plugin(plugin_id, folder_name, manifest)
            except Exception as e:
                logger.error(f"Failed to load plugin from {folder_name}: {e}")

    def _load_plugin(self, plugin_id: str, folder_name: str, manifest: Dict):
        """Dynamically loads a plugin module and instantiates its class."""
        try:
            # 1. Prepare module path
            entry_point = manifest.get("entry_point", "plugin.py")
            module_base = entry_point.rsplit(".", 1)[0] # 'plugin' from 'plugin.py'
            pkg_name = f"plugins.{folder_name}"
            full_module_name = f"{pkg_name}.{module_base}"
            
            logger.debug(f"Importing plugin module: {full_module_name}")
            
            # 2. Fix for "is not a package" errors: Ensure parent package is loaded correctly
            if pkg_name in sys.modules and not hasattr(sys.modules[pkg_name], '__path__'):
                del sys.modules[pkg_name]
            
            # 3. Use standard import system
            if full_module_name in sys.modules:
                module = importlib.reload(sys.modules[full_module_name])
            else:
                module = importlib.import_module(full_module_name)
            
            # 4. Find the VNPlugin subclass in the module
            plugin_class: Type[VNPlugin] = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, VNPlugin) and attr is not VNPlugin:
                    plugin_class = attr
                    break

            if not plugin_class:
                logger.warning(f"No VNPlugin subclass found in plugin {plugin_id}")
                return

            # 5. Instantiate and Activate
            plugin_instance = plugin_class(self.context, self.main_window)
            plugin_instance.manifest = manifest
            
            logger.info(f"Activating plugin: {manifest.get('name', plugin_id)} ({manifest.get('version', '?.?.?')})")
            plugin_instance.activate()
            
            self.plugins[plugin_id] = plugin_instance
            
        except Exception as e:
            logger.error(f"Error activating plugin {plugin_id}: {e}", exc_info=True)

    def install_plugin(self, zip_path: str):
        """Extracts a plugin ZIP and reloads the system."""
        import zipfile
        import shutil
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 1. Basic validation: Find manifest.json
                namelist = zip_ref.namelist()
                manifest_entry = next((n for n in namelist if n.endswith("manifest.json")), None)
                if not manifest_entry:
                    return False, "Invalid plugin: manifest.json not found in ZIP."
                
                # 2. Extraction
                # We extract everything to a temporary folder first to handle nested or flat zips
                temp_dir = os.path.join(self.plugins_dir, "_temp_extract")
                if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
                os.makedirs(temp_dir)
                
                zip_ref.extractall(temp_dir)
                
                # 3. Move to permanent home
                # Locate the directory containing manifest.json
                manifest_abs_path = os.path.join(temp_dir, manifest_entry)
                plugin_source_dir = os.path.dirname(manifest_abs_path)
                
                # Determine folder name from manifest ID or zip name
                with open(manifest_abs_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                target_folder_name = manifest.get("id", os.path.basename(zip_path).replace(".zip", ""))
                target_dir = os.path.join(self.plugins_dir, target_folder_name)
                
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                
                shutil.copytree(plugin_source_dir, target_dir)
                shutil.rmtree(temp_dir)
                
                # Ensure it's a package
                init_py = os.path.join(target_dir, "__init__.py")
                if not os.path.exists(init_py):
                    with open(init_py, 'w') as f: pass
                
                # 4. Success! Now trigger a scan
                self.load_plugins()
                return True, f"Plugin '{manifest.get('name', target_folder_name)}' installed successfully!"
                
        except Exception as e:
            logger.error(f"Failed to install plugin: {e}")
            return False, f"Installation failed: {str(e)}"

    def install_plugin_from_url(self, url: str) -> Tuple[bool, str]:
        """Downloads a plugin from a URL and installs it."""
        try:
            logger.info(f"Downloading plugin from: {url}")
            
            # 1. Download to a temporary file
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip", mode='wb') as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            # 2. Use existing install_plugin method
            success, message = self.install_plugin(tmp_path)
            
            # 3. Cleanup
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
            return success, message
            
        except Exception as e:
            logger.error(f"Failed to download/install plugin from URL: {e}")
            return False, f"Download failed: {str(e)}"

    def deactivate_all(self):
        """Deactivates all loaded plugins."""
        for plugin_id, plugin in list(self.plugins.items()):
            try:
                logger.info(f"Deactivating plugin: {plugin_id}")
                plugin.deactivate()
            except Exception as e:
                logger.error(f"Error deactivating plugin {plugin_id}: {e}")
        self.plugins.clear()
