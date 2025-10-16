#!/usr/bin/env python3
"""
Copy static files from project root to backend static directory
This script should be run from the backend directory or project root
"""

import shutil
from pathlib import Path
import sys

# Get the script's directory (backend/)
script_dir = Path(__file__).parent.resolve()

# Project root is one level up from backend/
project_root = script_dir.parent

# Source: project_root/static/
source_static = project_root / "static"

# Destination: backend/open_webui/static/
dest_static = script_dir / "open_webui" / "static"

# Files to copy
files_to_copy = ["favicon.png", "user.png", "doge.png"]

print(f"Project root: {project_root}")
print(f"Source static dir: {source_static}")
print(f"Destination static dir: {dest_static}")
print(f"Source exists: {source_static.exists()}")
print(f"Destination exists: {dest_static.exists()}")
print()

if not source_static.exists():
    print(f"ERROR: Source directory does not exist: {source_static}")
    sys.exit(1)

if not dest_static.exists():
    print(f"ERROR: Destination directory does not exist: {dest_static}")
    sys.exit(1)

# Copy files
copied_count = 0
for filename in files_to_copy:
    source_file = source_static / filename
    dest_file = dest_static / filename
    
    if source_file.exists():
        try:
            shutil.copy2(source_file, dest_file)
            file_size = dest_file.stat().st_size
            print(f"[OK] Copied {filename} ({file_size} bytes)")
            copied_count += 1
        except Exception as e:
            print(f"[FAIL] Failed to copy {filename}: {e}")
    else:
        print(f"[WARN] Source file not found: {source_file}")

print(f"\nCopied {copied_count}/{len(files_to_copy)} files successfully!")

# List the destination directory contents
print(f"\nContents of {dest_static}:")
for item in sorted(dest_static.iterdir()):
    if item.is_file():
        size = item.stat().st_size
        print(f"  - {item.name} ({size} bytes)")
    else:
        print(f"  - {item.name}/ (directory)")

