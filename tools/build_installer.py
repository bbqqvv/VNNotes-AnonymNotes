import os
import subprocess
import sys

def make_installer():
    # Detect the correct base directory (parent of tools folder)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dist_dir = os.path.join(base_dir, "dist", "VNNotes")
    iss_file = os.path.join(base_dir, "tools", "vnnotes_installer.iss")
    
    # ── Step 1: Optimize App Bloat ──────────────────────────────────────────
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

    for item in to_remove:
        path = os.path.join(dist_dir, "Resources", item) if "/" in item else os.path.join(dist_dir, item)
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"   [Removed] {item}")
            except Exception as e:
                print(f"   [Warning] Could not remove {item}: {e}")

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

    # ── Step 2: Compile with Inno Setup ─────────────────────────────────────
    print("2. Building Professional Windows Installer via Inno Setup...")
    
    # Attempt to locate ISCC.exe
    iscc_paths = [
        r"D:\ProgramUtil\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe"
    ]
    
    iscc_exe = None
    for path in iscc_paths:
        if os.path.exists(path):
            iscc_exe = path
            break
            
    if not iscc_exe:
        print("[ERROR] Inno Setup Compiler (ISCC.exe) not found.")
        print("Please install Inno Setup from: https://jrsoftware.org/isdl.php")
        sys.exit(1)
        
    print(f"   Found ISCC at: {iscc_exe}")
    
    # Cast iscc_exe to string to satisfy type checker
    cmd = [str(iscc_exe), iss_file]
    
    try:
        subprocess.check_call(cmd, cwd=os.path.join(base_dir, "tools"))
        print("\nDONE! Professional Installer is ready in: dist/VNNotes_Setup.exe")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Inno Setup compilation failed with code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    make_installer()
