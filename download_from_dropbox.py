#!/usr/bin/env python3
"""
Script to copy files from Dropbox folders to local folders based on API ID list with multi-threading
"""

import os
import shutil
import requests
from pathlib import Path
from typing import List, Set, Tuple, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import argparse
from embroidery_sorter.workflow_logger import log_print, logged_input, get_logger

def get_order_ids_from_api() -> Set[int]:
    """Get order IDs from the API endpoint"""
    try:
        log_print("Fetching order IDs from API...")
        response = requests.get("https://lemiex.us/api/order-status", timeout=30)
        response.raise_for_status()
        
        data = response.json()
        log_print(f"API Response type: {type(data)}")
        
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
        
        log_print(f"Extracted {len(ids)} unique IDs from API")
        if ids:
            log_print(f"Sample IDs: {sorted(list(ids))[:10]}...")
        
        return ids
        
    except requests.exceptions.RequestException as e:
        log_print(f"Error fetching from API: {e}")
        log_print("Continuing without API data...")
        return set()
    except Exception as e:
        log_print(f"Error parsing API response: {e}")
        log_print("Continuing without API data...")
        return set()

def filter_ids_by_range(ids: Set[int], start_id: Optional[int] = None, end_id: Optional[int] = None) -> Set[int]:
    """Filter IDs by range (inclusive)"""
    if not ids:
        return set()
    
    if start_id is None and end_id is None:
        return ids
    
    filtered_ids = set()
    for id_val in ids:
        if start_id is not None and id_val < start_id:
            continue
        if end_id is not None and id_val > end_id:
            continue
        filtered_ids.add(id_val)
    
    return filtered_ids

def get_range_from_user(all_ids: Set[int]) -> Tuple[Optional[int], Optional[int]]:
    """Get start and end range from user logged_input"""
    if not all_ids:
        return None, None
    
    sorted_ids = sorted(list(all_ids))
    min_id = sorted_ids[0]
    max_id = sorted_ids[-1]
    
    log_print(f"Available ID range: {min_id} - {max_id} ({len(all_ids)} total IDs)")
    log_print(f"Sample IDs: {sorted_ids[:10]}{'...' if len(sorted_ids) > 10 else ''}")
    log_print('')
    
    while True:
        try:
            start_logged_input = logged_input(f"Enter start ID (default: {min_id}): ").strip()
            start_id = int(start_logged_input) if start_logged_input else min_id
            
            end_logged_input = logged_input(f"Enter end ID (default: {max_id}): ").strip()
            end_id = int(end_logged_input) if end_logged_input else max_id
            
            if start_id > end_id:
                log_print("Start ID cannot be greater than end ID. Please try again.")
                continue
                
            return start_id, end_id
            
        except ValueError:
            log_print("Please enter valid numbers.")
        except KeyboardInterrupt:
            log_print("\nCancelled.")
            return None, None

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

def copy_files_from_folder(target_ids: Set[int], source_folder: Path, dest_folder: Path, folder_type: str) -> Dict[str, Any]:
    """Copy files from a specific Dropbox folder to destination folder"""
    log_print(f"\n=== Processing {folder_type.upper()} files ===")
    log_print(f"Source: {source_folder}")
    log_print(f"Destination: {dest_folder.absolute()}")
    
    if not source_folder.exists():
        log_print(f"❌ {folder_type.capitalize()} folder not found at {source_folder}")
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
    
    log_print(f"Found {len(source_files)} {folder_type} files")
    
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
                    log_print(message)
                
                # Progress indicator
                if completed % 20 == 0 or completed == total_tasks:
                    elapsed = time.time() - start_time
                    log_print(f"Progress: {completed}/{total_tasks} IDs processed ({completed/total_tasks*100:.1f}%) - {elapsed:.1f}s")
                    
            except Exception as e:
                log_print(f"❌ Error processing ID {target_id}: {e}")
                with copy_lock:
                    copy_stats['errors'] += 1
    
    elapsed_time = time.time() - start_time
    
    # Report results for this folder
    log_print(f"\n--- {folder_type.capitalize()} Summary ---")
    log_print(f"Execution time: {elapsed_time:.2f} seconds")
    log_print(f"Files copied: {copy_stats['copied']}")
    log_print(f"Copy errors: {copy_stats['errors']}")
    log_print(f"IDs found: {len(copy_stats['found_ids'])}")
    log_print(f"IDs not found: {len(copy_stats['missing_ids'])}")
    
    # Show missing IDs list
    if copy_stats['missing_ids']:
        missing_list = sorted(list(copy_stats['missing_ids']))
        log_print(f"Missing IDs: {missing_list}")
    
    if elapsed_time > 0:
        log_print(f"Copy speed: {copy_stats['copied']/elapsed_time:.1f} files/second")
    
    return {
        'copied': copy_stats['copied'],
        'errors': copy_stats['errors'],
        'found_ids': copy_stats['found_ids'],
        'missing_ids': copy_stats['missing_ids']
    }

