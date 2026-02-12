import pytesseract
from PIL import Image
from PyQt6.QtCore import QBuffer, QIODevice
import io

def extract_text_from_pixmap(pixmap):
    """
    Extracts text from a QPixmap using OCR (Tesseract).
    Returns tuple (success: bool, content: str).
    """
    try:
        # Convert QPixmap to PIL Image
        qimage = pixmap.toImage()
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.ReadWrite)
        qimage.save(buffer, "PNG")
        
        image = Image.open(io.BytesIO(buffer.data()))
        
        # Perform OCR
        # Providing specific config can optimize for blocks of text
        # lang='vie+eng' if supported
        # For now default English/detect. User might need Vietnamese pack installed.
        # Assuming lang='eng' default or auto?
        # Let's try 'vie+eng' but fallback if 'vie' not installed.
        # Simple 'image_to_string' uses default eng unless specified.
        
        # Detect installed langs?
        # langs = pytesseract.get_languages() # Might fail
        
        text = pytesseract.image_to_string(image, lang='vie+eng') 
        return True, text.strip()
        
    except pytesseract.TesseractError as e:
        # Fallback to eng only if vie fails?
        try:
             text = pytesseract.image_to_string(image)
             return True, text.strip()
        except Exception:
             return False, f"OCR Error: {e}"
             
    except ImportError:
        return False, "Error: pytesseract/Pillow not installed."
        
    except Exception as e:
        if "FileNotFoundError" in str(e) or "tesseract is not installed" in str(e):
             return False, "Error: Tesseract-OCR not found in PATH."
        return False, f"Error: {e}"
