import sys
from PyQt6.QtWidgets import QApplication, QTextEdit
from PyQt6.QtGui import QTextDocument
import mammoth
import os

def check_mammoth_output(docx_path):
    if not os.path.exists(docx_path):
        print(f"File {docx_path} not found")
        return
        
    with open(docx_path, "rb") as f:
        result = mammoth.convert_to_html(f)
        html = result.value
        print(f"HTML Output length: {len(html)}")
        if "data:image" in html:
            print("Found base64 image in HTML")
            # Print a snippet of the img tag
            idx = html.find("<img")
            print(f"Img tag: {html[idx:idx+200]}...")
        else:
            print("No images found in HTML output")

if __name__ == "__main__":
    # We need a real docx for this test if possible, or I'll just check code
    print("Testing base64 support in QTextEdit...")
    app = QApplication(sys.argv)
    te = QTextEdit()
    # Tiny 1x1 red dot png base64
    base64_img = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    html_test = f"<p>Image test:</p><img src=\"data:image/png;base64,{base64_img}\" />"
    te.setHtml(html_test)
    
    # Check if document has the image
    doc = te.document()
    # This is tricky to check programmatically without a GUI, 
    # but we can check if it loaded into resources? 
    # Actually, QTextEdit doesn't automatically add data URIs to resources.
    
    print("Done testing.")
