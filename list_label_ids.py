#!/usr/bin/env python3
"""
Script to list all order IDs from PNG label files and find the maximum ID.
Handles transformed PNG filenames with hash codes at the beginning.
Supports custom folder selection and recursive scanning.
"""

import os
import re
from pathlib import Path
from typing import List, Set, Dict
from embroidery_sorter.workflow_logger import log_print, logged_input

try:
    import tkinter as tk
    from tkinter import filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    log_print("⚠️  tkinter not available - folder dialog will not work")


def extract_stt_from_folder_name(folder_name: str) -> int:
    """
    Extract STT number from folder name with pattern XXX_hash.
    
    Examples:
    - 017_f0a1d6cb -> 17
    - 001_dcefbd29 -> 1
    - 025_abc123def -> 25
    
    Returns 0 if no valid STT found.
    """
    try:
        # Split by underscore and take the first part
        parts = folder_name.split('_')
        if len(parts) >= 2:
            stt_str = parts[0]
            # Check if it's a valid number
            if stt_str.isdigit():
                return int(stt_str)
        return 0
    except Exception as e:
        log_print(f"Error parsing folder name {folder_name}: {e}")
        return 0


def scan_person_max_stt(base_folder: str) -> Dict[str, int]:
    """
    Scan person folders and find max STT in each person's subfolders.
    Automatically detects all person folders (A, B, C, D, F, etc.) instead of hardcoding.
    
    Args:
        base_folder: Base folder path (should contain sorted/ subdirectory)
    
    Returns:
        Dict mapping person letter to max STT number
        Example: {'A': 17, 'B': 15, 'C': 0, 'D': 0, 'F': 5}
    """
    result = {}
    
    # Look for sorted folder in the selected directory
    base_path = Path(base_folder)
    sorted_path = base_path / "sorted"
    
    # If no sorted subfolder, check if the selected folder itself is the sorted folder
    if not sorted_path.exists():
        # Check if current folder looks like a sorted folder (contains person subdirs)
        person_folders = [p for p in base_path.iterdir() if p.is_dir() and len(p.name) == 1 and p.name.isalpha() and p.name.isupper()]
        if person_folders:
            sorted_path = base_path
        else:
            log_print(f"⚠️  No 'sorted' folder or person folders found in {base_folder}")
            return {}
    
    log_print(f"🔍 Scanning person folders in: {sorted_path}")
    
    # Auto-detect all person folders (single uppercase letters)
    person_folders = [p for p in sorted_path.iterdir() if p.is_dir() and len(p.name) == 1 and p.name.isalpha() and p.name.isupper()]
    
    if not person_folders:
        log_print("⚠️  No person folders found (expected single letter folders like A, B, C, D, F, etc.)")
        return {}
    
    # Sort person folders alphabetically for consistent output
    person_folders.sort(key=lambda x: x.name)
    
    # Scan each detected person folder
    for person_dir in person_folders:
        person_letter = person_dir.name
        max_stt = 0
        
        # Check both old and new structure
        # New structure: sorted/A/pes/001_hash/
        pes_path = person_dir / "pes"
        if pes_path.exists():
            # New structure
            stt_folders = [f for f in pes_path.iterdir() if f.is_dir()]
        else:
            # Old structure: sorted/A/001_hash/
            stt_folders = [f for f in person_dir.iterdir() if f.is_dir() and '_' in f.name]
        
        # Extract STT from each folder and find max
        for folder in stt_folders:
            stt = extract_stt_from_folder_name(folder.name)
            if stt > max_stt:
                max_stt = stt
        
        result[person_letter] = max_stt
        # log_print(f"   • Person {person_letter}: Max STT = {max_stt:03d}")
    
    return result


