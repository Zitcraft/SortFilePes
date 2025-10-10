"""
Export PES files to DST format with naming convention for embroidery machines
Handles single/multi-face items and groups by hash folders
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import pyembroidery


def parse_pes_filename(filename):
    """
    Parse PES filename to extract components
    Format: ID_ITEM_POSITION_SIZE_GARMENT_TOTAL_CURRENT_item_NUM.pes
    Example: 1997_2282_front_L_Sweatshirt_1_1_item_1.pes
    Example: 2150_2448_sleeve_left_L_Sweatshirt_2_2_item_1.pes
    """
    # Updated pattern to handle positions with underscores like sleeve_left, sleeve_right
    pattern = r'^(\d+)_(\d+)_([^_]+(?:_[^_]+)?)_([^_]+)_([^_]+)_(\d+)_(\d+)_item_(\d+)\.pes$'
    match = re.match(pattern, filename)
    
    if match:
        return {
            'id': int(match.group(1)),
            'item': int(match.group(2)),
            'position': match.group(3),  # front, sleeve_left, sleeve_right, etc.
            'size': match.group(4),
            'garment': match.group(5),
            'total_faces': int(match.group(6)),
            'current_face': int(match.group(7)),
            'item_num': int(match.group(8))
        }
    return None


def get_position_code(position):
    """Convert position to single character code"""
    position_map = {
        'front': 'F',
        'sleeve_left': 'L',
        'sleeve_right': 'R',
        'back': 'B',
        'chest': 'C',
        'pocket': 'P'
    }
    return position_map.get(position.lower(), 'F')


def get_month_code():
    """Get current month as alphabet (a=Jan, b=Feb, ..., j=Oct)"""
    month = datetime.now().month
    return chr(ord('a') + month - 1)


def generate_dst_name(folder_order, person, total_faces, position, day):
    """
    Generate DST filename according to specification
    Format: XXXYLZMDD.dst (max 9 chars for display, but we can save with full name)
    """
    month_code = get_month_code()
    position_code = get_position_code(position)
    
    # Build name: folder_order(3) + person(1) + total_faces(1) + position(1) + day(2) + month(1)
    dst_name = f"{folder_order:03d}{person}{total_faces}{position_code}{day:02d}{month_code}.dst"
    
    return dst_name


def scan_sorted_folders(sorted_dir):
    """
    Scan sorted folders to collect PES files info
    Returns: dict with folder info and PES files
    """
    sorted_path = Path(sorted_dir)
    folder_info = {}
    
    # Scan person folders (A, B, C)
    for person_dir in sorted_path.glob("[A-Z]"):
        if not person_dir.is_dir():
            continue
            
        person = person_dir.name
        folder_info[person] = {}
        
        # Scan hash folders within person folder
        for hash_dir in person_dir.glob("*_*"):
            if not hash_dir.is_dir():
                continue
                
            # Extract folder order from folder name (e.g., "014_3edcb035" -> 014)
            folder_name = hash_dir.name
            try:
                folder_order = int(folder_name.split('_')[0])
            except (ValueError, IndexError):
                continue
                
            # Scan PES files in this folder
            pes_files = list(hash_dir.glob("*.pes"))
            if not pes_files:
                continue
                
            folder_info[person][folder_order] = {
                'folder_name': folder_name,
                'folder_path': hash_dir,
                'pes_files': []
            }
            
            # Parse each PES file
            for pes_file in pes_files:
                parsed = parse_pes_filename(pes_file.name)
                if parsed:
                    parsed['file_path'] = pes_file
                    folder_info[person][folder_order]['pes_files'].append(parsed)
    
    return folder_info


def group_files_for_dst_export(folder_info):
    """
    Group PES files for DST export
    - Multi-face items: each position gets separate DST 
    - Same hash folder with single position: group into 1 DST
    """
    export_jobs = []
    
    # First collect all PES files across all folders
    all_pes_files = []
    for person, person_folders in folder_info.items():
        for folder_order, folder_data in person_folders.items():
            for pes_file in folder_data['pes_files']:
                pes_file['person'] = person
                pes_file['folder_order'] = folder_order
                pes_file['folder_name'] = folder_data['folder_name']
                pes_file['folder_path'] = folder_data['folder_path']
                all_pes_files.append(pes_file)
    
    # Group by person, item_id, and position to handle multi-face items correctly
    item_position_groups = defaultdict(list)
    
    for pes_file in all_pes_files:
        key = (pes_file['person'], pes_file['item'], pes_file['position'])
        item_position_groups[key].append(pes_file)
    
    # Create DST jobs for each unique item-position combination
    for (person, item_id, position), files in item_position_groups.items():
        if not files:
            continue
            
        # Get representative file for metadata
        representative_file = files[0]
        total_faces = representative_file['total_faces']
        
        # For naming, use the first file's folder order
        folder_order = representative_file['folder_order']
        
        dst_name = generate_dst_name(
            folder_order, person, total_faces, position, datetime.now().day
        )
        
        # Get person folder path (parent of hash folders)
        person_folder_path = representative_file['folder_path'].parent
        
        export_jobs.append({
            'dst_name': dst_name,
            'person': person,
            'folder_order': folder_order,
            'folder_name': representative_file['folder_name'],
            'items': [item_id],
            'position': position,
            'total_faces': total_faces,
            'pes_files': files,
            'dst_path': person_folder_path / 'dst' / dst_name
        })
    
    return export_jobs


def export_pes_to_dst(pes_file_path, dst_file_path):
    """
    Convert PES file to DST format using pyembroidery
    """
    try:
        # Read PES file
        pattern = pyembroidery.read(str(pes_file_path))
        
        # Ensure dst directory exists
        dst_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write as DST
        pyembroidery.write_dst(pattern, str(dst_file_path))
        return True
        
    except Exception as e:
        print(f"❌ Error converting {pes_file_path} to DST: {e}")
        return False


def create_mapping_log(export_jobs, log_path):
    """
    Create JSON log for DST to label mapping
    """
    mapping_data = {
        'export_date': datetime.now().isoformat(),
        'total_dst_files': len(export_jobs),
        'naming_convention': {
            'format': 'XXXYLZMDD.dst',
            'XXX': 'folder_order (3 digits)',
            'Y': 'person (A/B/C)',
            'L': 'total_faces of item',
            'Z': 'position (F=front, L=sleeve_left, R=sleeve_right)',
            'MM': 'day (01-31)',
            'D': 'month_code (a=Jan, b=Feb, ..., j=Oct)'
        },
        'mappings': []
    }
    
    for job in export_jobs:
        # Create mapping entry
        mapping_entry = {
            'dst_name': job['dst_name'],
            'person': job['person'],
            'folder_order': job['folder_order'],
            'folder_name': job['folder_name'],
            'items': job['items'],
            'position': job['position'],
            'total_faces': job['total_faces'],
            'pes_files': [f['file_path'].name for f in job['pes_files']],
            'label_patterns': [
                f"{f['id']}_{f['item']}_1_1_item_1.png" 
                for f in job['pes_files']
            ],
            'dst_path': str(job['dst_path'])
        }
        mapping_data['mappings'].append(mapping_entry)
    
    # Save JSON log
    log_path = Path(log_path)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f, indent=2, ensure_ascii=False)
    
    print(f"📋 Mapping log saved: {log_path}")
    
    return mapping_data


def main():
    """Main function to export DST files"""
    print("=" * 60)
    print("DST FILE EXPORTER")
    print("=" * 60)
    print()
    
    # Show what will happen
    print("Xuất file DST từ file PES đã phân loại:")
    print("- Nguồn: sorted/*/")
    print("- Đích: sorted/*/dst/")
    print("- Định dạng: XXXYLZMDD.dst")
    print("- Xử lý multi-face items (front, sleeve_left, sleeve_right)")
    print()
    
    confirm = input("Bạn có muốn tiếp tục? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Đã hủy bỏ.")
        return
    print()
    
    sorted_dir = "sorted"
    
    print("🎯 DST Export Tool")
    print("=" * 50)
    
    # Check if sorted directory exists
    sorted_path = Path(sorted_dir)
    if not sorted_path.exists():
        print(f"❌ Sorted directory not found: {sorted_dir}")
        print("Please run the sort script first.")
        return
    
    # Create output directory and log paths
    output_dir = sorted_path / "output"
    output_dir.mkdir(exist_ok=True)
    log_path = output_dir / "dst_export_log.json"
    
    # Scan folders and collect PES files
    print("📁 Scanning sorted folders...")
    folder_info = scan_sorted_folders(sorted_dir)
    
    total_folders = sum(len(person_folders) for person_folders in folder_info.values())
    total_pes = sum(
        len(folder_data['pes_files']) 
        for person_folders in folder_info.values() 
        for folder_data in person_folders.values()
    )
    
    print(f"Found {total_folders} hash folders with {total_pes} PES files")
    
    # Group files for DST export
    print("🔄 Grouping files for DST export...")
    export_jobs = group_files_for_dst_export(folder_info)
    
    print(f"Generated {len(export_jobs)} DST export jobs")
    
    # Show sample jobs
    print("\n📋 Sample DST export jobs:")
    for i, job in enumerate(export_jobs[:5]):
        print(f"  {job['dst_name']} ← {len(job['pes_files'])} PES files from folder {job['folder_name']}")
    
    if len(export_jobs) > 5:
        print(f"  ... and {len(export_jobs) - 5} more jobs")
    
    # Export DST files
    print(f"\n⚙️  Exporting {len(export_jobs)} DST files...")
    
    success_count = 0
    error_count = 0
    
    for i, job in enumerate(export_jobs):
        print(f"Processing {i+1}/{len(export_jobs)}: {job['dst_name']}")
        
        # For same hash folder, use the first PES file as template
        # (since they should have same embroidery pattern)
        source_pes = job['pes_files'][0]['file_path']
        
        success = export_pes_to_dst(source_pes, job['dst_path'])
        
        if success:
            success_count += 1
            print(f"✅ {job['dst_name']}")
        else:
            error_count += 1
    
    # Create mapping log
    print(f"\n📝 Creating mapping log...")
    create_mapping_log(export_jobs, log_path)
    
    # Final summary
    print(f"\n🎉 Export Summary:")
    print(f"  DST files created: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"  Mapping log saved: {log_path}")
    
    # Show folder structure
    print(f"\n📂 DST files location:")
    for person in sorted(folder_info.keys()):
        person_dst_count = sum(1 for job in export_jobs if job['person'] == person)
        print(f"  {sorted_dir}/{person}/dst/ ({person_dst_count} DST files)")
    
    print("Done!")


if __name__ == "__main__":
    main()