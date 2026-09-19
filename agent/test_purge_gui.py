import sys
import os
from pathlib import Path
import json

# Add agent tools to path
sys.path.append(r"D:\AI\tools\agent")

try:
    from purge_gui import PurgeGUI
    import tkinter as tk
    print("IMPORT SUCCESS")
except Exception as e:
    print(f"IMPORT FAILED: {e}")
    sys.exit(1)

def test_settings_roundtrip():
    print("Testing settings roundtrip...")
    root = tk.Tk()
    root.withdraw() # Don't show window
    
    app = PurgeGUI(root)
    
    # Change settings
    app.settings['root'] = r"D:\AI\test_root"
    app.settings['keep'] = 5
    app.settings['creo_mode'] = True
    app.settings['backup_dir'] = r"D:\AI\test_backup"
    app.save_settings()
    
    # Reload settings
    new_app = PurgeGUI(root)
    
    assert new_app.settings['root'] == r"D:\AI\test_root"
    assert new_app.settings['keep'] == 5
    assert new_app.settings['creo_mode'] is True
    assert new_app.settings['backup_dir'] == r"D:\AI\test_backup"
    
    print("SETTINGS ROUNDTRIP SUCCESS")
    root.destroy()

if __name__ == "__main__":
    test_settings_roundtrip()
    print("ALL TESTS PASSED")