def main():
    """Main function with argument parsing"""
    log_print("=" * 60)
    log_print("EMBROIDERY FILE DOWNLOADER")
    log_print("=" * 60)
    log_print('')
    
    # Show confirmation and options
    log_print("Tải file từ Dropbox về thư mục 'files/':")
    log_print("1. Design files (.pes) -> files/design/")
    log_print("2. Label files (.png/.pdf/.jpg/.svg) -> files/labels/")
    log_print('')
    
    parser = argparse.ArgumentParser(description='Copy files from Dropbox folders based on API IDs')
    parser.add_argument('--design', action='store_true', help='Copy design files (PES) from designpes folder')
    parser.add_argument('--label', action='store_true', help='Copy label files (PDF/PNG/JPG) from labels folder')
    parser.add_argument('--all', action='store_true', help='Copy both design and label files')
    parser.add_argument('--list', action='store_true', help='List files in Dropbox folders')
    parser.add_argument('--start', type=int, help='Start ID for range filtering (inclusive)')
    parser.add_argument('--end', type=int, help='End ID for range filtering (inclusive)')
    parser.add_argument('--range', action='store_true', help='Use interactive range selection')
    parser.add_argument('--ids', type=str, help='Comma-separated list of order IDs to download (e.g. 3784,3787,3788)')
    
    args = parser.parse_args()
    
    # Check for partial auto mode environment variables
    partial_auto = os.environ.get('PARTIAL_AUTO_MODE') == '1'
    auto_option = os.environ.get('AUTO_OPTION')
    auto_confirm = os.environ.get('AUTO_CONFIRM')
    
    # If no specific option is provided, show interactive prompt
    if not any([args.design, args.label, args.all, args.list, args.range, args.ids]):
        log_print("Chọn tùy chọn:")
        log_print("1. Tải chỉ design files (.pes)")
        log_print("2. Tải chỉ label files (.png/.pdf/.jpg/.svg)")
        log_print("3. Tải tất cả files")
        log_print("4. Liệt kê files trong Dropbox")
        log_print("5. Chọn range ID để tải")
        log_print("6. Nhập danh sách ID order thủ công (comma-separated)")
        log_print('')
        
        # Use auto option if in partial auto mode
        if partial_auto and auto_option:
            choice = auto_option
            log_print(f"🤖 Auto mode: Chọn option {choice}")
        else:
            choice = logged_input("Nhập lựa chọn (1-6) hoặc 'q' để thoát: ").strip()
        
        if choice == 'q':
            log_print("Đã hủy bỏ.")
            return
        elif choice == '1':
            args.design = True
        elif choice == '2':
            args.label = True
        elif choice == '3':
            args.all = True
        elif choice == '4':
            args.list = True
        elif choice == '5':
            args.range = True
            args.all = True  # Default to all files for range selection
        elif choice == '6':
            ids_logged_input = logged_input("Nhập danh sách ID (ví dụ: 3784,3787,3788): ").strip()
            if ids_logged_input:
                args.ids = ids_logged_input
                # parse below will convert to set
            else:
                log_print("Không có ID hợp lệ được nhập. Quay lại menu.")
                return
        else:
            log_print("Lựa chọn không hợp lệ. Mặc định tải design files.")
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
    
    log_print(f"{action}")
    
    # Use auto confirm if in partial auto mode
    if partial_auto and auto_confirm:
        confirm = auto_confirm
        log_print(f"🤖 Auto mode: Xác nhận '{confirm}'")
    else:
        confirm = logged_input("Bạn có muốn tiếp tục? (y/N): ").strip().lower()
    
    # if confirm not in ['y', 'yes']:
    #     log_print("Đã hủy bỏ.")
    #     return
    # log_print()
    
    # Create directories
    os.makedirs("files/design", exist_ok=True)
    os.makedirs("files/labels", exist_ok=True)
    
    # If user provided --ids or entered manual ids, parse them into a set; otherwise fetch from API
    if args.ids:
        try:
            provided = [int(x.strip()) for x in args.ids.split(',') if x.strip()]
            target_ids = set(provided)
            log_print(f"Using provided IDs: {sorted(list(target_ids))}")
            # If the user provided explicit IDs but didn't choose what to download,
            # default to downloading both design and labels to match interactive intent.
            if not any([args.design, args.label, args.all]):
                args.all = True
                log_print("No file type specified for provided IDs — defaulting to download both design and labels.")
        except Exception as e:
            log_print(f"Error parsing provided IDs: {e}")
            return
    else:
        target_ids = get_order_ids_from_api()

    if not target_ids:
        log_print("No IDs found. Exiting...")
        return

    # Show a clearer message depending on where IDs came from
    if args.ids:
        log_print(f"Total provided IDs: {len(target_ids)} IDs")
    else:
        log_print(f"Total IDs from API: {len(target_ids)} IDs")
    
    # Apply range filtering if specified
    if args.range or args.start is not None or args.end is not None:
        if args.range:
            # Interactive range selection
            range_values = get_range_from_user(target_ids)
            if range_values:
                target_ids = filter_ids_by_range(target_ids, range_values[0], range_values[1])
        else:
            # Command line range filtering
            target_ids = filter_ids_by_range(target_ids, args.start, args.end)
        
        if not target_ids:
            log_print("No IDs found in specified range. Exiting...")
            return
        
        log_print(f"Filtered IDs: {len(target_ids)} IDs")
    
    log_print(f"Target IDs for download: {sorted(list(target_ids))}")

    # Dropbox base path
    user_dir = os.path.expanduser("~")
    dropbox_base = Path(os.path.join(user_dir, "Dropbox"))
    
    total_copied = 0
    total_errors = 0
    all_missing_ids = []  # Collect all missing IDs
    
    # Process design files
    if args.design or args.all:
        design_source = dropbox_base / "designpes"
        design_dest = Path("files/design")
        design_stats = copy_files_from_folder(target_ids, design_source, design_dest, "design")
        total_copied += design_stats['copied']
        total_errors += design_stats['errors']
        all_missing_ids.extend(design_stats['missing_ids'])
    
    # Process label files
    if args.label or args.all:
        label_source = dropbox_base / "labels"
        label_dest = Path("files/labels")
        label_stats = copy_files_from_folder(target_ids, label_source, label_dest, "label")
        total_copied += label_stats['copied']
        total_errors += label_stats['errors']
        all_missing_ids.extend(label_stats['missing_ids'])
    
    # Final summary with complete missing IDs
    log_print(f"\n=== FINAL SUMMARY ===")
    log_print(f"Total files copied: {total_copied}")
    log_print(f"Total errors: {total_errors}")
    
    if all_missing_ids:
        # Remove duplicates and sort
        missing_list = sorted(list(set(all_missing_ids)))
        log_print(f"⚠️  Total IDs not found across all folders: {len(missing_list)}")
        log_print(f"Missing IDs: {missing_list}")
        
        # Ask if user wants to retry
        # log_print('')
        # retry = logged_input("Bạn có muốn thử tải lại các file bị thiếu? (y/N): ").strip().lower()
        # if retry in ['y', 'yes']:
        log_print("🔄 Đang cố gắng đồng bộ (sync) các ID bị thiếu trước khi tải lại...")
        re_download(missing_list, args)
    else:
        log_print("✅ All requested files found and copied successfully!")
    log_print('')

