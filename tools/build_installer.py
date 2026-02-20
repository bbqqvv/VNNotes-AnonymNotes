import os
import shutil
import subprocess

def make_installer():
    # Detect the correct base directory (parent of tools folder)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dist_dir = os.path.join(base_dir, "dist/VNNotes")
    output_7z = os.path.join(base_dir, "tools/data.7z")
    installer_script = os.path.join(base_dir, "tools/setup_gui.py")
    app_image = os.path.join(base_dir, "appnote.png")
    license_file = os.path.join(base_dir, "LICENSE")
    
    print("1. Optimizing App Bloat (Controlled Pruning)...")
    to_remove = [
        "PyQt6/Qt6/resources/qtwebengine_devtools_resources.debug.pak",
        "PyQt6/Qt6/resources/qtwebengine_resources.debug.pak",
        "PyQt6/Qt6/resources/qtwebengine_resources_100p.debug.pak",
        "PyQt6/Qt6/resources/qtwebengine_resources_200p.debug.pak",
        "PyQt6/Qt6/resources/v8_context_snapshot.debug.bin",
        "PyQt6/Qt6/resources/qtwebengine_resources_200p.pak",
        "PyQt6/Qt6/resources/qtwebengine_devtools_resources.pak", 
        "debug.log",
    ]

    # Locales pruning (Safe)
    print("   Pruning locales (keeping only essential en-US)...")
    locales_paths = [
        os.path.join(dist_dir, "Resources", "PyQt6/Qt6/translations/qtwebengine_locales"),
        os.path.join(dist_dir, "Resources", "PyQt6/Qt6/translations/qtwebengine_locales.debug")
    ]
    for locales_dir in locales_paths:
        if os.path.exists(locales_dir):
            for f in os.listdir(locales_dir):
                if not (f.startswith("en-") and f.endswith(".pak")):
                    try: os.remove(os.path.join(locales_dir, f))
                    except: pass

    print("2. 7z Compression (LZMA2 - God Mode)...")
    if os.path.exists(output_7z):
        os.remove(output_7z)
        
    import py7zr
    with py7zr.SevenZipFile(output_7z, 'w') as archive:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Ensure the arcname is relative to dist_dir
                arcname = os.path.relpath(file_path, dist_dir)
                archive.write(file_path, arcname)
                
    print(f"   7z created: {output_7z}")
    
    print("3. Building Installer EXE...")
    import sys
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--optimize", "2",
        "--name", "VNNotes_Setup",
        "--icon", app_image, # Use app icon for installer
        "--add-data", f"{output_7z};.",
        "--add-data", f"{app_image};.", # Include image for installer UI
        "--add-data", f"{license_file};.", # Include License in installer
        "--clean",
        "--noconfirm",
        "--version-file", "file_version_info_setup.txt",
        installer_script
    ]
    
    subprocess.check_call(cmd, cwd=os.path.join(base_dir, "tools"))
    print("DONE! Installer is in tools/dist/VNNotes_Setup.exe")

if __name__ == "__main__":
    make_installer()
