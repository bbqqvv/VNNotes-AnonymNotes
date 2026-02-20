import logging
import threading
from PyQt6.QtCore import QTimer, QByteArray, Qt
from PyQt6.QtWidgets import QDockWidget

class SessionManager:
    """
    Manages application session state (saving/restoring window geometry, docks, and content).
    Separates persistence logic from MainWindow.
    """
    def __init__(self, main_window, context):
        self.main_window = main_window
        self.ctx = context
        self.config = context.config
        self.note_service = context.notes
        self.browser_service = context.browser
        
        self.autosave_timer = QTimer(self.main_window)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(2000)
        self.autosave_timer.timeout.connect(self.auto_save)
        
        self._is_restoring = False
        self._restore_successful = False # Data integrity guard

    def start_autosave(self):
        """Starts or restarts the autosave timer if enabled."""
        autosave_enabled = self.config.get_value("app/autosave_enabled", True)
        if isinstance(autosave_enabled, str):
            autosave_enabled = autosave_enabled.lower() == 'true'
        
        if autosave_enabled:
            self.autosave_timer.start()

    def set_autosave_enabled(self, enabled):
        """Enables or disables auto-save."""
        self.config.set_value("app/autosave_enabled", enabled)
        if enabled:
            if not self.autosave_timer.isActive():
                self.autosave_timer.start()
        else:
            if self.autosave_timer.isActive():
                self.autosave_timer.stop()

    def auto_save(self):
        """Background auto-save."""
        self.save_app_state()

    def save_app_state(self):
        """Saves current window state, notes, and other data."""
        if self._is_restoring:
            logging.debug("Skipping save_app_state: Restore in progress")
            return
            
        if not self._restore_successful:
            logging.error("SessionManager: save_app_state BLOCKED - Window restoration never completed successfully.")
            return

        mw = self.main_window

        # Convert QByteArray to Hex string for stable INI storage
        self.config.set_value("window/geometry", str(mw.saveGeometry().toHex(), 'utf-8'))
        self.config.set_value("window/dock_state_v5", str(mw.saveState().toHex(), 'utf-8'))
        
        notes_data = []
        browser_data = []
        
        # Filter valid docks
        valid_main_docks = [d for d in mw.findChildren(QDockWidget) 
                            if d.objectName() != "SidebarDock"]
        
        from src.features.notes.note_pane import NotePane
        from src.features.browser.browser_pane import BrowserPane

        for dock in valid_main_docks:
            try:
                widget = dock.widget()
                if not widget: continue
                obj_name = dock.objectName()
                
                # Robust detection using object name prefixes
                if obj_name.startswith("NoteDock_") or isinstance(widget, NotePane):
                    content = widget.get_content_with_embedded_images() if hasattr(widget, 'get_content_with_embedded_images') else widget.toHtml()
                    notes_data.append({
                        "obj_name": obj_name, 
                        "title": dock.windowTitle(), 
                        "content": content
                    })
                elif obj_name.startswith("BrowserDock_") or isinstance(widget, BrowserPane):
                    # Safe check for browser widget attributes
                    url = "https://google.com"
                    if hasattr(widget, 'browser'):
                        url = widget.browser.url().toString()
                    elif hasattr(widget, 'url'):
                        url = widget.url
                        
                    browser_data.append({
                        "obj_name": obj_name, 
                        "title": dock.windowTitle(), 
                        "url": url
                    })
            except (RuntimeError, AttributeError) as e:
                logging.debug(f"Error saving dock {dock.objectName()}: {e}")
                continue
                
        # Sync to Services
        self.note_service.sync_to_storage(notes_data)
        self.browser_service.sync_to_storage(browser_data)
        
        # Force immediate write to disk (bypass throttle)
        if hasattr(self.ctx, 'storage'):
            self.ctx.storage.flush()
            
        logging.info(f"State Saved: {len(notes_data)} notes, {len(browser_data)} browsers.")

    def restore_app_state(self):
        """Restores window state and content."""
        if self._is_restoring: return
        self._is_restoring = True
        
        mw = self.main_window
        mw._is_restoring = True # Synchronize flag
        
        # Senior Optimization: Batch Context
        mw.setUpdatesEnabled(False)
        mw.blockSignals(True)
        
        logging.info("Starting optimized batch restore...")
        from PyQt6.QtWidgets import QApplication
        
        try:
            # 1. Load Content
            notes = self.note_service.load_notes()
            browsers = self.browser_service.load_browsers()
            
            anchor_dock = None
            
            if not notes and not browsers:
                mw.add_note_dock()
            else:
                # Optimized Restoration Loop
                for i, item in enumerate(notes):
                    if i >= 15: break 
                    dock = mw.add_note_dock(
                        content=item.get("content", ""), 
                        title=item.get("title"), 
                        obj_name=item.get("obj_name"),
                        anchor_dock=anchor_dock
                    )
                    if not anchor_dock: anchor_dock = dock
                    
                for i, item in enumerate(browsers):
                    if i >= 10: break
                    dock = mw.add_browser_dock(
                        url=item.get("url", "https://google.com"),
                        anchor_dock=anchor_dock,
                        obj_name=item.get("obj_name")
                    )
                    if not anchor_dock: anchor_dock = dock

            # 2. Restore Geometry & Dock State
            try:
                geo = self.config.get_value("window/geometry")
                if geo:
                    if isinstance(geo, str):
                        mw.restoreGeometry(QByteArray.fromHex(geo.encode()))
                    else:
                        mw.restoreGeometry(geo)
            except Exception as e:
                logging.error(f"Failed to restore geometry: {e}")
                
            try:
                state = self.config.get_value("window/dock_state_v5")
                if state:
                    if isinstance(state, str):
                        mw.restoreState(QByteArray.fromHex(state.encode()))
                    else:
                        mw.restoreState(state)
            except Exception as e:
                logging.error(f"Failed to restore dock state: {e}")

            # 3. Final Cleanup & Visual Refresh
            if hasattr(mw, 'sidebar'):
                mw.sidebar.refresh_tree()
                
            mw.check_docks_closed() # Update branding
            
            # Ensure visible docks are raised (Visual pass)
            for dock in mw.findChildren(QDockWidget):
                if dock.isVisible() and dock.objectName() != "SidebarDock":
                    dock.show()
                    dock.raise_()
                    
            self._restore_successful = True # Restoration reached valid state
        except Exception as e:
            logging.critical(f"SessionManager: CATASTROPHIC RESTORE FAILURE: {e}", exc_info=True)
            self._restore_successful = False 
        finally:
            self._is_restoring = False
            mw._is_restoring = False
            mw.blockSignals(False)
            mw.setUpdatesEnabled(True)
            QApplication.processEvents()
            # Deferred sidebar refresh — ensures browser widgets are fully initialized
            if hasattr(mw, 'sidebar') and mw.sidebar:
                QTimer.singleShot(100, mw.sidebar.refresh_tree)
            logging.info("Optimized batch restore complete.")
