from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSize
import sys
import os

app = QApplication(sys.argv)

icon_path = "assets/icons/light_theme/note.svg"
if not os.path.exists(icon_path):
    print(f"File not found: {icon_path}")
    sys.exit(1)

icon = QIcon(icon_path)
pixmap = icon.pixmap(QSize(32, 32))

print(f"Icon isNull: {icon.isNull()}")
print(f"Pixmap isNull: {pixmap.isNull()}")

if pixmap.isNull():
    print("SVG Load Failed! QtSvg plugin might be missing.")
else:
    print("SVG Load Success!")