def check_order_blankshirt(id_list: List[int], api_key: str = "yoXIxxKk-3Ps5-i5IG-dri8") -> List[int]:
    """Return subset of ids that are blankshirt products by querying the order API."""
    blankshirt_ids = []
    for oid in id_list:
        try:
            url = f"https://lemiex.us/api/order/{oid}?api_key={api_key}"
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                log_print(f"Warning: order {oid} API returned {resp.status_code}")
                continue
            data = resp.json()
            items = data.get('items', [])
            for it in items:
                if isinstance(it, dict):
                    pname = it.get('product_name')
                    if isinstance(pname, str) and pname.lower() == 'blankshirt':
                        blankshirt_ids.append(oid)
                        break
        except Exception as e:
            log_print(f"Error checking order {oid}: {e}")
    return blankshirt_ids


def sync_missing_ids(missing_ids: List[int]) -> bool:
    """Call sync API to request Dropbox sync for missing IDs."""
    try:
        ids_param = ','.join(map(str, missing_ids))
        url = f"https://lemiex.us/api/sync-confirm?ids={ids_param}"
        log_print(f"Calling sync API: {url}")
        resp = requests.get(url, timeout=20)
        if resp.status_code in (200, 204):
            log_print("Sync request accepted")
            return True
        else:
            log_print(f"Sync API responded with status {resp.status_code}")
            return False
    except Exception as e:
        log_print(f"Error calling sync API: {e}")
        return False


