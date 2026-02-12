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
        self.title("Stealth Assist Setup")
        self.geometry("600x400")
        self.resizable(False, False)
        self.configure(bg="white")
        
        self.install_dir = os.path.join(os.environ['LOCALAPPDATA'], "StealthAssist")
        self.zip_path = self.resource_path("data.zip")
        self.logo_path = self.resource_path("appnote.png")
        
        self.frames = {}
        self.current_frame = None

        self.setup_ui()
        self.show_frame("Welcome")

    def resource_path(self, relative_path):
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def setup_ui(self):
        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="white")
        style.configure("TLabel", background="white", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="white", font=("Segoe UI", 14, "bold"), foreground="#2c3e50")
        style.configure("TButton", padding=6)
        
        # Sidebar with Logo
        sidebar = tk.Frame(self, bg="#2c3e50", width=160)
        sidebar.pack(side="left", fill="y")
        
        try:
            from PIL import Image, ImageTk
            img = Image.open(self.logo_path)
            img = img.resize((100, 100), Image.Resampling.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
            logo_label = tk.Label(sidebar, image=self.logo_img, bg="#2c3e50")
            logo_label.pack(pady=40)
        except Exception as e:
            print(f"Error loading logo: {e}")
            tk.Label(sidebar, text="Stealth\nAssist", fg="white", bg="#2c3e50", font=("Segoe UI", 16, "bold")).pack(pady=40)
        
        container = tk.Frame(self, bg="white")
        container.pack(side="right", fill="both", expand=True, padx=30, pady=20)

        # Header Logo (small top right)
        try:
            h_img = Image.open(self.logo_path)
            h_img = h_img.resize((30, 30), Image.Resampling.LANCZOS)
            self.header_logo_img = ImageTk.PhotoImage(h_img)
            h_label = tk.Label(container, image=self.header_logo_img, bg="white")
            h_label.place(relx=1.0, rely=0.0, anchor="ne")
        except:
             pass
        
        # Frame 1: Welcome
        f1 = tk.Frame(container, bg="white")
        tk.Label(f1, text="Welcome to Stealth Assist Setup", font=("Segoe UI", 16, "bold"), bg="white", fg="#2c3e50").pack(anchor="w", pady=(0, 20))
        tk.Label(f1, text="This wizard will install Stealth Assist v1.0 on your computer.", bg="white", wraplength=350, justify="left").pack(anchor="w")
        tk.Label(f1, text="\nStealth Assist is ultra-lightweight and hidden from screen capture software, ensuring your notes stay private.", bg="white", wraplength=350, justify="left").pack(anchor="w")
        self.frames["Welcome"] = f1
        
        # Frame 2: Select Location
        f2 = tk.Frame(container, bg="white")
        tk.Label(f2, text="Installation Folder", font=("Segoe UI", 14, "bold"), bg="white", fg="#2c3e50").pack(anchor="w", pady=(0, 20))
        tk.Label(f2, text="Confirm the installation path below:", bg="white").pack(anchor="w")
        
        path_frame = tk.Frame(f2, bg="white")
        path_frame.pack(fill="x", pady=10)
        self.path_entry = ttk.Entry(path_frame)
        self.path_entry.insert(0, self.install_dir)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(path_frame, text="Browse...", command=self.browse_folder).pack(side="right")
        
        tk.Label(f2, text="Required space: 600 MB", bg="white", fg="#7f8c8d").pack(anchor="w", pady=10)
        self.frames["Location"] = f2
        
        # Frame 3: Installing
        f3 = tk.Frame(container, bg="white")
        tk.Label(f3, text="Installing Stealth Assist", font=("Segoe UI", 14, "bold"), bg="white", fg="#2c3e50").pack(anchor="w", pady=(0, 20))
        self.status_label = tk.Label(f3, text="Extracting components...", bg="white")
        self.status_label.pack(anchor="w")
        self.progress = ttk.Progressbar(f3, mode="determinate")
        self.progress.pack(fill="x", pady=10)
        self.frames["Installing"] = f3
        
        # Frame 4: Finished
        f4 = tk.Frame(container, bg="white")
        tk.Label(f4, text="Installation Complete", font=("Segoe UI", 16, "bold"), bg="white", fg="#2c3e50").pack(anchor="w", pady=(0, 20))
        tk.Label(f4, text="Stealth Assist has been successfully installed.", bg="white").pack(anchor="w")
        self.chk_shortcut = tk.IntVar(value=1)
        tk.Checkbutton(f4, text="Create Desktop Shortcut", variable=self.chk_shortcut, bg="white").pack(anchor="w", pady=10)
        self.chk_launch = tk.IntVar(value=1)
        tk.Checkbutton(f4, text="Launch Stealth Assist now", variable=self.chk_launch, bg="white").pack(anchor="w")
        self.frames["Finished"] = f4

        # Navigation Buttons (Bottom Right)
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        
        self.btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        self.btn_cancel.pack(side="right", padx=(5, 0))
        
        self.btn_next = ttk.Button(btn_frame, text="Next >", command=self.go_next)
        self.btn_next.pack(side="right", padx=(5, 0))
        
        self.btn_back = ttk.Button(btn_frame, text="< Back", command=self.go_back)
        self.btn_back.pack(side="right")

    def show_frame(self, name):
        if self.current_frame:
            self.current_frame.pack_forget()
        self.current_frame = self.frames[name]
        self.current_frame.pack(fill="both", expand=True)
        self.current_step = name
        
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
