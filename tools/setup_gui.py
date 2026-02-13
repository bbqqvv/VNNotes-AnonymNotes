import os
import sys
import zipfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shutil
import winshell
from win32com.client import Dispatch
from PIL import Image, ImageTk

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VNNotes Setup")
        self.geometry("640x480")
        self.resizable(False, False)
        self.configure(bg="#f8f9fa")
        
        # Paths
        self.install_dir = os.path.join(os.environ['LOCALAPPDATA'], "VNNotes")
        self.zip_path = self.resource_path("data.zip")
        self.logo_path = self.resource_path("appnote.png")
        self.license_text = """MIT License

Copyright (c) 2026 VTech Digital Solution

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

        self.frames = {}
        self.current_frame = None
        self.accepted_license = tk.BooleanVar(value=False)

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
        style.configure("TFrame", background="#f8f9fa")
        style.configure("TLabel", background="#f8f9fa", font=("Segoe UI", 10))
        style.configure("Header.TLabel", background="#f8f9fa", font=("Segoe UI", 16, "bold"), foreground="#1a1a1a")
        style.configure("TButton", padding=6)
        
        # Layout: Sidebar & Content
        self.sidebar = tk.Frame(self, bg="#0f172a", width=180)
        self.sidebar.pack(side="left", fill="y")
        
        # Content Container
        self.container = tk.Frame(self, bg="#f8f9fa")
        self.container.pack(side="right", fill="both", expand=True, padx=40, pady=30)

        # Sidebar Logo
        try:
            img = Image.open(self.logo_path)
            img = img.resize((120, 120), Image.Resampling.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
            logo_label = tk.Label(self.sidebar, image=self.logo_img, bg="#0f172a")
            logo_label.pack(pady=50)
        except:
            tk.Label(self.sidebar, text="VNNotes", fg="white", bg="#0f172a", font=("Segoe UI", 20, "bold")).pack(pady=50)
            
        tk.Label(self.sidebar, text="The Secret Weapon for Flow", fg="#94a3b8", bg="#0f172a", font=("Segoe UI", 9)).pack(side="bottom", pady=20)

        # Build Frames
        self.create_welcome_page()
        self.create_license_page()
        self.create_location_page()
        self.create_install_page()
        self.create_finish_page()

        # Navigation Buttons
        self.nav_frame = tk.Frame(self, bg="#f8f9fa")
        self.nav_frame.place(relx=1.0, rely=1.0, anchor="se", x=-40, y=-20)
        
        self.btn_cancel = ttk.Button(self.nav_frame, text="Cancel", command=self.on_cancel)
        self.btn_cancel.pack(side="right", padx=(5, 0))
        
        self.btn_next = ttk.Button(self.nav_frame, text="Next >", command=self.go_next)
        self.btn_next.pack(side="right", padx=(5, 0))
        
        self.btn_back = ttk.Button(self.nav_frame, text="< Back", command=self.go_back)
        self.btn_back.pack(side="right")

    def create_welcome_page(self):
        f = tk.Frame(self.container, bg="#f8f9fa")
        ttk.Label(f, text="Welcome to VNNotes Setup", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        
        desc = "VNNotes is the ultimate stealth partner for high-stakes Meetings and Interviews. This setup wizard will guide you through the official installation process of VNNotes v1.0.0 Stable.\n\nKey Power Features:\n• Phantom Invisibility (Anti-Capture Tech)\n• Meeting Master Teleprompting\n• Multi-Document Workspace System\n• Integrated Ultra-Hub (Browser & Clipboard)\n• 100% Standalone Private Vault"
        tk.Label(f, text=desc, bg="#f8f9fa", wraplength=400, justify="left", font=("Segoe UI", 10)).pack(anchor="w")
        
        tk.Label(f, text="\nClick 'Next' to proceed with the installation.", bg="#f8f9fa", font=("Segoe UI", 10, "italic")).pack(anchor="w")
        self.frames["Welcome"] = f

    def create_license_page(self):
        f = tk.Frame(self.container, bg="#f8f9fa")
        ttk.Label(f, text="End-User License Agreement", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        
        text_area = tk.Text(f, height=12, width=50, font=("Consolas", 9), relief="flat", borderwidth=1)
        text_area.insert("1.0", self.license_text)
        text_area.config(state="disabled")
        text_area.pack(fill="both", expand=True)
        
        cb = tk.Checkbutton(f, text="I accept the terms of the License Agreement", variable=self.accepted_license, bg="#f8f9fa", font=("Segoe UI", 10), command=self.update_nav)
        cb.pack(anchor="w", pady=(10, 0))
        self.frames["License"] = f

    def create_location_page(self):
        f = tk.Frame(self.container, bg="#f8f9fa")
        ttk.Label(f, text="Select Installation Folder", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        tk.Label(f, text="The installer will install VNNotes to the following folder:", bg="#f8f9fa").pack(anchor="w")
        
        path_frame = tk.Frame(f, bg="#f8f9fa")
        path_frame.pack(fill="x", pady=15)
        self.path_entry = ttk.Entry(path_frame)
        self.path_entry.insert(0, self.install_dir)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(path_frame, text="Browse...", command=self.browse_folder).pack(side="right")
        
        tk.Label(f, text="At least 600 MB of free disk space is required.", bg="#f8f9fa", fg="#64748b", font=("Segoe UI", 9)).pack(anchor="w")
        self.frames["Location"] = f

    def create_install_page(self):
        f = tk.Frame(self.container, bg="#f8f9fa")
        ttk.Label(f, text="Installing Files", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        self.status_label = tk.Label(f, text="Ready to extract files...", bg="#f8f9fa")
        self.status_label.pack(anchor="w")
        
        self.progress = ttk.Progressbar(f, mode="determinate")
        self.progress.pack(fill="x", pady=20)
        self.frames["Installing"] = f

    def create_finish_page(self):
        f = tk.Frame(self.container, bg="#f8f9fa")
        ttk.Label(f, text="Completing VNNotes Setup", style="Header.TLabel").pack(anchor="w", pady=(0, 20))
        tk.Label(f, text="VNNotes has been successfully installed on your computer.\n\nClick Finish to exit the wizard.", bg="#f8f9fa").pack(anchor="w")
        
        self.chk_shortcut = tk.IntVar(value=1)
        tk.Checkbutton(f, text="Create Desktop Shortcut", variable=self.chk_shortcut, bg="#f8f9fa", font=("Segoe UI", 10)).pack(anchor="w", pady=(20, 5))
        self.chk_launch = tk.IntVar(value=1)
        tk.Checkbutton(f, text="Launch VNNotes Official Release", variable=self.chk_launch, bg="#f8f9fa", font=("Segoe UI", 10)).pack(anchor="w")
        
        tk.Label(f, text="\nThank you for choosing VNNotes.", bg="#f8f9fa", fg="#10b981", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.frames["Finished"] = f

    def show_frame(self, name):
        if self.current_frame:
            self.current_frame.pack_forget()
        self.current_frame = self.frames[name]
        self.current_frame.pack(fill="both", expand=True)
        self.current_step = name
        self.update_nav()

    def update_nav(self):
        self.btn_back.state(["!disabled"])
        self.btn_next.state(["!disabled"])
        self.btn_cancel.state(["!disabled"])
        self.btn_next.config(text="Next >")

        if self.current_step == "Welcome":
            self.btn_back.state(["disabled"])
        elif self.current_step == "License":
            if not self.accepted_license.get():
                self.btn_next.state(["disabled"])
        elif self.current_step == "Location":
            self.btn_next.config(text="Install")
        elif self.current_step == "Installing":
            self.btn_back.state(["disabled"])
            self.btn_next.state(["disabled"])
            self.btn_cancel.state(["disabled"])
        elif self.current_step == "Finished":
            self.btn_back.pack_forget()
            self.btn_cancel.pack_forget()
            self.btn_next.config(text="Finish")

    def go_next(self):
        steps = ["Welcome", "License", "Location", "Installing", "Finished"]
        idx = steps.index(self.current_step)
        if self.current_step == "Location":
            self.start_install()
        elif self.current_step == "Finished":
            self.finish()
        else:
            self.show_frame(steps[idx+1])

    def go_back(self):
        steps = ["Welcome", "License", "Location"]
        idx = steps.index(self.current_step)
        self.show_frame(steps[idx-1])

    def on_cancel(self):
        if messagebox.askyesno("Exit Setup", "Are you sure you want to cancel the installation?"):
            self.destroy()

    def browse_folder(self):
        d = filedialog.askdirectory(initialdir=self.install_dir)
        if d:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, d)

    def start_install(self):
        self.install_dir = self.path_entry.get()
        self.show_frame("Installing")
        threading.Thread(target=self.run_install, daemon=True).start()

    def run_install(self):
        try:
            if os.path.exists(self.install_dir):
                self.status_label.config(text="Preparing directory...")
                # Try to avoid full wipe if user selected a custom dir with files
                # But for app integrity, we usually replace.
            
            os.makedirs(self.install_dir, exist_ok=True)
            
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                files = zf.namelist()
                total = len(files)
                for i, file in enumerate(files):
                    zf.extract(file, self.install_dir)
                    if i % 20 == 0:
                        pct = (i / total) * 100
                        self.progress['value'] = pct
                        self.status_label.config(text=f"Copying: {os.path.basename(file)}")
                        self.update_idletasks()
                        
            self.progress['value'] = 100
            self.status_label.config(text="Installation successful.")
            self.after(800, lambda: self.show_frame("Finished"))
        except Exception as e:
            messagebox.showerror("Installation Error", str(e))
            self.destroy()

    def finish(self):
        exe_path = os.path.join(self.install_dir, "VNNotes.exe")
        # Handle zip nesting if PyInstaller created its own subfolder
        if not os.path.exists(exe_path):
             nested = os.path.join(self.install_dir, "VNNotes", "VNNotes.exe")
             if os.path.exists(nested):
                 exe_path = nested
                 self.install_dir = os.path.join(self.install_dir, "VNNotes")

        if self.chk_shortcut.get():
            try:
                desktop = winshell.desktop()
                path = os.path.join(desktop, "VNNotes.lnk")
                shell = Dispatch('WScript.Shell')
                shortcut = shell.CreateShortcut(path)
                shortcut.TargetPath = exe_path
                shortcut.WorkingDirectory = self.install_dir
                shortcut.IconLocation = exe_path
                shortcut.Save()
            except Exception as e:
                print(f"Shortcut error: {e}")
                
        if self.chk_launch.get():
            try:
                os.startfile(exe_path)
            except:
                pass
            
        self.destroy()

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
