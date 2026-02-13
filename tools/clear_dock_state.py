from src.core.config import ConfigManager
import sys

def clear_dock_state():
    print("🧹 Cleaning up dock state...")
    config = ConfigManager()
    
    # Remove all known dock state keys
    keys_to_remove = [
        "window/dock_state",
        "window/dock_state_v2",
        "window/dock_state_v3",
        "window/dock_state_v4"
    ]
    
    for key in keys_to_remove:
        if config.get_value(key):
            print(f"   - Removing {key}")
            config.set_value(key, "")
            
    print("✅ Dock state cleared. Please restart the application.")

if __name__ == "__main__":
    clear_dock_state()
