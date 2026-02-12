from PyQt6.QtWidgets import QApplication, QWidget, QLabel
import sys

app = QApplication(sys.argv)
w = QWidget()
w.setWindowTitle("Test")
l = QLabel("Hello", w)
w.show()
print("Displayed")
sys.exit(app.exec())
