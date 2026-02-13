# 🍃 VNNotes: The Invisible Workspace

![Version](https://img.shields.io/badge/version-1.0.0-emerald?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-gray?style=flat-square)

**VNNotes** is a professional "invisible" workspace for Windows. The application helps you take notes, store ideas, and look up information with **absolute stealth**, remaining undetectable by screen recording software, livestreams, or screen sharing (Zoom, Teams, Discord, OBS...).

> **"Visible to you. Invisible to the world."**

---

## 🌟 Key Features

### 1. 👻 Ghost Mode (Anti-Capture Technology)
Using the **Windows Display Affinity API**, VNNotes can:
-   **Be 100% invisible** to screen recording/capturing software.
-   When sharing your screen, viewers only see your desktop wallpaper, while you continue to read or take notes normally.
-   Adjust transparency (Opacity) to blend perfectly with your environment.

### 2. 📝 Power Notes
A professional Markdown editor with advanced features (Updated **v1.0.0**):
-   **Drag & Drop**: Drag images and text from outside or move them freely within the editor.
-   **Image Alignment**: Right-click on images -> Select **Align Left / Center / Right**.
-   **Smart Resize**: Double-click on images to enter precise pixel dimensions.
-   **Code Blocks**: Write beautiful code with Monospace fonts.
-   **Checklists**: Quickly manage your to-do lists.

### 3. 🌐 Integrated Mini Browser
-   Dock a browser right next to your notes.
-   Look up documentation, Google Search, or view docs without Alt-Tabbing out of your main workflow.
-   Optionally set to "Always on Top".

### 4. 🔒 Local Privacy
-   Data is stored locally (**JSON**), never sent to the Cloud.
-   You have full ownership of your data.

---

## 🚀 Download & Installation

### Option 1: For General Users (Recommended)
Download the latest `.exe` installer from the **Releases** page:

👉 **[Download VNNotes v1.0.0](https://github.com/bbqqvv/AnonymNotes/releases/latest)**

1.  Download `VNNotes_Setup.exe`.
2.  Run the installer.
3.  Launch the app from the Desktop shortcut.

### Option 2: Portable Version
In the installation folder (`%LOCALAPPDATA%\VNNotes`), you can copy the `.exe` file anywhere.

---

## 💻 For Developers

If you want to add features or build from source:

### Requirements
-   Python 3.10 or higher.
-   Git.

### Environment Setup
```bash
# 1. Clone the project
git clone https://github.com/bbqqvv/AnonymNotes.git
cd AnonymNotes

# 2. Create a virtual environment
python -m venv venv
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Running the App
```bash
python main.py
```

### Building the Executable
Use the automated build script:
```bash
python tools/build_installer.py
```
The installer will be located in `tools/dist/`.

---

## 🌐 Web Landing Page
The project includes a modern Landing Page (Next.js + TailwindCSS) located in the `/web` directory.
To run the website:
1.  `cd web`
2.  Run `install_and_run.bat`.
3.  Visit `http://localhost:3000`.

---

## ⌨️ Shortcuts

| Shortcut | Function |
| :--- | :--- |
| `Ctrl + N` | Create new note |
| `Ctrl + S` | Manual save (Auto-saves every 5s) |
| `Ctrl + F` | Search within notes |
| `Ctrl + B/I/U` | Bold / Italic / Underline |
| `Double-Click Image` | Resize image |

---

**Developed by VTech Digital Solution.**
*Privacy First. Always.*
