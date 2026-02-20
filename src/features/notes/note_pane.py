import logging
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFont, QTextListFormat, QTextCursor, QTextBlockFormat
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt, QUrl, QRect

class NotePane(QTextEdit):
    focus_received = pyqtSignal(object) # Signal to notify main window of focus
    content_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type notes here... (Paste images supported)")
        self.setMouseTracking(True) 
        self.viewport().setMouseTracking(True)
        self.setAcceptDrops(True)
        self._deferred_content = None # Lazy Loading support
        self.file_path = None # Tracking the physical file on disk
        
        self.textChanged.connect(self.content_changed.emit)

    def load_deferred_content(self):
        """Loads the content only when actually needed (visible)."""
        if self._deferred_content is not None:
            logging.debug(f"NotePane: Loading deferred content (len={len(self._deferred_content)})")
            # Block signals to avoid triggering on_content_changed during initial load
            self.blockSignals(True)
            self.set_html_safe(self._deferred_content)
            self._deferred_content = None
            self.blockSignals(False)
            return True
        return False

    def showEvent(self, event):
        """Triggered when the widget is shown. Perfect time for lazy loading."""
        super().showEvent(event)
        self.load_deferred_content()
    def _process_html_for_insertion(self, html):
        """
        Processes HTML by extracting base64 images and adding them as document resources.
        Returns the processed HTML string WITHOUT setting it to the document.
        """
        import re
        import base64
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import QUrl
        
        # Regex to find data URIs
        pattern = r'src=["\']data:image/(?P<ext>[^;]+);base64,(?P<data>[^"\']+)["\']'
        
        # Use a timestamp-based unique prefix to avoid collisions with Word images
        import time
        prefix = int(time.time() * 1000)
        index = 0
        doc = self.document()
        
        def replace_match(match):
            nonlocal index
            ext = match.group('ext')
            data_b64 = match.group('data')
            
            try:
                img_data = base64.b64decode(data_b64)
                image = QImage.fromData(img_data)
                
                if not image.isNull():
                    res_name = f"img_{prefix}_{index}.{ext}"
                    doc.addResource(3, QUrl(res_name), image)
                    index += 1
                    return f'src="{res_name}"'
            except Exception:
                pass
            return match.group(0)

        processed_html = re.sub(pattern, replace_match, html)
        
        # --- SURGICAL NORMALIZATION ---
        # Strip style (CSS) which often contains conflicting/broken units (in, pt)
        # BUT keep width and height attributes if they exist (for persistence)
        processed_html = re.sub(r'(<img[^>]+)style=["\'][^"\']*["\']', r'\1', processed_html)
        
        return processed_html

    def set_html_safe(self, html):
        """
        Safely sets the entire document HTML. Used during note loading.
        Maintains width/height attributes for persistence.
        """
        processed_html = self._process_html_for_insertion(html)
        # Note: We do NOT strip width/height here anymore, 
        # as they are the source of truth for saved sizes.
        self.setHtml(processed_html)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.load_deferred_content() # Extra safety: load if user clicks it
        self.focus_received.emit(self)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
             # Use precision spatial sensor
             img_cursor = self._get_image_at_cursor(self.cursorForPosition(event.pos()), event.pos())
             if img_cursor:
                 self.resize_image_dialog(img_cursor)
                 return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        """Provide visual feedback (hand cursor) ONLY when over images."""
        if self._get_image_at_cursor(self.cursorForPosition(event.pos()), event.pos()):
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check for Checkbox Click
            cursor = self.cursorForPosition(event.pos())
            # Peek right
            test_cursor = QTextCursor(cursor)
            test_cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            char = test_cursor.selectedText()
            
            if char in ["☐", "☑"]:
                new_char = "☑" if char == "☐" else "☐"
                test_cursor.insertText(new_char)
                return 

        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        # Create standard menu first
        menu = self.createStandardContextMenu()
        
        from PyQt6.QtGui import QAction, QIcon
        import os
        
        # Helper to find assets
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        # Determine theme from MainWindow
        main_window = self.window()
        theme = "dark"
        if hasattr(main_window, 'theme_manager'):
            theme = main_window.theme_manager.current_theme
        
        icon_folder = "dark_theme" if theme == "dark" else "light_theme"
        icon_dir = os.path.join(base_path, "assets", "icons", icon_folder)
        
        # Apply SVG icons to standard actions if possible
        # Standard actions usually don't have icons by default in simple QTextEdit context menu
        # We can try to map them by text if needed, but the user specifically asked for SVGs everywhere.
        # Let's add icons to the standard ones we have in our assets.
        for action in menu.actions():
            text = action.text().replace("&", "")
            if "Undo" in text: action.setIcon(QIcon(os.path.join(icon_dir, "theme.svg"))) # Placeholder if none
            if "Redo" in text: action.setIcon(QIcon(os.path.join(icon_dir, "refresh.svg")))
            if "Cut" in text: action.setIcon(QIcon(os.path.join(icon_dir, "close.svg"))) # Reuse or specific
            if "Copy" in text: action.setIcon(QIcon(os.path.join(icon_dir, "clipboard.svg")))
            if "Paste" in text: action.setIcon(QIcon(os.path.join(icon_dir, "clipboard.svg")))
            if "Delete" in text: action.setIcon(QIcon(os.path.join(icon_dir, "trash.svg")))
            if "Select All" in text: action.setIcon(QIcon(os.path.join(icon_dir, "search.svg")))

        # --- NEW FEATURES: Search & Translate ---
        cursor = self.textCursor()
        selected_text = cursor.selectedText().strip()
        
        if selected_text:
            dock_manager = getattr(main_window, 'dock_manager', None)
            display_text = (selected_text[:20] + '..') if len(selected_text) > 20 else selected_text
            
            # Ask AI Action
            ai_act = QAction("Ask AI", self)
            ai_act.setIcon(QIcon(os.path.join(icon_dir, "ai.svg")))
            if dock_manager:
                ai_url = f"https://www.perplexity.ai/?q={selected_text}"
                ai_act.triggered.connect(lambda: dock_manager.add_browser_dock(ai_url))

            # Translate Action
            translate_act = QAction("Translate", self)
            translate_act.setIcon(QIcon(os.path.join(icon_dir, "browser.svg")))
            if dock_manager:
                trans_url = f"https://translate.google.com/?sl=auto&tl=vi&text={selected_text}&op=translate"
                translate_act.triggered.connect(lambda: dock_manager.add_browser_dock(trans_url))
            
            # Search Action
            search_act = QAction("Search", self)
            search_act.setIcon(QIcon(os.path.join(icon_dir, "search.svg")))
            if dock_manager:
                search_url = f"https://www.google.com/search?q={selected_text}"
                search_act.triggered.connect(lambda: dock_manager.add_browser_dock(search_url))

            # Insert at the TOP
            first_action = menu.actions()[0] if menu.actions() else None
            
            if first_action:
                menu.insertAction(first_action, translate_act)
                menu.insertAction(translate_act, search_act) 
                menu.insertAction(search_act, ai_act) # AI First
                menu.insertSeparator(first_action)
            else:
                menu.addAction(ai_act)
                menu.addAction(search_act)
                menu.addAction(translate_act)
        
        # --- Image Options ---
        # Use precision spatial sensor
        img_cursor = self._get_image_at_cursor(self.cursorForPosition(event.pos()), event.pos())
        
        if img_cursor:
            fmt = img_cursor.charFormat()
            menu.addSeparator()
            
            align_menu = menu.addMenu(QIcon(os.path.join(icon_dir, "theme.svg")), "Alignment")
            
            align_left = align_menu.addAction(QIcon(os.path.join(icon_dir, "align-left.svg")), "Align Left")
            align_left.triggered.connect(lambda: self.apply_alignment(Qt.AlignmentFlag.AlignLeft))
            
            align_center = align_menu.addAction(QIcon(os.path.join(icon_dir, "align-center.svg")), "Align Center")
            align_center.triggered.connect(lambda: self.apply_alignment(Qt.AlignmentFlag.AlignCenter))
            
            align_right = align_menu.addAction(QIcon(os.path.join(icon_dir, "align-right.svg")), "Align Right")
            align_right.triggered.connect(lambda: self.apply_alignment(Qt.AlignmentFlag.AlignRight))
            
            menu.addSeparator()
            
            resize_act = menu.addAction(QIcon(os.path.join(icon_dir, "image.svg")), "Resize Image...")
            resize_act.triggered.connect(lambda: self.resize_image_dialog(cursor))
            
            reset_act = menu.addAction(QIcon(os.path.join(icon_dir, "refresh.svg")), "Reset Size")
            reset_act.triggered.connect(lambda: self.reset_image_size(cursor))
            
            save_act = menu.addAction(QIcon(os.path.join(icon_dir, "clipboard.svg")), "Save Image As...")
            save_act.triggered.connect(lambda: self.save_image_as(cursor))
            
        menu.exec(event.globalPos())

    def apply_alignment(self, alignment):
        """Applies alignment to the current block(s)."""
        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(alignment)
        cursor = self.textCursor()
        cursor.mergeBlockFormat(block_fmt)
        self.setFocus()

    def _get_image_at_cursor(self, cursor, pos=None):
        """
        Robustly identifies and selects the image character at or near the cursor.
        Returns a QTextCursor with the image selected, or None.
        Calculates holistic bounding boxes for 100% surface area hit detection.
        """
        # Scan current, previous, and next blocks to handle alignment/proximity mapping issues
        target_block = cursor.block()
        blocks_to_search = [target_block]
        if target_block.previous().isValid(): blocks_to_search.append(target_block.previous())
        if target_block.next().isValid(): blocks_to_search.append(target_block.next())

        for block in blocks_to_search:
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():
                    fmt = fragment.charFormat().toImageFormat()
                    
                    # 1. Capture the Top-Left using a zero-width cursor at start of fragment
                    tl_cursor = QTextCursor(self.document())
                    tl_cursor.setPosition(fragment.position())
                    top_left_rect = self.cursorRect(tl_cursor)
                    tl = top_left_rect.topLeft()
                    
                    # 2. Get the actual display size
                    w = fmt.width()
                    h = fmt.height()
                    
                    # 3. Construct a holistic bounding box
                    image_rect = QRect(tl.x(), tl.y(), int(w), int(h))
                    
                    if pos:
                        # 4. Check if the mouse (viewport coords) is inside this visual rectangle
                        # Includes 5px padding for easier interaction.
                        if image_rect.adjusted(-5, -5, 5, 5).contains(pos):
                            img_cursor = QTextCursor(self.document())
                            img_cursor.setPosition(fragment.position())
                            img_cursor.movePosition(QTextCursor.MoveOperation.Right, 
                                                   QTextCursor.MoveMode.KeepAnchor, 
                                                   fragment.length())
                            return img_cursor
                    else:
                        img_cursor = QTextCursor(self.document())
                        img_cursor.setPosition(fragment.position())
                        img_cursor.movePosition(QTextCursor.MoveOperation.Right, 
                                               QTextCursor.MoveMode.KeepAnchor, 
                                               fragment.length())
                        return img_cursor
                it += 1
                 
        return None

    def resize_image_dialog(self, cursor):
        """Standardizes image resizing with native ratio support."""
        from PyQt6.QtWidgets import QInputDialog
        
        # 1. Robustly find the image
        img_cursor = self._get_image_at_cursor(cursor)
        if not img_cursor:
            return
            
        target_fmt = img_cursor.charFormat().toImageFormat()
        name = target_fmt.name()
        image_res = self.document().resource(3, QUrl(name))
        
        # Get native dimensions
        native_w = image_res.width() if image_res and not image_res.isNull() else 0
        native_h = image_res.height() if image_res and not image_res.isNull() else 0
        
        current_w = target_fmt.width()
        if current_w <= 0: current_w = native_w if native_w > 0 else 300
        
        # 2. Prompt for width
        new_width, ok = QInputDialog.getInt(self, "Resize Image", 
                                           f"Enter width (Native: {native_w}px):", 
                                           int(current_w), 10, 3000, 10)
        
        if ok and new_width > 0:
            # Maintain aspect ratio if possible
            new_height = 0
            if native_w > 0:
                new_height = int(new_width * (native_h / native_w))
            
            # 3. Apply format AUTHORITATIVELY with EXACT selection
            new_fmt = target_fmt
            new_fmt.setWidth(new_width)
            if new_height > 0:
                new_fmt.setHeight(new_height)
            
            # Use the img_cursor found by our sensor (it already has the char selected)
            img_cursor.setCharFormat(new_fmt)
            self.setFocus()

    def reset_image_size(self, cursor):
        img_cursor = self._get_image_at_cursor(cursor)
        if img_cursor:
             fmt = img_cursor.charFormat().toImageFormat()
             fmt.setWidth(0)
             fmt.setHeight(0)
             img_cursor.setCharFormat(fmt)
             self.setFocus()

    def save_image_as(self, cursor):
        from PyQt6.QtWidgets import QFileDialog
        img_cursor = self._get_image_at_cursor(cursor)
        if not img_cursor:
            return
            
        fmt = img_cursor.charFormat().toImageFormat()
        name = fmt.name()
        image = self.document().resource(3, QUrl(name))
        if image and not image.isNull():
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "image.png", "Images (*.png *.jpg)")
            if file_path: image.save(file_path)

    def apply_format(self, fmt_type):
        cursor = self.textCursor()
        fmt = cursor.charFormat()
        
        if fmt_type == "bold":
            fmt.setFontWeight(QFont.Weight.Bold if fmt.fontWeight() != QFont.Weight.Bold else QFont.Weight.Normal)
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "italic":
            fmt.setFontItalic(not fmt.fontItalic())
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "underline":
            fmt.setFontUnderline(not fmt.fontUnderline())
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "list":
            cursor.createList(QTextListFormat.Style.ListDisc)
        elif fmt_type == "checkbox":
            cursor.insertText("☐ ")
        elif fmt_type == "code":
            from PyQt6.QtGui import QColor
            fmt.setFontFamilies(["Consolas", "Courier New", "Monospace"])
            fmt.setBackground(QColor("#444444"))
            fmt.setForeground(QColor("#e0e0e0"))
            cursor.mergeCharFormat(fmt)
        elif fmt_type == "highlight":
            from PyQt6.QtGui import QColor
            if fmt.background().color().name() == "#ffff00":
                fmt.setBackground(Qt.GlobalColor.transparent)
            else:
                fmt.setBackground(QColor("yellow"))
                fmt.setForeground(QColor("black"))
            cursor.mergeCharFormat(fmt)
        # Alignment
        elif fmt_type == "align-left":
            self.apply_alignment(Qt.AlignmentFlag.AlignLeft)
        elif fmt_type == "align-center":
            self.apply_alignment(Qt.AlignmentFlag.AlignCenter)
        elif fmt_type == "align-right":
            self.apply_alignment(Qt.AlignmentFlag.AlignRight)
        elif fmt_type == "align-justify":
            self.apply_alignment(Qt.AlignmentFlag.AlignJustify)
            
        self.setFocus()
        
    def canInsertFromMimeData(self, source):
        return source.hasImage() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if image:
                from PyQt6.QtCore import QBuffer, QIODevice
                from PyQt6.QtGui import QImage
                import base64
                if not isinstance(image, QImage): image = QImage(image)
                ba = QBuffer()
                ba.open(QIODevice.OpenModeFlag.WriteOnly)
                image.save(ba, "PNG")
                base64_data = base64.b64encode(ba.data().data()).decode('utf-8')
                # FIX: Use insertHtml to avoid wiping the document
                processed_img = self._process_html_for_insertion(f'<img src="data:image/png;base64,{base64_data}" />')
                self.textCursor().insertHtml(processed_img)
                return
        super().insertFromMimeData(source)

    def get_content_with_embedded_images(self):
        """
        Exports HTML with images embedded as base64 data URIs.
        This ensures images persist across sessions.
        """
        # CRITICAL: Ensure content is loaded from deferred state before we try to take a snapshot
        self.load_deferred_content()
        
        html = self.toHtml()
        doc = self.document()
        
        # Regex to find src="word_img_..." or other internal resources
        # We need to find the resource name and replace it with data URI
        import re
        import base64
        from PyQt6.QtCore import QBuffer, QIODevice
        
        # Helper to convert QImage to Base64
        def image_to_base64(image):
            ba = QBuffer()
            ba.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(ba, "PNG")
            return base64.b64encode(ba.data().data()).decode('utf-8')

        def replace_src(match):
            src = match.group(1)
            # Check if it's an internal resource (img_... or word_img_... or qrc:/)
            if any(p in src for p in ["img_", "word_img_", "qrc:/"]):
                 # Resource Type 3 is Image
                 image = doc.resource(3, QUrl(src))
                 
                 if image and not image.isNull():
                     b64_data = image_to_base64(image)
                     return f'src="data:image/png;base64,{b64_data}"'
            
            return match.group(0) # Keep original if not an internal image

        # Replace src="..."
        # Pattern matches src="value"
        pattern = r'src="([^"]+)"'
        new_html = re.sub(pattern, replace_src, html)
        return new_html

    def insert_image_from_file(self):
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import QBuffer, QIODevice
        import base64
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if not file_path: return
        image = QImage(file_path)
        if image.isNull(): return
        ba = QBuffer()
        ba.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(ba, "PNG")
        base64_data = base64.b64encode(ba.data().data()).decode('utf-8')
        # FIX: Use insertHtml to avoid wiping the document
        processed_img = self._process_html_for_insertion(f'<img src="data:image/png;base64,{base64_data}" />')
        self.textCursor().insertHtml(processed_img)
