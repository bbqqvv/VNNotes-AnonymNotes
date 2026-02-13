import os
import zipfile
import xml.etree.ElementTree as ET

class UniversalReader:
    @staticmethod
    def read_file(file_path):
        """Reads content from various file types."""
        if not os.path.exists(file_path):
            return None
            
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == ".docx":
                return UniversalReader._read_docx(file_path)
            elif ext in [".txt", ".md", ".py", ".js", ".html", ".css", ".json", ".xml", ".log", ".bat", ".sh"]:
                return UniversalReader._read_text(file_path)
            else:
                # Try as text for unknown extensions
                return UniversalReader._read_text(file_path)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return f"Error reading file: {str(e)}"

    @staticmethod
    def _read_text(file_path):
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()

    @staticmethod
    def _read_docx(file_path):
        """Extracts text from .docx without python-docx dependency."""
        try:
            with zipfile.ZipFile(file_path) as docx:
                xml_content = docx.read('word/document.xml')
                tree = ET.fromstring(xml_content)
                
                # Namespace map (docx usually uses w string)
                # But we can just iterate all elements and look for <w:t> text tags
                
                passages = []
                
                # Recursive function to find text
                # Actually, simpler: find all 't' tags which contain text
                # The namespace usually is http://schemas.openxmlformats.org/wordprocessingml/2006/main
                
                namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                
                for p in tree.iter():
                    if p.tag.endswith('}p'): # Paragraph
                        para_text = ""
                        for t in p.iter():
                            if t.tag.endswith('}t'): # Text node
                                if t.text:
                                    para_text += t.text
                        if para_text:
                            passages.append(para_text)
                            
                return "\n".join(passages)
                
        except Exception as e:
            return f"Error extracting DOCX: {str(e)}\n(Try installing python-docx for better support)"
