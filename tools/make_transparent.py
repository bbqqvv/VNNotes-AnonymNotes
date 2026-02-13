from PIL import Image
import os

def remove_white_bg(input_path, output_path):
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()

    new_data = []
    threshold = 240 # Adjust for "near white"
    
    for item in datas:
        # Check if pixel is white-ish
        if item[0] > threshold and item[1] > threshold and item[2] > threshold:
            new_data.append((255, 255, 255, 0)) # Make transparent
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Saved transparent image to: {output_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src_icon = os.path.join(base_dir, "logo.png")
    dst_icon = os.path.join(base_dir, "logo_transparent.png")
    
    remove_white_bg(src_icon, dst_icon)