def print_person_max_stt_summary(stt_data: Dict[str, int]) -> None:
    """Print a summary of max STT for each person."""
    if not stt_data:
        log_print("⚠️  No person folder data found")
        return
    
    log_print("")
    log_print("📊 MAX STT SUMMARY PER PERSON:")
    log_print("=" * 40)
    
    total_folders = 0
    # Sort by person letter for consistent output
    for person in sorted(stt_data.keys()):
        max_stt = stt_data[person]
        total_folders += max_stt
        log_print(f"   🏷️  Person {person} = {max_stt:03d}")
    
    log_print("-" * 40)
    log_print(f"   📦 Total folders: {total_folders}")
    log_print("=" * 40)
    # log_print("")


def extract_id_from_filename(filename: str) -> int:
    """
    Extract order ID from transformed PNG filename.
    
    Examples:
    - 006B1F01K_4202_4859_1_1_item_1.png -> 4202
    - 006C2F01K_007C2R01K_4209_4866_1_1_item_1.png -> 4209
    - 006A1F01K_006B2F01K_006C3F01K_4215_4872_1_1_item_1.png -> 4215
    
    Pattern: [HASH_CODES]_[ID]_[OTHER_NUMBERS]_[REST].png
    """
    try:
        # Remove .png extension
        name_without_ext = filename.replace('.png', '')
        
        # Split by underscore
        parts = name_without_ext.split('_')
        
        # Find the first part that is a pure numeric ID (not a hash code)
        # Hash codes typically contain letters, pure IDs are numeric only
        for i, part in enumerate(parts):
            if part.isdigit() and len(part) >= 3:  # Order IDs are typically 3+ digits
                # Check if this looks like an order ID (not item numbers like 1, 1, etc.)
                if int(part) >= 1000:  # Assume order IDs start from 1000
                    return int(part)
        
        # Fallback: if no clear ID found, return 0
        return 0
        
    except Exception as e:
        log_print(f"Error parsing filename {filename}: {e}")
        return 0


def scan_label_folder(folder_path: str) -> List[int]:
    """Scan the specified folder recursively and extract all order IDs from PNG files."""
    
    if not os.path.exists(folder_path):
        log_print(f"❌ Folder not found: {folder_path}")
        return []
    
    folder = Path(folder_path)
    # Use recursive glob to find all PNG files in folder and subfolders
    png_files = list(folder.rglob("*.png"))
    
    # log_print(f"📁 Scanning folder: {folder.absolute()}")
    # log_print(f"🔍 Found {len(png_files)} PNG files (including subfolders)")
    # log_print("")
    
    if not png_files:
        log_print("⚠️  No PNG files found in the folder or its subfolders")
        return []
    
    # Extract IDs from all PNG files
    all_ids = []
    valid_ids = []
    invalid_files = []
    
    for png_file in png_files:
        filename = png_file.name
        relative_path = png_file.relative_to(folder)
        order_id = extract_id_from_filename(filename)
        
        if order_id > 0:
            all_ids.append(order_id)
            valid_ids.append((order_id, str(relative_path)))
        else:
            invalid_files.append(str(relative_path))
    
    # Remove duplicates and sort
    unique_ids = sorted(list(set(all_ids)))
    
    # Show results
    log_print(f"📊 EXTRACTION RESULTS:")
    log_print(f"   • Total PNG files processed: {len(png_files)}")
    log_print(f"   • Valid IDs extracted: {len(all_ids)}")
    log_print(f"   • Unique IDs found: {len(unique_ids)}")
    log_print(f"   • Files with no valid ID: {len(invalid_files)}")
    log_print("")
    
    if invalid_files:
        log_print(f"⚠️  Files that couldn't be parsed:")
        for filepath in invalid_files[:10]:  # Show first 10
            log_print(f"   • {filepath}")
        if len(invalid_files) > 10:
            log_print(f"   ... and {len(invalid_files) - 10} more")
    
    # Show sample valid extractions
    # if valid_ids:
    #     log_print(f"✅ Sample valid extractions:")
    #     for order_id, filepath in valid_ids[:10]:  # Show first 10
    #         log_print(f"   • {order_id} <- {filepath}")
    #     if len(valid_ids) > 10:
    #         log_print(f"   ... and {len(valid_ids) - 10} more")
    #     log_print("")
    
    return unique_ids


