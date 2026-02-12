from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QFont, QTextListFormat, QTextCursor
from PyQt6.QtCore import pyqtSignal, Qt

class NotePane(QTextEdit):
    focus_received = pyqtSignal(object) # Signal to notify main window of focus

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type notes here... (Paste images supported)")
        self.setMouseTracking(True) 
        self.viewport().setMouseTracking(True) # Important for QTextEdit
        self.resizing_image = False
        self.resize_start_pos = None
        self.resize_orig_size = None
        self.resize_cursor = None
        
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

    def mouseMoveEvent(self, event):
        # 1. Handle Resizing
        if self.resizing_image and self.resize_cursor:
            delta = event.pos() - self.resize_start_pos
            # Calculate new size
            new_width = max(10, self.resize_orig_size.width() + delta.x())
            
            # Update Image Format
            fmt = self.resize_cursor.charFormat().toImageFormat()
            fmt.setWidth(new_width)
            fmt.setHeight(0) 
            
            self.resize_cursor.setCharFormat(fmt)
            return

        # 2. Handle Hover (Cursor Change)
        cursor = self.cursorForPosition(event.pos())
        fmt = cursor.charFormat()
        
        if fmt.isImageFormat():
            # Get Rect of the image
            rect = self.cursorRect(cursor)
            # Check if near bottom-right
            bn_right = rect.bottomRight()
            dist = (bn_right - event.pos()).manhattanLength()
            
            if dist < 30:
                 self.viewport().setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                 self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
            
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 1. Check for Checkbox Click
            cursor = self.cursorForPosition(event.pos())
            # Select the character after the cursor position
            cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.KeepAnchor)
            char = cursor.selectedText()
            
            if char in ["☐", "☑"]:
                # Toggle
                new_char = "☑" if char == "☐" else "☐"
                cursor.insertText(new_char)
                return # Consume event
                
            # 2. Check for Image Resize Start
            cursor = self.cursorForPosition(event.pos()) # Reset cursor
            fmt = cursor.charFormat()
            if fmt.isImageFormat():
                 rect = self.cursorRect(cursor)
                 bn_right = rect.bottomRight()
                 if (bn_right - event.pos()).manhattanLength() < 30:
                     self.resizing_image = True
                     self.resize_start_pos = event.pos()
                     
                     # Select the image so setCharFormat applies to it
                     # Cursor is after the image (since hitting bottom-right)
                     selection_cursor = QTextCursor(cursor)
                     selection_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor)
                     self.resize_cursor = selection_cursor
                     
                     img_fmt = fmt.toImageFormat()
                     self.resize_orig_size = rect.size()
                     return # Consume event

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing_image:
            self.resizing_image = False
            self.resize_cursor = None
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
            return
            
        super().mouseReleaseEvent(event)

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


