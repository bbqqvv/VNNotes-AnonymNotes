# ADR 0001: Use Software Rendering for UI Stability

## Status
Accepted

## Context
Various users reported "White Screen" or "Invisible UI" issues during application startup. These issues were traced back to OpenGL/GPU driver incompatibilities on Windows, particularly when combined with high DPI scaling (125% - 150%) and diverse hardware (Intel UHD Graphics, NVIDIA, etc.). Qt's hardware acceleration frequently conflicts with Windows' Desktop Window Manager (DWM) in these scenarios.

## Decision
We will force **Software Rendering** as the default for the entire application (including QWebEngineView) by setting the following environment variables at the very beginning of `main.py`:

- `os.environ["QT_OPENGL"] = "software"`
- `os.environ["QTWEBENGINE_DISABLE_LOGGING"] = "1"`
- `os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing"`

Additionally, `AA_ShareOpenGLContexts` is enabled to ensure WebEngine stability in this mode.

## Consequences
- **Positive**: Eliminates the persistent white screen/rendering crash on startup.
- **Positive**: Provides a consistent UI appearance across different hardware setups.
- **Neutral**: Slightly higher CPU usage for UI drawing, but negligible for a note-taking application.
- **Negative**: High-frame-rate CSS animations in the browser might be less smooth, though stability is prioritized over "60fps" for enterprise text editing.
