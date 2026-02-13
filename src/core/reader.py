import os
import zipfile
import xml.etree.ElementTree as ET

try:
    import mammoth
except ImportError:
    mammoth = None

try:
    import docx
except ImportError:
    docx = None

class UniversalReader:
    @staticmethod
    def read_file(file_path):
        """Reads content and returns it. For docx, it might return HTML."""
        if not os.path.exists(file_path):
            return None
            
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == ".docx":
                return UniversalReader._read_docx(file_path)
            elif ext in [".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".log", ".bat", ".sh"]:
                content = UniversalReader._read_text(file_path)
                return content.replace("\n", "<br>") # Convert newlines for NotePane
            else:
                # Try as text for unknown extensions
                content = UniversalReader._read_text(file_path)
                return content.replace("\n", "<br>")
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return f"Error reading file: {str(e)}"

    @staticmethod
    def _read_text(file_path):
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    @staticmethod
    def _read_docx(file_path):
        """Extracts content from .docx using mammoth (HTML) with dual fallbacks."""
        # 1. Best: Mammoth (Handles images and formatting)
        if mammoth:
            try:
                with open(file_path, "rb") as docx_file:
                    result = mammoth.convert_to_html(docx_file)
                    # mammoth returns a Result object with 'value' as HTML
                    return result.value
            except Exception as e:
                print(f"Mammoth error: {e}, falling back to python-docx...")

        # 2. Better: python-docx (Handles paragraphs well)
        if docx:
            try:
                doc = docx.Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                return text.replace("\n", "<br>")
            except Exception as e:
                print(f"python-docx error: {e}, falling back to manual parser...")
                
        # 3. Last Resort: Manual XML Extraction
        try:
            with zipfile.ZipFile(file_path) as docx_zip:
                xml_content = docx_zip.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                passages = []
                for p in tree.iter():
                    if p.tag.endswith('}p'):
                        para_text = ""
                        for t in p.iter():
                            if t.tag.endswith('}t'):
                                if t.text: para_text += t.text
                        if para_text: passages.append(para_text)
                return "<br>".join(passages)
        except Exception as e:
            return f"Error extracting DOCX: {str(e)}<br>(Install mammoth for best results)"
