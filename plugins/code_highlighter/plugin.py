import logging
from src.core.plugins import VNPlugin
from .highlighter import UniversalHighlighter
from PyQt6.QtGui import QAction

logger = logging.getLogger(__name__)

class CodeHighlighterPlugin(VNPlugin):
    """
    Plugin that manages syntax highlighting lifecycle based on Dev Mode.
    """
    def __init__(self, context, main_window):
        super().__init__(context, main_window)
        self.highlighters = {} # dock_obj_name -> highlighter instance

    def activate(self):
        logger.info("Syntax Highlighter Plugin Activated")
        
        # 1. Listen for new notes
        self.main_window.note_dock_created.connect(self._on_note_created)
        logger.debug("Connected to note_dock_created signal")
        
        # 2. Listen for Dev Mode changes
        dev_mode_act = self.main_window.menu_manager.actions.get("dev_mode")
        if dev_mode_act:
            dev_mode_act.toggled.connect(self.update_all_highlighters)
            logger.debug("Connected to dev_mode toggled signal")
        else:
            logger.warning("Dev Mode action not found in MenuToolbarManager")
        
        # 3. Listen for theme changes to update highlighter colors
        if hasattr(self.main_window, 'theme_manager'):
            self.main_window.theme_manager.theme_changed.connect(self._on_theme_changed)
            logger.debug("Connected to theme_changed signal")

        # 4. Initial state
        self.update_all_highlighters()

    def deactivate(self):
        logger.info("Syntax Highlighter Plugin Deactivated")
        self.clear_all_highlighters()

    def _on_note_created(self, dock):
        # Auto-apply if Dev Mode is currently ON
        dev_mode_act = self.main_window.menu_manager.actions.get("dev_mode")
        if dev_mode_act and dev_mode_act.isChecked():
            self._apply_to_dock(dock)

    def update_all_highlighters(self, checked=None):
        dev_mode_act = self.main_window.menu_manager.actions.get("dev_mode")
        is_active = checked if checked is not None else (dev_mode_act.isChecked() if dev_mode_act else False)
        logger.info(f"Updating highlighters. Dev Mode: {is_active}")
        
        if is_active:
            docks = self.main_window.dock_manager.get_note_docks()
            logger.debug(f"Found {len(docks)} note docks to process")
            for dock in docks:
                self._apply_to_dock(dock)
        else:
            self.clear_all_highlighters()

    def _on_theme_changed(self, is_dark):
        """Dynamic theme update for existing highlighters."""
        logger.info(f"Theme changed, updating highlighters (is_dark={is_dark})")
        for highlighter in self.highlighters.values():
            if hasattr(highlighter, 'is_dark'):
                highlighter.is_dark = is_dark
                highlighter._initialize_formats()
                highlighter.rehighlight()

    def _apply_to_dock(self, dock):
        obj_name = dock.objectName()
        if obj_name in self.highlighters:
            return
            
        pane = dock.widget()
        if hasattr(pane, 'document'):
            logger.debug(f"Applying highlighter to {obj_name}")
            is_dark = self.main_window.theme_manager.is_dark_mode if hasattr(self.main_window, 'theme_manager') else True
            highlighter = UniversalHighlighter(pane.document(), is_dark=is_dark)
            self.highlighters[obj_name] = highlighter

    def clear_all_highlighters(self):
        logger.debug("Clearing all syntax highlighters")
        for obj_name, highlighter in list(self.highlighters.items()):
            highlighter.setDocument(None)
            del self.highlighters[obj_name]
