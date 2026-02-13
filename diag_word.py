import sys
import os
import traceback

# Add src to path
sys.path.append(os.getcwd())

try:
    from src.core.reader import UniversalReader
    import docx
    print(f"DEBUG: python-docx version: {docx.__version__}")
    
    # Check if we can instantiate a Document
    test_doc_path = "test_word_support.docx"
    from docx import Document
    doc = Document()
    doc.add_paragraph("Hello VNNotes")
    doc.save(test_doc_path)
    print(f"DEBUG: Created test file: {test_doc_path}")
    
    content = UniversalReader.read_file(test_doc_path)
    print(f"DEBUG: Read result: '{content}'")
    
    # Cleanup
    if os.path.exists(test_doc_path):
        os.remove(test_doc_path)
        
except Exception as e:
    print("DEBUG: CRASH DURING TEST")
    traceback.print_exc()
