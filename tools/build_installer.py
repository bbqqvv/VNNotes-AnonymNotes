import os
import shutil
import zipfile
import subprocess

def make_installer():
    base_dir = "d:/Workspace/Tool/TH/StealthAssist"
    dist_dir = os.path.join(base_dir, "dist/VNNotes")
    output_zip = os.path.join(base_dir, "tools/data.zip")
    installer_script = os.path.join(base_dir, "tools/setup_gui.py")
    app_image = os.path.join(base_dir, "appnote.png")
    license_file = os.path.join(base_dir, "LICENSE")
    
    print("1. Optimizing App Bloat (Removing debug resources)...")
    # Exclusion list: files we don't need
    to_remove = [
        "PyQt6/Qt6/resources/qtwebengine_devtools_resources.debug.pak",
        "PyQt6/Qt6/resources/qtwebengine_resources.debug.pak",
        "PyQt6/Qt6/resources/qtwebengine_resources_100p.debug.pak",
        "PyQt6/Qt6/resources/qtwebengine_resources_200p.debug.pak",
        "PyQt6/Qt6/resources/v8_context_snapshot.debug.bin",
        "PyQt6/translations", 
    ]
    
    for relative_path in to_remove:
        path = os.path.join(dist_dir, "libs", relative_path)
        if os.path.exists(path):
            print(f"   Removing: {relative_path}")
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
    
    print("2. Zipping Application...")
    if os.path.exists(output_zip):
        os.remove(output_zip)
        
    shutil.make_archive(output_zip.replace(".zip", ""), 'zip', dist_dir)
    print(f"   Zip created: {output_zip}")
    
    print("3. Building Installer EXE...")
    cmd = [
        "py", "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "VNNotes_Setup",
        "--icon", app_image, # Use app icon for installer
        "--add-data", f"{output_zip};.",
        "--add-data", f"{app_image};.", # Include image for installer UI
        "--add-data", f"{license_file};.", # Include License in installer
        "--clean",
        "--noconfirm",
        installer_script
    ]
    
    subprocess.check_call(cmd, cwd=os.path.join(base_dir, "tools"))
    print("DONE! Installer is in tools/dist/VNNotes_Setup.exe")

if __name__ == "__main__":
    make_installer()
