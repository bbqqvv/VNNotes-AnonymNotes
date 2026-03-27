# VNNotes Architecture & Technical Documentation

> **Executive Summary:** VNNotes is a stealth-oriented, multi-pane note-taking and teleprompter application built using Python and PyQt6. It provides local-first, anti-capture "phantom" functionality designed primarily for meetings and interviews, alongside a tight integrated web-based Plugin Market.

## 1. System Architecture Overview

VNNotes utilizes a desktop-first architecture combining native Windows APIs with a robust UI layout engine (`QDockWidget`). The application logic resides in standard domain-driven hierarchies, bridging Python execution with modern web technologies (`QWebEngineView`) for complex integrated components (like the Plugin Marketplace and local search engines).

### Key Subsystems:
- **Core Engine:** Application lifecycle, threading, environment optimizations (GPU).
- **UI & Layout Manager:** Handles the `QMainWindow`, nested docks, and flexible sidebars using customized `DockManager` and `ThemeManager` modules.
- **Phantom Layer (Anti-Capture):** Integrates with `ctypes.windll.user32.SetWindowDisplayAffinity` to make windows invisible to Discord, Zoom, OBS, and Teams.
- **Plugin System & Market Bridge:** Supports dynamic Python-based plugins (`src.core.plugins.PluginManager`) and a `QWebChannel`-based bridge (`MarketBridge`) communicating directly with Next.js web applications.
- **Infrastructure:** Local-first session and clipboard control without utilizing any cloud sync features to maximize data sovereignty.

## 2. Core Components

### `main.py`
The entry point of VNNotes. It enforces critical environment parameters before initiating the Qt loop:
- Allows hardware acceleration (`QT_OPENGL="desktop"`) while disabling Chromium logs.
- Instantiates `QApplication`, configures shared OpenGL contexts, and defines the global exception hook for graceful crash telemetry (`FATAL_CRASH.txt`).

### `MainWindow` (`src/ui/main_window.py`)
The central nervous system of the UI layout:
- **`DockManager`**: Orchestrates nested `QDockWidget` objects. Provides APIs to split notes right/down, preventing native layout crashes through careful bounding.
- **`SidebarWidget`**: A resizable tree view of the filesystem or local notes database, restricted to the left area.
- **`VisibilityManager`**: Controls the Anti-Capture toggles and window opacity shortcuts.
- **`MarketBridge`**: Mounts `window.vnnotes_market` using `QWebChannel` for a seamless hybrid React-to-Python application market experience.

## 3. Design Decisions & Rationale

- **PyQt6 over Electron:** PyQt6 allows deeply integrated native Windows API manipulation (essential for the `SetWindowDisplayAffinity` anti-capture stealth modes) while maintaining low memory footprint compared to Chrome V8 overheads.
- **Local-First Zero-Cloud:** Protects the sensitive nature of meeting notes and interviews. No telemetry.
- **Hybrid Market Strategy:** While the core app is fast and native, the *Plugin Market* is built with Next.js to leverage sleek, modern web aesthetics and fast iteration via `QWebEngineView`. To avoid Electron's bloat, this is a local/remote bridge strictly limited to market/browser operations.

## 4. Integration Points (Market Bridge)
The market bridge (`src/core/market_bridge.py`) defines a PyQt slot mechanism exposed via `QWebChannel`.
1. The Next.js frontend calls `window.vnnotes_market.install_plugin(id, url)`.
2. The Python handler downloads the zip, verifies integrity, and unpacks to the `plugins/` directory.
3. The `PluginManager` dynamically loads the components into the active layout.

## 5. Security & Privacy Model
- **Memory Safety:** Does not access untrusted memory addresses manually. Local Python scope execution only.
- **Data Protection:** Files are stored cleanly on disk in a standalone private vault format.
- **Plugin Sandboxing:** (Roadmap) Currently, plugins run in the same process space, requiring vetted/trusted plugins for core functionality. Future implementations might utilize separate processes.

## 6. Glossary
- **Phantom Mode:** The state where the application window is flagged as `WDA_EXCLUDEFROMCAPTURE`, disappearing from stream encoders.
- **Ultra-Hub:** Embedded browser dock allowing inline lookups.
- **Zeta Strategy:** Atomic visibility toggling rules defined in the `MainWindow` layout refresh cycle to prevent visual stutter.
