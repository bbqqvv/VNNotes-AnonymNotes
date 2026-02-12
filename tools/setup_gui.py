import os
import sys
import zipfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
import winshell
from win32com.client import Dispatch

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Stealth Assist Installer")
        self.geometry("500x350")
        self.resizable(False, False)
        
        # Icon
        # try:
        #     self.iconbitmap(self.resource_path("appnote.ico"))
        # except:
        #     pass

        self.install_dir = os.path.join(os.environ['LOCALAPPDATA'], "StealthAssist")
        self.zip_path = self.resource_path("data.zip")
        
        self.frames = {}
        self.current_frame = None

        self.setup_ui()
        self.show_frame("Welcome")

    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def setup_ui(self):
        # Styles
        style = ttk.Style()
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
        
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Frame 1: Welcome
        f1 = ttk.Frame(container)
        lbl = ttk.Label(f1, text="Welcome to Stealth Assist Setup", style="Header.TLabel")
        lbl.pack(pady=(0, 20))
        ttk.Label(f1, text="This wizard will install Stealth Assist on your computer.").pack(anchor="w")
        ttk.Label(f1, text="\nClick Next to continue, or Cancel to exit Setup.").pack(anchor="w")
        self.frames["Welcome"] = f1
        
        # Frame 2: Select Location
        f2 = ttk.Frame(container)
        ttk.Label(f2, text="Select Installation Folder", style="Header.TLabel").pack(pady=(0, 20))
        ttk.Label(f2, text="Where should Stealth Assist be installed?").pack(anchor="w")
        
        path_frame = ttk.Frame(f2)
        path_frame.pack(fill="x", pady=10)
        self.path_entry = ttk.Entry(path_frame)
        self.path_entry.insert(0, self.install_dir)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(path_frame, text="Browse...", command=self.browse_folder).pack(side="right")
        
        ttk.Label(f2, text="At least 600 MB of free disk space is required.").pack(anchor="w", pady=10)
        self.frames["Location"] = f2
        
        # Frame 3: Installing
        f3 = ttk.Frame(container)
        ttk.Label(f3, text="Installing...", style="Header.TLabel").pack(pady=(0, 20))
        self.status_label = ttk.Label(f3, text="Preparing...")
        self.status_label.pack(anchor="w")
        self.progress = ttk.Progressbar(f3, mode="determinate")
        self.progress.pack(fill="x", pady=10)
        self.frames["Installing"] = f3
        
        # Frame 4: Finished
        f4 = ttk.Frame(container)
        ttk.Label(f4, text="Installation Complete", style="Header.TLabel").pack(pady=(0, 20))
        ttk.Label(f4, text="Stealth Assist has been installed on your computer.").pack(anchor="w")
        self.chk_shortcut = tk.IntVar(value=1)
        ttk.Checkbutton(f4, text="Create Desktop Shortcut", variable=self.chk_shortcut).pack(anchor="w", pady=10)
        self.chk_launch = tk.IntVar(value=1)
        ttk.Checkbutton(f4, text="Launch Stealth Assist", variable=self.chk_launch).pack(anchor="w")
        self.frames["Finished"] = f4

        # Navigation Buttons (Bottom)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", side="bottom", padx=20, pady=20)
        
        self.btn_back = ttk.Button(btn_frame, text="< Back", command=self.go_back)
        self.btn_back.pack(side="left")
        
        self.btn_next = ttk.Button(btn_frame, text="Next >", command=self.go_next)
        self.btn_next.pack(side="right")
        
        self.btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        self.btn_cancel.pack(side="right", padx=(0, 10))

    def show_frame(self, name):
        if self.current_frame:
            self.current_frame.pack_forget()
        self.current_frame = self.frames[name]
        self.current_frame.pack(fill="both", expand=True)
        self.current_step = name
        
        # Update Buttons
        if name == "Welcome":
            self.btn_back.state(["disabled"])
            self.btn_next.state(["!disabled"])
            self.btn_next.config(text="Next >", command=self.go_next)
        elif name == "Location":
            self.btn_back.state(["!disabled"])
            self.btn_next.state(["!disabled"])
            self.btn_next.config(text="Install", command=self.start_install)
        elif name == "Installing":
            self.btn_back.state(["disabled"])
            self.btn_next.state(["disabled"])
            self.btn_cancel.state(["disabled"])
        elif name == "Finished":
            self.btn_back.pack_forget()
            self.btn_cancel.pack_forget()
            self.btn_next.state(["!disabled"])
            self.btn_next.config(text="Finish", command=self.finish)

    def browse_folder(self):
        d = filedialog.askdirectory(initialdir=self.install_dir)
        if d:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, d)

    def go_back(self):
        if self.current_step == "Location":
            self.show_frame("Welcome")

    def go_next(self):
        if self.current_step == "Welcome":
            self.show_frame("Location")
            
    def start_install(self):
        self.install_dir = self.path_entry.get()
        self.show_frame("Installing")
        threading.Thread(target=self.run_install, daemon=True).start()

    def run_install(self):
        try:
            # 1. Clean old
            if os.path.exists(self.install_dir):
                self.status_label.config(text="Cleaning old version...")
                shutil.rmtree(self.install_dir, ignore_errors=True)
            
            os.makedirs(self.install_dir, exist_ok=True)
            
            # 2. Extract
            self.status_label.config(text="Extracting files...")
            
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                files = zf.namelist()
                total = len(files)
                for i, file in enumerate(files):
                    zf.extract(file, self.install_dir)
                    
                    if i % 10 == 0: # Update UI
                        pct = (i / total) * 100
                        self.progress['value'] = pct
                        self.update_idletasks()
                        
            self.progress['value'] = 100
            self.status_label.config(text="Done!")
            self.after(500, lambda: self.show_frame("Finished"))
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.destroy()

    def finish(self):
        exe_path = os.path.join(self.install_dir, "StealthAssist.exe") # Adjust depending on zip structure
        # If zip structure is dist/StealthAssist/..., creating installer might need to account for root folder
        # I'll ensure zip is content only or handle it.
        
        # Check zip root
        if not os.path.exists(exe_path):
             # Maybe nested in StealthAssist subdirectory
             nested = os.path.join(self.install_dir, "StealthAssist", "StealthAssist.exe")
             if os.path.exists(nested):
                 exe_path = nested
                 self.install_dir = os.path.join(self.install_dir, "StealthAssist")
        
        if self.chk_shortcut.get():
            try:
                desktop = winshell.desktop()
                path = os.path.join(desktop, "Stealth Assist.lnk")
                shell = Dispatch('WScript.Shell')
                shortcut = shell.CreateShortcut(path)
                shortcut.TargetPath = exe_path
                shortcut.WorkingDirectory = self.install_dir
                shortcut.IconLocation = exe_path
                shortcut.Save()
            except Exception as e:
                print(e)
                
        if self.chk_launch.get():
            os.startfile(exe_path)
            
        self.destroy()

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
