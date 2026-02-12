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
        
        # 1. Identify valid image cursor
        # cursorForPosition usually places cursor closest to click.
        # We need to find WHICH character is the image (Left or Right of cursor).
        
        target_cursor = None
        img_fmt = None
        
        # Check Right
        c_right = self.textCursor()
        c_right.setPosition(cursor.position())
        c_right.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor)
        if c_right.charFormat().isImageFormat():
            target_cursor = c_right
            img_fmt = c_right.charFormat().toImageFormat()
        
        # Check Left (if Right failed)
        if not target_cursor:
            c_left = self.textCursor()
            c_left.setPosition(cursor.position())
            c_left.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
            if c_left.charFormat().isImageFormat():
                target_cursor = c_left
                img_fmt = c_left.charFormat().toImageFormat()
                
        # If still not found, check the cursor's own charFormat (which is "char before")
        if not target_cursor and cursor.charFormat().isImageFormat():
             # The cursor is AFTER the image
             c_left = self.textCursor()
             c_left.setPosition(cursor.position())
             c_left.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
             target_cursor = c_left
             img_fmt = cursor.charFormat().toImageFormat()

        if not target_cursor or not img_fmt:
            return

        current_width = img_fmt.width()
        current_height = img_fmt.height()
        
        # Load visual image to get aspect ratio if needed
        name = img_fmt.name()
        original_image = self.document().resource(3, QUrl(name))
        
        # If current size is 0/0, use original
        native_width = 0
        native_height = 0
        if original_image and not original_image.isNull():
             native_width = original_image.width()
             native_height = original_image.height()
        
        if current_width <= 0:
             current_width = native_width if native_width > 0 else 300
        
        # Show Dialog
        new_width, ok = QInputDialog.getInt(
            self, "Resize Image", "Enter new width (px):", 
            int(current_width), 10, 2000, 10
        )
        
        if ok:
             # Calculate new height to maintain aspect ratio
             new_height = 0
             if native_width > 0 and native_height > 0:
                  ratio = native_height / native_width
                  new_height = int(new_width * ratio)
             elif current_height > 0 and current_width > 0:
                  ratio = current_height / current_width
                  new_height = int(new_width * ratio)
             
             # Apply
             img_fmt.setWidth(new_width)
             if new_height > 0:
                 img_fmt.setHeight(new_height)
             else:
                 img_fmt.setHeight(0) # Fallback to auto
             
             # Crucial: Ensure name is preserved (it should be in fmt)
             # Apply to document
             target_cursor.setCharFormat(img_fmt)

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


