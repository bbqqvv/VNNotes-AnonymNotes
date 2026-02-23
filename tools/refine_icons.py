import os
import re

def refine_svgs():
    """
    Refines all SVG icons in assets/icons by:
    1. Reducing stroke-width from 2 to 1.5 for a lighter feel.
    2. Changing pure black (#000000) to a softer gray (#37474f) in light theme.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    icons_dir = os.path.normpath(os.path.join(project_root, "assets", "icons"))

    if not os.path.exists(icons_dir):
        print(f"Error: Icons directory not found: {icons_dir}")
        return

    print(f"Refining icons in: {icons_dir}")
    print("-" * 50)

    count = 0
    errors = 0

    for root, dirs, files in os.walk(icons_dir):
        for file in files:
            if file.endswith(".svg"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    original_content = content

                    # 1. Reduce stroke-width
                    content = content.replace('stroke-width="2"', 'stroke-width="1.5"')
                    
                    # 2. Soften colors in light theme
                    if "light_theme" in root or "light_theme" in file_path:
                        # Replace pure black with softer gray
                        content = content.replace('stroke="#000000"', 'stroke="#37474f"')
                    
                    if content != original_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        count += 1
                        print(f"  Refined: {os.path.relpath(file_path, icons_dir)}")
                except Exception as e:
                    print(f"  Error processing {file}: {e}")
                    errors += 1

    print("-" * 50)
    print(f"Successfully refined {count} icons.")
    if errors:
        print(f"Encountered {errors} errors.")

if __name__ == "__main__":
    refine_svgs()
