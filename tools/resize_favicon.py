from PIL import Image
import os

src = "web/public/logo.png"
dst_ico = "web/public/favicon.ico"
dst_png = "web/public/icon-192.png"

try:
    with Image.open(src) as img:
        # Save as ICO (32x32)
        img.resize((32, 32)).save(dst_ico, sizes=[(32, 32)])
        print(f"Created {dst_ico}")

        # Save as PNG (192x192)
        img.resize((192, 192)).save(dst_png)
        print(f"Created {dst_png}")
except Exception as e:
    print(f"Error: {e}")
