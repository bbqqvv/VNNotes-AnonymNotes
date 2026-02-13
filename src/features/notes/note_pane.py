from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFont, QTextListFormat, QTextCursor
from PyQt6.QtCore import pyqtSignal, Qt, QUrl

class NotePane(QTextEdit):
    focus_received = pyqtSignal(object) # Signal to notify main window of focus

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type notes here... (Paste images supported)")
        self.setMouseTracking(True) 
        self.viewport().setMouseTracking(True)
        self.setAcceptDrops(True)

    def set_html_safe(self, html):
        """
        Robustly sets HTML by extracting base64 images and adding them as document resources.
        This fixes issues where QTextEdit fails to render data:image URIs directly.
        """
        import re
        import base64
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import QUrl
        
        # Regex to find data URIs
        pattern = r'src="data:image/(?P<ext>[^;]+);base64,(?P<data>[^"]+)"'
        
        index = 0
        def replace_match(match):
            nonlocal index
            ext = match.group('ext')
            data_b64 = match.group('data')
            
            try:
                # 1. Decode base64
                img_data = base64.b64decode(data_b64)
                image = QImage.fromData(img_data)
                
                if not image.isNull():
                    # 2. Add as internal resource (ResourceType 3 = Image)
                    res_name = f"word_img_{index}.{ext}"
                    self.document().addResource(3, QUrl(res_name), image)
                    index += 1
                    # 3. Return new internal src
                    return f'src="{res_name}"'
            except Exception as e:
                print(f"Error processing Word image {index}: {e}")
                
            return match.group(0) # Keep original if failed

        # Replace and set
        processed_html = re.sub(pattern, replace_match, html)
        self.setHtml(processed_html)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focus_received.emit(self)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
             cursor = self.cursorForPosition(event.pos())
             fmt = cursor.charFormat()
             if fmt.isImageFormat():
                 self.resize_image_dialog(cursor)
                 return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check for Checkbox Click
            cursor = self.cursorForPosition(event.pos())
            cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.KeepAnchor)
            char = cursor.selectedText()
            
            if char in ["☐", "☑"]:
                new_char = "☑" if char == "☐" else "☐"
                cursor.insertText(new_char)
                return 

        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        # Create standard menu first
        menu = self.createStandardContextMenu()
        
        # --- NEW FEATURES: Search & Translate ---
        cursor = self.textCursor()
        selected_text = cursor.selectedText().strip()
        
        if selected_text:
            from PyQt6.QtGui import QAction, QIcon
            import os
            
            # Helper to find assets
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            icon_dir = os.path.join(base_path, "assets", "icons", "dark_theme")

            # Find MainWindow to access DockManager
            main_window = self.window()
            dock_manager = getattr(main_window, 'dock_manager', None)
            
            display_text = (selected_text[:20] + '..') if len(selected_text) > 20 else selected_text
            
            # Ask AI Action
            ai_act = QAction(f"✨ Ask AI '{display_text}'", self)
            ai_icon_path = os.path.join(icon_dir, "ai.svg")
            if os.path.exists(ai_icon_path):
                ai_act.setIcon(QIcon(ai_icon_path))
            
            if dock_manager:
                ai_url = f"https://www.perplexity.ai/?q={selected_text}"
                ai_act.triggered.connect(lambda: dock_manager.add_browser_dock(ai_url))

            # Translate Action
            translate_act = QAction(f"Translate '{display_text}'", self)
            translate_icon_path = os.path.join(icon_dir, "browser.svg")
            if os.path.exists(translate_icon_path):
                translate_act.setIcon(QIcon(translate_icon_path))
                
            if dock_manager:
                trans_url = f"https://translate.google.com/?sl=auto&tl=vi&text={selected_text}&op=translate"
                translate_act.triggered.connect(lambda: dock_manager.add_browser_dock(trans_url))
            
            # Search Action
            search_act = QAction(f"Search '{display_text}'", self)
            search_icon_path = os.path.join(icon_dir, "search.svg")
            if os.path.exists(search_icon_path):
                search_act.setIcon(QIcon(search_icon_path))
                
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
        cursor = self.cursorForPosition(event.pos())
        fmt = cursor.charFormat()
        
        if fmt.isImageFormat():
            menu.addSeparator()
            
            align_menu = menu.addMenu("📏 Alignment")
            align_left = align_menu.addAction("⬅️ Align Left")
            align_left.triggered.connect(lambda: self.set_image_alignment(cursor, Qt.AlignmentFlag.AlignLeft))
            align_center = align_menu.addAction("⏺️ Align Center")
            align_center.triggered.connect(lambda: self.set_image_alignment(cursor, Qt.AlignmentFlag.AlignCenter))
            align_right = align_menu.addAction("➡️ Align Right")
            align_right.triggered.connect(lambda: self.set_image_alignment(cursor, Qt.AlignmentFlag.AlignRight))
            
            menu.addSeparator()
            resize_act = menu.addAction("🖼️ Resize Image...")
            resize_act.triggered.connect(lambda: self.resize_image_dialog(cursor))
            reset_act = menu.addAction("🔄 Reset Size")
            reset_act.triggered.connect(lambda: self.reset_image_size(cursor))
            save_act = menu.addAction("💾 Save Image As...")
            save_act.triggered.connect(lambda: self.save_image_as(cursor))
            
        menu.exec(event.globalPos())

    def set_image_alignment(self, cursor, alignment):
        block_cursor = QTextCursor(cursor)
        from PyQt6.QtGui import QTextBlockFormat
        block_fmt = QTextBlockFormat()
        block_fmt.setAlignment(alignment)
        block_cursor.mergeBlockFormat(block_fmt)

    def resize_image_dialog(self, cursor):
        from PyQt6.QtWidgets import QInputDialog
        target_cursor = None
        img_fmt = None
        
        if cursor.charFormat().isImageFormat():
            target_cursor = self.textCursor()
            target_cursor.setPosition(cursor.position())
            target_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
            img_fmt = cursor.charFormat().toImageFormat()
            
        if not target_cursor:
            c_right = self.textCursor()
            c_right.setPosition(cursor.position())
            c_right.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            if c_right.charFormat().isImageFormat():
                target_cursor = c_right
                img_fmt = c_right.charFormat().toImageFormat()

        if not target_cursor or not img_fmt:
            return

        current_width = img_fmt.width()
        name = img_fmt.name()
        
        image_resource = self.document().resource(3, QUrl(name))
        native_width = image_resource.width() if image_resource and not image_resource.isNull() else 0
        native_height = image_resource.height() if image_resource and not image_resource.isNull() else 0
        
        start_width = current_width if current_width > 0 else (native_width if native_width > 0 else 300)
        
        new_width, ok = QInputDialog.getInt(self, "Resize Image", "Enter new width (px):", int(start_width), 10, 2000, 10)
        
        if ok:
             new_height = 0
             if native_width > 0:
                  new_height = int(new_width * (native_height / native_width))
             
             new_fmt = target_cursor.charFormat().toImageFormat()
             new_fmt.setName(name)
             new_fmt.setWidth(new_width)
             if new_height > 0: new_fmt.setHeight(new_height)
             else: new_fmt.setHeight(0)
             
             target_cursor.mergeCharFormat(new_fmt)

    def reset_image_size(self, cursor):
        self.setTextCursor(cursor)
        selection_cursor = self.textCursor()
        selection_cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
        if not selection_cursor.charFormat().isImageFormat():
             selection_cursor = self.textCursor()
             selection_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
        if selection_cursor.charFormat().isImageFormat():
             fmt = selection_cursor.charFormat().toImageFormat()
             fmt.setWidth(0)
             fmt.setHeight(0)
             selection_cursor.setCharFormat(fmt)

    def save_image_as(self, cursor):
        from PyQt6.QtWidgets import QFileDialog
        fmt = cursor.charFormat().toImageFormat()
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
                self.set_html_safe(f'<img src="data:image/png;base64,{base64_data}" />')
                return
        super().insertFromMimeData(source)

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
        self.set_html_safe(f'<img src="data:image/png;base64,{base64_data}" />')
