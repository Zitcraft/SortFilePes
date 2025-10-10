#!/usr/bin/env python3
"""
Script to copy files from Dropbox folders to local folders based on API ID list with multi-threading
"""

import os
import shutil
import requests
from pathlib import Path
from typing import List, Set, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import argparse

def get_order_ids_from_api() -> Set[int]:
    """Get order IDs from the API endpoint"""
    try:
        print("Fetching order IDs from API...")
        response = requests.get("https://lemiex.us/api/order-status", timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print(f"API Response type: {type(data)}")
        
        # Handle different API response formats
        ids = set()
        
        if isinstance(data, list):
            # If API returns list of IDs or objects
            for item in data:
                if isinstance(item, int):
                    ids.add(item)
                elif isinstance(item, dict):
                    # Try common ID field names
                    for id_field in ['id', 'order_id', 'orderId', 'ID']:
                        if id_field in item and isinstance(item[id_field], int):
                            ids.add(item[id_field])
                            break
        
        elif isinstance(data, dict):
            # If API returns object with orders array
            for key in ['orders', 'data', 'results', 'items']:
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        if isinstance(item, int):
                            ids.add(item)
                        elif isinstance(item, dict):
                            for id_field in ['id', 'order_id', 'orderId', 'ID']:
                                if id_field in item and isinstance(item[id_field], int):
                                    ids.add(item[id_field])
                                    break
                    break
            
            # If data itself contains ID fields
            if not ids:
                for id_field in ['id', 'order_id', 'orderId', 'ID']:
                    if id_field in data and isinstance(data[id_field], int):
                        ids.add(data[id_field])
        
        print(f"Extracted {len(ids)} unique IDs from API")
        if ids:
            print(f"Sample IDs: {sorted(list(ids))[:10]}...")
        
        return ids
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from API: {e}")
        print("Continuing without API data...")
        return set()
    except Exception as e:
        print(f"Error parsing API response: {e}")
        print("Continuing without API data...")
        return set()

# Thread-safe counters
copy_lock = threading.Lock()
copy_stats = {
    'copied': 0,
    'errors': 0,
    'found_ids': set(),
    'missing_ids': []
}

def copy_single_file(source_file: Path, dest_folder: Path) -> Tuple[bool, str]:
    """Copy a single file. Returns (success, message)"""
    try:
        dest_file = dest_folder / source_file.name
        shutil.copy2(source_file, dest_file)
        return True, f"✅ Copied: {source_file.name}"
    except Exception as e:
        return False, f"❌ Error copying {source_file.name}: {e}"

def process_target_id(target_id: int, source_files: List[Path], dest_folder: Path) -> Tuple[int, List[str]]:
    """Process a single target ID. Returns (file_count, messages)"""
    matching_files = []
    messages = []
    
    # Find files that start with this ID
    for source_file in source_files:
        filename = source_file.name
        parts = filename.split("_")
        if parts and parts[0].isdigit():
            file_id = int(parts[0])
            if file_id == target_id:
                matching_files.append(source_file)
    
    if matching_files:
        with copy_lock:
            copy_stats['found_ids'].add(target_id)
        
        # Copy all matching files for this ID
        for source_file in matching_files:
            success, message = copy_single_file(source_file, dest_folder)
            messages.append(message)
            
            with copy_lock:
                if success:
                    copy_stats['copied'] += 1
                else:
                    copy_stats['errors'] += 1
        
        return len(matching_files), messages
    else:
        with copy_lock:
            copy_stats['missing_ids'].append(target_id)
        return 0, []

def copy_files_from_folder(target_ids: Set[int], source_folder: Path, dest_folder: Path, folder_type: str) -> Dict[str, int]:
    """Copy files from a specific Dropbox folder to destination folder"""
    print(f"\n=== Processing {folder_type.upper()} files ===")
    print(f"Source: {source_folder}")
    print(f"Destination: {dest_folder.absolute()}")
    
    if not source_folder.exists():
        print(f"❌ {folder_type.capitalize()} folder not found at {source_folder}")
        return {'copied': 0, 'errors': 0, 'found_ids': 0, 'missing_ids': 0}
    
    # Create destination folder
    dest_folder.mkdir(exist_ok=True)
    
    # Find all files in source folder (support multiple extensions)
    if folder_type == 'design':
        source_files = list(source_folder.glob("*.pes"))
    elif folder_type == 'label':
        # Support common label file formats
        source_files = []
        for ext in ['*.pdf', '*.png', '*.jpg', '*.jpeg', '*.svg']:
            source_files.extend(source_folder.glob(ext))
    else:
        source_files = list(source_folder.glob("*"))
    
    print(f"Found {len(source_files)} {folder_type} files")
    
    if not source_files:
        return {'copied': 0, 'errors': 0, 'found_ids': 0, 'missing_ids': 0}
    
    # Reset stats for this folder
    global copy_stats
    copy_stats = {
        'copied': 0,
        'errors': 0,
        'found_ids': set(),
        'missing_ids': []
    }
    
    start_time = time.time()
    
    # Process IDs with thread pool
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_id = {
            executor.submit(process_target_id, target_id, source_files, dest_folder): target_id 
            for target_id in target_ids
        }
        
        # Process completed tasks
        completed = 0
        total_tasks = len(future_to_id)
        
        for future in as_completed(future_to_id):
            target_id = future_to_id[future]
            completed += 1
            
            try:
                file_count, messages = future.result()
                for message in messages:
                    print(message)
                
                # Progress indicator
                if completed % 20 == 0 or completed == total_tasks:
                    elapsed = time.time() - start_time
                    print(f"Progress: {completed}/{total_tasks} IDs processed ({completed/total_tasks*100:.1f}%) - {elapsed:.1f}s")
                    
            except Exception as e:
                print(f"❌ Error processing ID {target_id}: {e}")
                with copy_lock:
                    copy_stats['errors'] += 1
    
    elapsed_time = time.time() - start_time
    
    # Report results for this folder
    print(f"\n--- {folder_type.capitalize()} Summary ---")
    print(f"Execution time: {elapsed_time:.2f} seconds")
    print(f"Files copied: {copy_stats['copied']}")
    print(f"Copy errors: {copy_stats['errors']}")
    print(f"IDs found: {len(copy_stats['found_ids'])}")
    print(f"IDs not found: {len(copy_stats['missing_ids'])}")
    
    # Show missing IDs list
    if copy_stats['missing_ids']:
        missing_list = sorted(list(copy_stats['missing_ids']))
        print(f"Missing IDs: {missing_list}")
    
    if elapsed_time > 0:
        print(f"Copy speed: {copy_stats['copied']/elapsed_time:.1f} files/second")
    
    return {
        'copied': copy_stats['copied'],
        'errors': copy_stats['errors'],
        'found_ids': copy_stats['found_ids'],
        'missing_ids': copy_stats['missing_ids']
    }

def main():
    """Main function with argument parsing"""
    print("=" * 60)
    print("EMBROIDERY FILE DOWNLOADER")
    print("=" * 60)
    print()
    
    # Show confirmation and options
    print("Tải file từ Dropbox về thư mục 'files/':")
    print("1. Design files (.pes) -> files/design/")
    print("2. Label files (.png/.pdf/.jpg/.svg) -> files/labels/")
    print()
    
    parser = argparse.ArgumentParser(description='Copy files from Dropbox folders based on API IDs')
    parser.add_argument('--design', action='store_true', help='Copy design files (PES) from designpes folder')
    parser.add_argument('--label', action='store_true', help='Copy label files (PDF/PNG/JPG) from labels folder')
    parser.add_argument('--all', action='store_true', help='Copy both design and label files')
    parser.add_argument('--list', action='store_true', help='List files in Dropbox folders')
    
    args = parser.parse_args()
    
    # If no specific option is provided, show interactive prompt
    if not any([args.design, args.label, args.all, args.list]):
        print("Chọn tùy chọn:")
        print("1. Tải chỉ design files (.pes)")
        print("2. Tải chỉ label files (.png/.pdf/.jpg/.svg)")
        print("3. Tải tất cả files")
        print("4. Liệt kê files trong Dropbox")
        print()
        choice = input("Nhập lựa chọn (1-4) hoặc 'q' để thoát: ").strip()
        
        if choice == 'q':
            print("Đã hủy bỏ.")
            return
        elif choice == '1':
            args.design = True
        elif choice == '2':
            args.label = True
        elif choice == '3':
            args.all = True
        elif choice == '4':
            args.list = True
        else:
            print("Lựa chọn không hợp lệ. Mặc định tải design files.")
            args.design = True
    
    if args.list:
        list_dropbox_files()
        return
    
    # Confirmation before processing
    if args.all:
        action = "Tải tất cả files (design + labels)"
    elif args.design:
        action = "Tải design files (.pes)"
    elif args.label:
        action = "Tải label files"
    else:
        action = "Tải files"
    
    print(f"\n{action}")
    confirm = input("Bạn có muốn tiếp tục? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Đã hủy bỏ.")
        return
    print()
    
    # Create directories
    os.makedirs("files/design", exist_ok=True)
    os.makedirs("files/labels", exist_ok=True)
    
    # Get API IDs
    target_ids = get_order_ids_from_api()
    
    if not target_ids:
        print("No IDs found from API. Exiting...")
        return
    
    print(f"Target IDs from API: {len(target_ids)} IDs")
    
    # Dropbox base path
    user_dir = os.path.expanduser("~")
    dropbox_base = Path(os.path.join(user_dir, "Dropbox"))
    
    total_copied = 0
    total_errors = 0
    all_missing_ids = set()  # Collect all missing IDs
    
    # Process design files
    if args.design or args.all:
        design_source = dropbox_base / "designpes"
        design_dest = Path("files/design")
        design_stats = copy_files_from_folder(target_ids, design_source, design_dest, "design")
        total_copied += design_stats['copied']
        total_errors += design_stats['errors']
        all_missing_ids.update(design_stats['missing_ids'])
    
    # Process label files
    if args.label or args.all:
        label_source = dropbox_base / "labels"
        label_dest = Path("files/labels")
        label_stats = copy_files_from_folder(target_ids, label_source, label_dest, "label")
        total_copied += label_stats['copied']
        total_errors += label_stats['errors']
        all_missing_ids.update(label_stats['missing_ids'])
    
    # Final summary with complete missing IDs
    print(f"\n=== FINAL SUMMARY ===")
    print(f"Total files copied: {total_copied}")
    print(f"Total errors: {total_errors}")
    
    if all_missing_ids:
        missing_list = sorted(list(all_missing_ids))
        print(f"⚠️  Total IDs not found across all folders: {len(missing_list)}")
        print(f"Missing IDs: {missing_list}")
        
        # Ask if user wants to retry
        print()
        retry = input("Bạn có muốn thử tải lại các file bị thiếu? (y/N): ").strip().lower()
        if retry in ['y', 'yes']:
            print("\n🔄 Đang thử tải lại các file bị thiếu...")
            retry_missing_files(missing_list, args)
    else:
        print("✅ All requested files found and copied successfully!")
    print()

def retry_missing_files(missing_ids, args):
    """Retry downloading missing files with different approach."""
    print(f"Đang thử tải lại {len(missing_ids)} ID bị thiếu...")
    
    # Get Dropbox path
    user_dir = os.path.expanduser("~")
    dropbox_base = Path(os.path.join(user_dir, "Dropbox"))
    
    if not dropbox_base.exists():
        print(f"❌ Dropbox folder not found: {dropbox_base}")
        return
    
    # Convert to set for faster lookup
    missing_set = set(missing_ids)
    retry_copied = 0
    retry_errors = 0
    
    # Process design files if requested
    if args.design or args.all:
        print("\n📁 Retry: Processing design files...")
        design_source = dropbox_base / "designpes" 
        design_dest = Path("files/design")
        
        if design_source.exists():
            for file in design_source.glob("*.pes"):
                try:
                    # Extract ID from filename
                    parts = file.name.split("_")
                    if parts and parts[0].isdigit():
                        file_id = int(parts[0])
                        if file_id in missing_set:
                            dest_file = design_dest / file.name
                            if not dest_file.exists():  # Only copy if not already exists
                                shutil.copy2(file, dest_file)
                                print(f"✅ Retry copied: {file.name}")
                                retry_copied += 1
                                missing_set.discard(file_id)
                except Exception as e:
                    retry_errors += 1
                    print(f"❌ Retry error: {file.name} - {e}")
    
    # Process label files if requested
    if args.label or args.all:
        print("\n📁 Retry: Processing label files...")
        label_source = dropbox_base / "labels"
        label_dest = Path("files/labels")
        
        if label_source.exists():
            for ext in ['*.pdf', '*.png', '*.jpg', '*.jpeg', '*.svg']:
                for file in label_source.glob(ext):
                    try:
                        # Extract ID from filename
                        parts = file.name.split("_")
                        if parts and parts[0].isdigit():
                            file_id = int(parts[0])
                            if file_id in missing_set:
                                dest_file = label_dest / file.name
                                if not dest_file.exists():  # Only copy if not already exists
                                    shutil.copy2(file, dest_file)
                                    print(f"✅ Retry copied: {file.name}")
                                    retry_copied += 1
                                    missing_set.discard(file_id)
                    except Exception as e:
                        retry_errors += 1
                        print(f"❌ Retry error: {file.name} - {e}")
    
    # Show retry results
    still_missing = sorted(list(missing_set))
    print(f"\n=== RETRY RESULTS ===")
    print(f"Retry copied: {retry_copied} files")
    print(f"Retry errors: {retry_errors} files")
    
    if still_missing:
        print(f"⚠️  Still missing {len(still_missing)} IDs: {still_missing}")
    else:
        print("✅ All missing files have been found and copied!")
        print("✅ All requested IDs were found and processed")
    
    print("Done!")

def list_dropbox_files():
    """List all files in Dropbox folders for debugging"""
    user_dir = os.path.expanduser("~")
    dropbox_base = Path(os.path.join(user_dir, "Dropbox"))
    
    folders = [
        ("designpes", "*.pes"),
        ("labels", "*")
    ]
    
    for folder_name, pattern in folders:
        folder_path = dropbox_base / folder_name
        print(f"\n=== {folder_name.upper()} FOLDER ===")
        print(f"Path: {folder_path}")
        
        if not folder_path.exists():
            print(f"❌ Folder not found")
            continue
        
        if folder_name == "labels":
            # Multiple extensions for labels
            files = []
            for ext in ['*.pdf', '*.png', '*.jpg', '*.jpeg', '*.svg']:
                files.extend(folder_path.glob(ext))
        else:
            files = list(folder_path.glob(pattern))
        
        print(f"Found {len(files)} files")
        
        # Group by ID for better overview
        id_groups = {}
        for file in files:
            parts = file.name.split("_")
            if parts and parts[0].isdigit():
                file_id = int(parts[0])
                if file_id not in id_groups:
                    id_groups[file_id] = []
                id_groups[file_id].append(file.name)
        
        print(f"Grouped into {len(id_groups)} unique IDs")
        for file_id in sorted(list(id_groups.keys())[:10]):  # Show first 10
            files_for_id = id_groups[file_id]
            print(f"  ID {file_id}: {len(files_for_id)} file(s)")
            for filename in files_for_id[:2]:  # Show first 2 files
                print(f"    - {filename}")
            if len(files_for_id) > 2:
                print(f"    ... and {len(files_for_id) - 2} more")
        
        if len(id_groups) > 10:
            print(f"  ... and {len(id_groups) - 10} more IDs")

if __name__ == "__main__":
    main()