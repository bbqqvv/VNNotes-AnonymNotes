import logging
import re
import base64
import os
from PyQt6.QtWidgets import QInputDialog, QFileDialog
from PyQt6.QtGui import QTextCursor, QImage, QTextCharFormat, QTextImageFormat
from PyQt6.QtCore import Qt, QUrl, QRect, QBuffer, QIODevice

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.features.notes.note_pane import NotePane

class NoteImageManager:
    """
    Component to manage image-related operations for NotePane.
    Extracts complex spatial logic and resource management from the main editor.
    """
    def __init__(self, editor: "NoteEditor"):
        self.editor = editor
        self.doc = editor.document()

    def get_image_at_cursor(self, cursor, pos=None):
        """
        Robustly identifies and selects the image character at or near the cursor.
        Returns a QTextCursor with the image selected, or None.
        """
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
                    
                    tl_cursor = QTextCursor(self.doc)
                    tl_cursor.setPosition(fragment.position())
                    top_left_rect = self.editor.cursorRect(tl_cursor)
                    tl = top_left_rect.topLeft()
                    
                    w = fmt.width()
                    h = fmt.height()
                    
                    # If the image format has no explicit size (never been resized),
                    # fall back to the native image dimensions from the document resource.
                    # Without this, image_rect = QRect(x, y, 0, 0) which never
                    # contains any click point â†’ context menu never shows image options.
                    if w <= 0 or h <= 0:
                        native_img = self.doc.resource(3, QUrl(fmt.name()))
                        if native_img and not native_img.isNull():
                            w = native_img.width()
                            h = native_img.height()
                        else:
                            # Last resort: use a generous detection area so the user
                            # can still right-click anywhere in the vicinity.
                            w = 300
                            h = 300
                    
                    image_rect = QRect(tl.x(), tl.y(), int(w), int(h))
                    
                    if pos:
                        if image_rect.adjusted(-5, -5, 5, 5).contains(pos):
                            img_cursor = QTextCursor(self.doc)
                            img_cursor.setPosition(fragment.position())
                            img_cursor.movePosition(QTextCursor.MoveOperation.Right, 
                                                   QTextCursor.MoveMode.KeepAnchor, 
                                                   fragment.length())
                            return img_cursor
                    else:
                        img_cursor = QTextCursor(self.doc)
                        img_cursor.setPosition(fragment.position())
                        img_cursor.movePosition(QTextCursor.MoveOperation.Right, 
                                               QTextCursor.MoveMode.KeepAnchor, 
                                               fragment.length())
                        return img_cursor
                it += 1
                 
        return None


    def resize_image_dialog(self, cursor):
        """Standardizes image resizing with native ratio support.
        
        `cursor` may be a pre-resolved img_cursor (from context menu) that
        already has the image selected, or a plain text cursor for fallback lookup.
        """
        # If cursor already has an image format selected, use it directly.
        # Otherwise, try to locate the image near the cursor position.
        if cursor.hasSelection() and cursor.charFormat().isImageFormat():
            img_cursor = cursor
        else:
            img_cursor = self.get_image_at_cursor(cursor)
        if not img_cursor:
            return
            
        target_fmt = img_cursor.charFormat().toImageFormat()
        name = target_fmt.name()
        image_res = self.doc.resource(3, QUrl(name))
        
        native_w = image_res.width() if image_res and not image_res.isNull() else 0
        native_h = image_res.height() if image_res and not image_res.isNull() else 0
        
        current_w = target_fmt.width()
        if current_w <= 0: current_w = native_w if native_w > 0 else 300
        
        new_width, ok = QInputDialog.getInt(self.editor, "Resize Image", 
                                           f"Enter width (Native: {native_w}px):", 
                                           int(current_w), 10, 3000, 10)
        
        if ok and new_width > 0:
            new_height = 0
            if native_w > 0:
                new_height = int(new_width * (native_h / native_w))
            
            new_fmt = target_fmt
            new_fmt.setWidth(new_width)
            if new_height > 0:
                new_fmt.setHeight(new_height)
            
            img_cursor.setCharFormat(new_fmt)
            self.editor.setFocus()

    def reset_image_size(self, cursor):
        """Reset image to native size. Accepts pre-resolved img_cursor or plain cursor."""
        if cursor.hasSelection() and cursor.charFormat().isImageFormat():
            img_cursor = cursor
        else:
            img_cursor = self.get_image_at_cursor(cursor)
        if img_cursor:
             fmt = img_cursor.charFormat().toImageFormat()
             fmt.setWidth(0)
             fmt.setHeight(0)
             img_cursor.setCharFormat(fmt)
             self.editor.setFocus()

    def save_image_as(self, cursor):
        """Save image to file. Accepts pre-resolved img_cursor or plain cursor."""
        if cursor.hasSelection() and cursor.charFormat().isImageFormat():
            img_cursor = cursor
        else:
            img_cursor = self.get_image_at_cursor(cursor)
        if not img_cursor:
            return
            
        fmt = img_cursor.charFormat().toImageFormat()
        name = fmt.name()
        image = self.doc.resource(3, QUrl(name))
        if image and not image.isNull():
            file_path, _ = QFileDialog.getSaveFileName(self.editor, "Save Image", "image.png", "Images (*.png *.jpg)")
            if file_path: image.save(file_path)

    def image_to_base64(self, image):
        """Converts QImage to Base64 string."""
        ba = QBuffer()
        ba.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(ba, "PNG")
        return base64.b64encode(ba.data().data()).decode('utf-8')

    def process_html_for_insertion(self, html):
        """Processes HTML by extracting base64 images and adding them as document resources."""
        # Find base64 image tags
        pattern = r'src=["\']data:image/(?P<ext>[^;]+);base64,(?P<data>[^"\']+)["\']'
        index_wrapper = [0] # Use list for closure mutability
        
        # Clean up existing style/size constraints to allow editor to control them
        html = re.sub(r'(<img[^>]+)style=["\'][^"\']*["\']', r'\1', html)
        html = re.sub(r'(<img[^>]+)width=["\'][^"\']*["\']', r'\1', html)
        html = re.sub(r'(<img[^>]+)height=["\'][^"\']*["\']', r'\1', html)
        
        # Add default style from registry
        from src.ui.style_registry import StyleRegistry
        # We assume border color comes from theme if we had direct access, 
        # but for now we use the template's default or a fallback
        img_style = StyleRegistry.IMAGE_DEFAULT_STYLE.format(border="#27272a")
        html = html.replace("<img ", f"<img style='{img_style}' ")

        def replace_match(match):
            ext = match.group('ext')
            data_b64 = match.group('data')
            try:
                img_data = base64.b64decode(data_b64)
                image = QImage.fromData(img_data)
                if not image.isNull():
                    res_name = f"img_{index_wrapper[0]}.{ext}"
                    self.doc.addResource(3, QUrl(res_name), image)
                    index_wrapper[0] += 1
                    return f'src="{res_name}"'
            except Exception as e:
                logging.error(f"Failed to process embedded image: {e}")
            return match.group(0)

        return re.sub(pattern, replace_match, html)

    def get_html_with_base64(self, html):
        """Converts internal resource images back to base64 for saving."""
        def replace_src(match):
            src = match.group(1)
            if any(p in src for p in ["img_", "word_img_", "qrc:/"]):
                 image = self.doc.resource(3, QUrl(src))
                 if image and not image.isNull():
                     b64_data = self.image_to_base64(image)
                     return f'src="data:image/png;base64,{b64_data}"'
            return match.group(0)

        pattern = r'src="([^"]+)"'
        return re.sub(pattern, replace_src, html)
