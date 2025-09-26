#!/usr/bin/env python3
"""
Adapter Recovery Script
This script helps recover adapter files from training sessions
"""

import os
import shutil
import json
from pathlib import Path

def recover_adapter_from_session(session_id, temp_base_dir=None):
    """
    Attempt to recover adapter files from a training session
    
    Args:
        session_id: The training session ID
        temp_base_dir: Base directory for temp files (defaults to system temp)
    """
    if temp_base_dir is None:
        temp_base_dir = os.path.join(os.environ.get('TEMP', '/tmp'), '..', 'Local', 'Temp')
    
    print(f"Looking for adapter files for session: {session_id}")
    
    # Possible locations where adapter might be
    possible_locations = [
        os.path.join(temp_base_dir, f"adapter_export_{session_id}"),
        os.path.join(temp_base_dir, f"model_artifacts_{session_id}"),
        os.path.join(os.getcwd(), "adapter_exports", f"adapter_export_{session_id}")
    ]
    
    # Check for any temp directories that might contain the adapter
    temp_dirs = []
    if os.path.exists(temp_base_dir):
        for item in os.listdir(temp_base_dir):
            if session_id in item:
                temp_dirs.append(os.path.join(temp_base_dir, item))
    
    possible_locations.extend(temp_dirs)
    
    print(f"Checking locations: {possible_locations}")
    
    for location in possible_locations:
        if os.path.exists(location):
            print(f"Found directory: {location}")
            
            # List contents
            try:
                contents = os.listdir(location)
                print(f"Contents: {contents}")
                
                # Look for adapter files
                for item in contents:
                    item_path = os.path.join(location, item)
                    if os.path.isdir(item_path) and 'adapter' in item.lower():
                        print(f"Found potential adapter directory: {item_path}")
                        return item_path
                        
            except Exception as e:
                print(f"Error reading {location}: {e}")
    
    print("No adapter files found")
    return None

def create_adapter_export_from_config(session_id):
    """
    Create a complete adapter export from existing configuration
    """
    export_dir = os.path.join("adapter_exports", f"adapter_export_{session_id}")
    
    if not os.path.exists(export_dir):
        print(f"Export directory not found: {export_dir}")
        return False
    
    print(f"Found export directory: {export_dir}")
    
    # Check if adapter_config.json exists
    config_path = os.path.join(export_dir, "adapter_config.json")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"Adapter configuration found:")
        print(f"  - Name: {config.get('adapter_name')}")
        print(f"  - Base Model: {config.get('base_model')}")
        print(f"  - Created: {config.get('created_at')}")
        print(f"  - Session ID: {config.get('session_id')}")
        
        # Check for adapter files
        adapter_path = os.path.join(export_dir, "adapter")
        if os.path.exists(adapter_path):
            print(f"✅ Adapter files found at: {adapter_path}")
            return True
        else:
            print(f"❌ Adapter files missing at: {adapter_path}")
            print("This is a configuration-only export (no actual adapter files)")
            return False
    else:
        print(f"Configuration file not found: {config_path}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
    else:
        session_id = "training_1758827267"  # Default to your session
    
    print(f"Recovering adapter for session: {session_id}")
    
    # Try to recover from temp directories
    recovered_path = recover_adapter_from_session(session_id)
    if recovered_path:
        print(f"✅ Recovered adapter from: {recovered_path}")
    else:
        print("❌ Could not recover adapter files from temp directories")
    
    # Check existing export
    print("\nChecking existing export...")
    create_adapter_export_from_config(session_id)
