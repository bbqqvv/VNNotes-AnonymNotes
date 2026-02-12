import os
import shutil
import zipfile
import subprocess

def make_installer():
    base_dir = "d:/Workspace/Tool/TH/StealthAssist"
    dist_dir = os.path.join(base_dir, "dist/StealthAssist")
    output_zip = os.path.join(base_dir, "tools/data.zip")
    installer_script = os.path.join(base_dir, "tools/setup_gui.py")
    
    print("1. Zipping Application...")
    if os.path.exists(output_zip):
        os.remove(output_zip)
        
    shutil.make_archive(output_zip.replace(".zip", ""), 'zip', dist_dir)
    print(f"   Zip created: {output_zip}")
    
    print("2. Building Installer EXE...")
    cmd = [
        "py", "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "StealthAssist_Setup",
        f"--add-data", f"{output_zip};.",
        "--clean",
        "--noconfirm",
        installer_script
    ]
    
    subprocess.check_call(cmd, cwd=os.path.join(base_dir, "tools"))
    print("DONE! Installer is in tools/dist/StealthAssist_Setup.exe")

if __name__ == "__main__":
    make_installer()