def re_download(missing_ids: List[int], args):
    """Attempt to sync missing IDs then re-download up to 3 attempts.

    Labels are always downloaded. Design files are skipped for orders that are blankshirt.
    """
    log_print(f"Starting re-download for {len(missing_ids)} missing IDs")
    user_dir = os.path.expanduser("~")
    dropbox_base = Path(os.path.join(user_dir, "Dropbox"))

    if not dropbox_base.exists():
        log_print(f"❌ Dropbox folder not found: {dropbox_base}")
        return

    # Determine blankshirt IDs to skip design
    blank_ids = check_order_blankshirt(missing_ids)
    if blank_ids:
        log_print(f"Blankshirt IDs (will skip design): {blank_ids}")

    # Call sync initially, then poll Dropbox until all IDs recovered.
    remaining = set(missing_ids)

    log_print("Requesting initial sync for missing IDs...")
    sync_missing_ids(list(remaining))

    label_source = dropbox_base / "labels"
    design_source = dropbox_base / "designpes"
    label_dest = Path("files/labels")
    design_dest = Path("files/design")

    poll_count = 0
    # Poll until remaining is empty
    while remaining:
        poll_count += 1
        found_this_round = set()

        # Check each remaining ID for presence: labels (.png) required; design (.pes) required unless blankshirt
        for fid in list(remaining):
            label_found = False
            design_found = False

            # Check label (.png) presence
            if label_source.exists():
                # look for any png starting with fid_
                matches = list(label_source.glob(f"{fid}_*.png"))
                if matches:
                    label_found = True
            # Check design (.pes) presence unless blankshirt
            if fid in blank_ids:
                design_found = True
            else:
                if design_source.exists():
                    matches_design = list(design_source.glob(f"{fid}_*.pes"))
                    if matches_design:
                        design_found = True

            # If both present (or design skipped), copy files
            if label_found and design_found:
                # copy all label pngs for this fid
                try:
                    if label_source.exists():
                        for file in label_source.glob(f"{fid}_*.png"):
                            try:
                                dest_file = label_dest / file.name
                                if not dest_file.exists():
                                    shutil.copy2(file, dest_file)
                                    log_print(f"✅ Re-downloaded label: {file.name}")
                            except Exception as e:
                                log_print(f"Error copying label {file.name}: {e}")
                except Exception:
                    pass

                # copy all design pes for this fid (if not blankshirt)
                if fid not in blank_ids and design_source.exists():
                    try:
                        for file in design_source.glob(f"{fid}_*.pes"):
                            try:
                                dest_file = design_dest / file.name
                                if not dest_file.exists():
                                    shutil.copy2(file, dest_file)
                                    log_print(f"✅ Re-downloaded design: {file.name}")
                            except Exception as e:
                                log_print(f"Error copying design {file.name}: {e}")
                    except Exception:
                        pass

                found_this_round.add(fid)

        # Remove found IDs
        if found_this_round:
            remaining -= found_this_round
            log_print(f"Recovered IDs this poll: {sorted(list(found_this_round))}")
            log_print(f"IDs remaining: {sorted(list(remaining))}")
        else:
            log_print(f"No new files found in this poll. IDs still missing: {sorted(list(remaining))}")

        # Re-request sync every 18 polls (~180s if sleep 10s)
        if poll_count % 18 == 0:
            log_print("Re-requesting sync from API for remaining IDs...")
            sync_missing_ids(list(remaining))

        # Sleep between polls
        time.sleep(10)

    log_print("✅ All missing IDs recovered and re-downloaded.")

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
        log_print(f"\n=== {folder_name.upper()} FOLDER ===")
        log_print(f"Path: {folder_path}")
        
        if not folder_path.exists():
            log_print(f"❌ Folder not found")
            continue
        
        if folder_name == "labels":
            # Multiple extensions for labels
            files = []
            for ext in ['*.pdf', '*.png', '*.jpg', '*.jpeg', '*.svg']:
                files.extend(folder_path.glob(ext))
        else:
            files = list(folder_path.glob(pattern))
        
        log_print(f"Found {len(files)} files")
        
        # Group by ID for better overview
        id_groups = {}
        for file in files:
            parts = file.name.split("_")
            if parts and parts[0].isdigit():
                file_id = int(parts[0])
                if file_id not in id_groups:
                    id_groups[file_id] = []
                id_groups[file_id].append(file.name)
        
        log_print(f"Grouped into {len(id_groups)} unique IDs")
        for file_id in sorted(list(id_groups.keys())[:10]):  # Show first 10
            files_for_id = id_groups[file_id]
            log_print(f"  ID {file_id}: {len(files_for_id)} file(s)")
            for filename in files_for_id[:2]:  # Show first 2 files
                log_print(f"    - {filename}")
            if len(files_for_id) > 2:
                log_print(f"    ... and {len(files_for_id) - 2} more")
        
        if len(id_groups) > 10:
            log_print(f"  ... and {len(id_groups) - 10} more IDs")

if __name__ == "__main__":
    main()