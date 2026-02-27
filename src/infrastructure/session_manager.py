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

    def save_single_note_state(self, dock):
        """DIAMOND-STANDARD: Surgically saves only one note dock to bypass full sync overhead."""
        if self._is_restoring or not self._restore_successful:
            return
            
        try:
            widget = dock.widget()
            if not widget: return
            obj_name = dock.objectName()
            
            from src.features.notes.note_pane import NotePane
            if obj_name.startswith("NoteDock_") or isinstance(widget, NotePane):
                # Extract content
                if hasattr(widget, 'get_save_content'):
                    content = widget.get_save_content()
                elif hasattr(widget, 'get_content_with_embedded_images'):
                    content = widget.get_content_with_embedded_images()
                else:
                    content = widget.toHtml()
                
                # Sync metadata and content for this specific note
                # Plan v13.7: Use intentional title (clean) to avoid persisting (1), (2) disambiguation
                title = dock.property("vnn_intentional_title") or dock.windowTitle()
                
                note_data = {
                    "obj_name": obj_name,
                    "title": title,
                    "content": content,
                    "zoom": widget.get_zoom() if hasattr(widget, 'get_zoom') else 100
                }
                
                # Use Service layer to sync only this one
                self.note_service.sync_to_storage([note_data])
                
                # Optional: Force flush if high-reliability is needed, 
                # but for auto-save, we can let OS buffer it for performance.
                # self.ctx.storage.flush()
                
                logging.debug(f"Incremental Save: {obj_name}")
        except Exception as e:
            logging.error(f"Failed incremental save for {dock.objectName()}: {e}")

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
        
        # Senior Fix: Explicitly track maximization state to override flaky restoreGeometry
        self.config.set_value("window/is_maximized", mw.isMaximized())
        
        notes_data = []
        browser_data = []
        
        # Filter valid docks
        valid_main_docks = [d for d in mw.findChildren(QDockWidget) 
                            if d.objectName() != "SidebarDock"]
        
        from src.features.notes.note_pane import NotePane
        from src.features.browser.browser_pane import BrowserPane

        for dock in valid_main_docks:
            try:
                # Plan v7.6 Fix: Ignore zombie docks that have been commanded to close but 
                # reside in memory pending the next Qt Event Loop iteration.
                if dock.property("vnn_closing"): continue
                
                widget = dock.widget()
                if not widget: continue
                obj_name = dock.objectName()
                
                # Robust detection using object name prefixes
                if obj_name.startswith("NoteDock_") or isinstance(widget, NotePane):
                    # Use the new high-perf save API if available
                    if hasattr(widget, 'get_save_content'):
                        content = widget.get_save_content()
                    elif hasattr(widget, 'get_content_with_embedded_images'):
                        content = widget.get_content_with_embedded_images()
                    else:
                        content = widget.toHtml()

                    # Plan v13.7: Use intentional title (clean) for persistence
                    title = dock.property("vnn_intentional_title") or dock.windowTitle()

                    notes_data.append({
                        "obj_name": obj_name, 
                        "title": title, 
                        "content": content,
                        "zoom": widget.get_zoom() if hasattr(widget, 'get_zoom') else 100
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
        """Restores window state and content. Called synchronously during startup."""
        if self._is_restoring: return
        self._is_restoring = True
        
        mw = self.main_window
        mw._is_restoring = True # Synchronize flag
        
        # Senior Optimization: Batch Context
        mw.setUpdatesEnabled(False)
        
        logging.info("Starting optimized batch restore...")
        from PyQt6.QtWidgets import QApplication
        
        try:
            # 1. Load Content
            notes = self.note_service.load_notes()
            browsers = self.browser_service.load_browsers()
            
            anchor_dock = None
            is_fresh_launch = not notes and not browsers
            
            if is_fresh_launch:
                # First launch: no saved data. Create default note with normal 
                # layout path (not the restoration path that skips tabification)
                mw._is_restoring = False
                mw.add_note_dock()
                mw._is_restoring = True
            else:
                # Optimized Restoration Loop
                for i, item in enumerate(notes):
                    if i >= 15: break 
                    if not hasattr(mw, 'note_service'):
                        logging.error("SessionManager: SKIP RESTORE - MainWindow missing note_service")
                        break
                    dock = mw.add_note_dock(
                        content=item.get("content", ""), 
                        title=item.get("title"), 
                        obj_name=item.get("obj_name"),
                        anchor_dock=anchor_dock,
                        zoom=item.get("zoom", 100)
                    )
                    if not anchor_dock: anchor_dock = dock
                    
                for i, item in enumerate(browsers):
                    break # Disable QWebEngine for Python 3.14 stability
                    if i >= 10: break
                    dock = mw.add_browser_dock(
                        url=item.get("url", "https://google.com"),
                        anchor_dock=anchor_dock,
                        obj_name=item.get("obj_name")
                    )
                    if not anchor_dock: anchor_dock = dock

            # 2. Restore Geometry & Dock State
            # Skip restoreState on fresh launch â€” no valid state exists,
            # and calling it would displace the newly created default dock.
            try:
                geo = self.config.get_value("window/geometry")
                if geo:
                    if isinstance(geo, str):
                        mw.restoreGeometry(QByteArray.fromHex(geo.encode()))
                    else:
                        mw.restoreGeometry(geo)
            except Exception as e:
                logging.error(f"Failed to restore geometry: {e}")
                
            if not is_fresh_launch:
                try:
                    state = self.config.get_value("window/dock_state_v5")
                    if state:
                        if isinstance(state, str):
                            success = mw.restoreState(QByteArray.fromHex(state.encode()))
                        else:
                            success = mw.restoreState(state)
                        logging.info(f"SessionManager: restoreState success: {success}")
                except Exception as e:
                    logging.error(f"Failed to restore dock state: {e}")

            # 3. Final Cleanup & Visual Refresh
            if hasattr(mw, 'sidebar'):
                mw.sidebar.refresh_tree()
                
            # â”€â”€ POST-RESTORE DOCK AREA SWEEP (DEFERRED) â”€â”€
            # Must run AFTER the event loop settles; doing addDockWidget/tabifyDockWidget
            # during restoreState internals can segfault.  We schedule it for 0ms later.
            def _deferred_dock_sweep():
                try:
                    right_area = Qt.DockWidgetArea.RightDockWidgetArea
                    left_area  = Qt.DockWidgetArea.LeftDockWidgetArea
                    no_area    = Qt.DockWidgetArea.NoDockWidgetArea

                    misplaced = []
                    right_anchor = None
                    
                    # 1. First Pass: Identify misplaced non-sidebar docks
                    for dock in mw.findChildren(QDockWidget):
                        obj = dock.objectName()
                        area = mw.dockWidgetArea(dock)
                        
                        if obj == "SidebarDock":
                            continue
                            
                        # If it's on the left, it's misplaced
                        if area == left_area:
                            misplaced.append(dock)
                        elif dock.isFloating() or area == no_area:
                            misplaced.append(dock)
                        elif area == right_area and right_anchor is None:
                            right_anchor = dock

                    # 2. Second Pass: Explicitly check if Sidebar is tabified with anything
                    if hasattr(mw, 'sidebar_dock'):
                        sd = mw.sidebar_dock
                        # Find docks tabified with sidebar and mark them as misplaced
                        tabified = mw.tabifiedDockWidgets(sd)
                        for d in tabified:
                            if d not in misplaced:
                                misplaced.append(d)

                    # 3. Move Misplaced Docks to Right
                    for dock in misplaced:
                        logging.info(f"Post-restore sweep: moving {dock.objectName()} -> RIGHT")
                        dock.setFloating(False)
                        if right_anchor is not None and right_anchor != dock:
                            mw.tabifyDockWidget(right_anchor, dock)
                        else:
                            mw.addDockWidget(right_area, dock)
                            if right_anchor is None:
                                right_anchor = dock
                        dock.show()

                    if hasattr(mw, 'sidebar_dock'):
                        mw.addDockWidget(left_area, mw.sidebar_dock)
                        mw.sidebar_dock.show()
                        mw.sidebar_dock.raise_()
                except Exception as e:
                    logging.error(f"Post-restore sweep failed (non-fatal): {e}")

            QTimer.singleShot(500, _deferred_dock_sweep)
            
            mw.check_docks_closed() # Update branding
            
            # Ensure visible docks are raised (Visual pass) - skip redundant raises if restoring
            # for dock in mw.findChildren(QDockWidget):
            #     if dock.isVisible() and dock.objectName() != "SidebarDock":
            #         dock.show()
            #         dock.raise_()
                    
            self._restore_successful = True # Restoration reached valid state
        except Exception as e:
            logging.critical(f"SessionManager: CATASTROPHIC RESTORE FAILURE: {e}", exc_info=True)
            self._restore_successful = False 
        finally:
            self._is_restoring = False
            mw._is_restoring = False
            # mw.blockSignals(False)
            mw.setUpdatesEnabled(True)
            QApplication.processEvents()
            
            # 5. Final Polish: Stabilization
            # if hasattr(mw, '_stabilize_layout'):
            #      mw._stabilize_layout()
            # 4. Global Startup Focus: Focus the first visible note pane
            visible_note_docks = [d for d in mw.findChildren(QDockWidget) 
                                 if d.isVisible() and d.objectName().startswith("NoteDock_")]
            if visible_note_docks:
                # Use the one that is currently 'on top' (at the end of the children list usually)
                target_dock = visible_note_docks[-1]
                pane = target_dock.widget()
                if pane:
                    mw.set_active_pane(pane)
                    pane.setFocus()
                    logging.info(f"SessionManager: Auto-focused {target_dock.objectName()} on startup.")

            logging.info("Optimized batch restore complete.")