def open_folder_dialog() -> str:
    """Open a folder selection dialog and return the selected path."""
    if not TKINTER_AVAILABLE:
        log_print("❌ Folder dialog not available. Please enter path manually:")
        custom_path = logged_input("Nhập đường dẫn folder: ").strip()
        return custom_path if custom_path else ""
    
    try:
        # Create a root window and hide it
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)  # Bring dialog to front
        
        # Open folder dialog
        folder_path = filedialog.askdirectory(
            title="Chọn folder chứa file PNG",
            initialdir=os.getcwd()
        )
        
        # Destroy the root window
        root.destroy()
        
        return folder_path if folder_path else ""
        
    except Exception as e:
        log_print(f"❌ Error opening folder dialog: {e}")
        log_print("Falling back to manual input:")
        custom_path = logged_input("Nhập đường dẫn folder: ").strip()
        return custom_path if custom_path else ""


def get_folder_from_user() -> str:
    """Get folder path from user input."""
    # Check for auto folder dialog mode from workflow
    auto_folder_dialog = os.environ.get('AUTO_FOLDER_DIALOG') == '1'
    auto_option = os.environ.get('AUTO_OPTION')
    
    log_print("📁 FOLDER SELECTION:")
    log_print("   1. files/labels (default)")
    log_print("   2. sorted/A/labels")
    log_print("   3. sorted/B/labels") 
    log_print("   4. sorted/C/labels")
    log_print("   5. sorted/D/labels")
    log_print("   6. Browse folder (dialog)")
    log_print("")
    
    # If auto mode is enabled, automatically select option 6
    if auto_folder_dialog and auto_option == '6':
        log_print("🤖 Auto mode: Automatically selecting option 6 (Browse folder dialog)")
        log_print("🗂️  Opening folder dialog...")
        selected_folder = open_folder_dialog()
        if selected_folder:
            log_print(f"✅ Selected folder: {selected_folder}")
            
            # Scan and display max STT for each person
            log_print("")
            log_print("🔍 Analyzing person folder STT numbers...")
            stt_data = scan_person_max_stt(selected_folder)
            print_person_max_stt_summary(stt_data)
            
            return selected_folder
        else:
            log_print("❌ No folder selected, falling back to default")
            return "files/labels"
    
    while True:
        choice = logged_input("Chọn folder (1-6): ").strip()
        
        if choice == '1' or choice == '':
            return "files/labels"
        elif choice == '2':
            return "sorted/A/labels"
        elif choice == '3':
            return "sorted/B/labels"
        elif choice == '4':
            return "sorted/C/labels"
        elif choice == '5':
            return "sorted/D/labels"
        elif choice == '6':
            log_print("🗂️  Opening folder dialog...")
            selected_folder = open_folder_dialog()
            if selected_folder:
                log_print(f"✅ Selected folder: {selected_folder}")
                
                # Scan and display max STT for each person
                log_print("")
                log_print("🔍 Analyzing person folder STT numbers...")
                stt_data = scan_person_max_stt(selected_folder)
                print_person_max_stt_summary(stt_data)
                
                return selected_folder
            else:
                log_print("❌ No folder selected")
        else:
            log_print("❌ Lựa chọn không hợp lệ, vui lòng chọn 1-6")


def main():
    """Main function to scan labels and show results."""
    log_print("=" * 60)
    log_print("LABEL ID EXTRACTOR")
    log_print("=" * 60)
    log_print("")
    
    # Get folder from user
    folder_path = get_folder_from_user()
    log_print("")
    
    # Scan the selected folder
    id_list = scan_label_folder(folder_path)
    
    if not id_list:
        log_print("❌ No valid IDs found!")
        return
    
    # Show final results
    log_print(f"🎯 FINAL RESULTS:")
    log_print(f"📋 All unique order IDs: {id_list}")
    log_print(f"📊 Total unique IDs: {len(id_list)}")
    log_print(f"🔢 ID range: {min(id_list)} - {max(id_list)}")
    log_print(f"🏆 End ID: {max(id_list)}")
    log_print("")


if __name__ == "__main__":
    main()