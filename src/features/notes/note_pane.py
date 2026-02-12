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
        
        self.setStyleSheet("""
            QTextEdit {
                background-color: #333;
                color: #eee;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                border: none;
                padding: 10px;
            }
            QTextEdit:focus {
                background-color: #383838;
            }
        """)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.focus_received.emit(self)

    # ... Formatting methods ...

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
        
        # Check if cursor is on image
        cursor = self.cursorForPosition(event.pos())
        fmt = cursor.charFormat()
        
        if fmt.isImageFormat():
            menu.addSeparator()
            
            resize_act = menu.addAction("🖼️ Resize Image...")
            resize_act.triggered.connect(lambda: self.resize_image_dialog(cursor))
            
            reset_act = menu.addAction("🔄 Reset Size")
            reset_act.triggered.connect(lambda: self.reset_image_size(cursor))
            
            save_act = menu.addAction("💾 Save Image As...")
            save_act.triggered.connect(lambda: self.save_image_as(cursor))
            
        menu.exec(event.globalPos())

    def resize_image_dialog(self, cursor):
        from PyQt6.QtWidgets import QInputDialog
        
        fmt = cursor.charFormat().toImageFormat()
        current_width = fmt.width()
        
        # If width is 0, it means original size. Try to get it.
        if current_width == 0:
             # Try to get native size
             name = fmt.name()
             image = self.document().resource(3, QUrl(name))
             if image and not image.isNull():
                 current_width = image.width()
             else:
                 current_width = 300 # Default fallback
        
        new_width, ok = QInputDialog.getInt(
            self, "Resize Image", "Enter new width (px):", 
            int(current_width), 10, 2000, 10
        )
        
        if ok:
            # Apply new width
            # We need to make sure we apply it to the image at cursor
            # Select the image char
            self.setTextCursor(cursor)
            selection_cursor = self.textCursor()
            selection_cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            
    def resize_image_dialog(self, cursor):
        from PyQt6.QtWidgets import QInputDialog
        
        # 1. Precise Image Targeting
        # cursor.charFormat() refers to the char BEFORE the cursor.
        
        target_cursor = None
        img_fmt = None
        
        # Strategy A: Check current cursor (Image is to the LEFT)
        if cursor.charFormat().isImageFormat():
            target_cursor = self.textCursor()
            target_cursor.setPosition(cursor.position())
            target_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
            img_fmt = cursor.charFormat().toImageFormat()
            
        # Strategy B: Check right of cursor (Image is to the RIGHT)
        # We peek at the char to the right
        if not target_cursor:
            c_right = self.textCursor()
            c_right.setPosition(cursor.position())
            c_right.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
            if c_right.charFormat().isImageFormat():
                target_cursor = c_right
                img_fmt = c_right.charFormat().toImageFormat()

        if not target_cursor or not img_fmt:
            return

        # 2. Get Data
        current_width = img_fmt.width()
        current_height = img_fmt.height()
        name = img_fmt.name() # CRITICAL: This holds the Base64 data for embedded images
        
        # Native size fallback
        image_resource = self.document().resource(3, QUrl(name))
        native_width = 0
        native_height = 0
        if image_resource and not image_resource.isNull():
             native_width = image_resource.width()
             native_height = image_resource.height()
        
        start_width = current_width if current_width > 0 else (native_width if native_width > 0 else 300)
        
        # 3. User Input
        new_width, ok = QInputDialog.getInt(
            self, "Resize Image", "Enter new width (px):", 
            int(start_width), 10, 2000, 10
        )
        
        if ok:
             # 4. Aspect Ratio Calculation
             new_height = 0
             if native_width > 0 and native_height > 0:
                  new_height = int(new_width * (native_height / native_width))
             elif current_width > 0 and current_height > 0:
                  new_height = int(new_width * (current_height / current_width))
             
             # 5. Apply Updates
             # IMPORTANT: We must create a new format but manually ensure the NAME is set.
             # Sometimes toImageFormat() might produce a format that needs explicit naming when re-applied.
             
             new_fmt = target_cursor.charFormat().toImageFormat() # Start from fresh selection format
             new_fmt.setName(name) # Explicitly restore name
             new_fmt.setWidth(new_width)
             
             if new_height > 0:
                 new_fmt.setHeight(new_height)
             else:
                 new_fmt.setHeight(0) # Let Qt decide (but explicit is better for "disappearing" bugs)
             
             # 6. Merge instead of Set
             # mergeCharFormat is safer as it keeps other properties
             target_cursor.mergeCharFormat(new_fmt)

    def reset_image_size(self, cursor):
        # Select image
        self.setTextCursor(cursor)
        selection_cursor = self.textCursor()
        selection_cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
        
        if not selection_cursor.charFormat().isImageFormat():
             selection_cursor = self.textCursor()
             selection_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
        
        if selection_cursor.charFormat().isImageFormat():
             fmt = selection_cursor.charFormat().toImageFormat()
             fmt.setWidth(0) # 0 means native size in Qt
             fmt.setHeight(0)
             selection_cursor.setCharFormat(fmt)

    def save_image_as(self, cursor):
        from PyQt6.QtWidgets import QFileDialog
        
        fmt = cursor.charFormat().toImageFormat()
        name = fmt.name()
        
        # Retrieve image data
        image = self.document().resource(3, QUrl(name))
        
        if isinstance(image, float): # Sometimes returns garbage if not found?
             return
             
        if image and not image.isNull():
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Image", "image.png", "Images (*.png *.jpg)"
            )
            
            if file_path:
                image.save(file_path)

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
            # Toggle highlight? Or just set yellow.
            if fmt.background().color().name() == "#ffff00":
                fmt.setBackground(Qt.GlobalColor.transparent) # Remove
            else:
                fmt.setBackground(QColor("yellow"))
                fmt.setForeground(QColor("black")) # Text black on yellow
            cursor.mergeCharFormat(fmt)
        
        self.setFocus()
        
    def canInsertFromMimeData(self, source):
        if source.hasImage():
            return True
        return super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage():
            image = source.imageData()
            if image:
                # Convert QImage/QPixmap to Base64 HTML
                # Process: QVariant (image) -> QImage -> QBuffer -> Base64
                from PyQt6.QtCore import QBuffer, QIODevice
                import base64
                
                # Check if it's already a QImage or QPixmap
                if not hasattr(image, "save"):
                     # Try to convert if it's a QVariant wrapping QImage
                     from PyQt6.QtGui import QImage
                     if isinstance(image, QImage):
                         pass
                     else:
                         image = QImage(image)

                ba = QBuffer()
                ba.open(QIODevice.OpenModeFlag.WriteOnly)
                image.save(ba, "PNG")
                base64_data = base64.b64encode(ba.data().data()).decode('utf-8')
                
                html = f'<img src="data:image/png;base64,{base64_data}" />'
                self.insertHtml(html)
                return
                
                
        super().insertFromMimeData(source)

    def insert_image_from_file(self):
        """Open file dialog and insert selected image"""
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import QBuffer, QIODevice
        import base64
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if not file_path:
            return
        
        # Load image
        image = QImage(file_path)
        if image.isNull():
            return
        
        # Convert to base64
        ba = QBuffer()
        ba.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(ba, "PNG")
        base64_data = base64.b64encode(ba.data().data()).decode('utf-8')
        
        # Insert as HTML
        html = f'<img src="data:image/png;base64,{base64_data}" />'
        self.insertHtml(html)


