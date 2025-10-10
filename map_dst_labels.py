#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DST Label Mapper
Maps DST content from export log to PNG labels based on item IDs.
Only processes labels that have corresponding DST mappings.
"""

import json
import os
import argparse
import shutil
from PIL import Image, ImageDraw, ImageFont
from collections import defaultdict
import sys

def load_dst_log(log_path="sorted/output/dst_export_log.json"):
    """Load DST export log and group by item IDs."""
    if not os.path.exists(log_path):
        print(f"Error: DST log file not found: {log_path}")
        return None
    
    with open(log_path, 'r', encoding='utf-8') as f:
        log_data = json.load(f)
    
    # Group DST mappings by item ID with person information
    item_dst_map = defaultdict(lambda: {'dst_names': set(), 'person': None})
    
    for mapping in log_data.get('mappings', []):
        items = mapping.get('items', [])
        dst_name = mapping.get('dst_name', '').replace('.dst', '')  # Remove .dst extension
        person = mapping.get('person', 'A')  # Get person assignment
        
        for item_id in items:
            item_dst_map[item_id]['dst_names'].add(dst_name)
            item_dst_map[item_id]['person'] = person
    
    # Convert to final format
    result = {}
    for item_id, data in item_dst_map.items():
        result[item_id] = {
            'dst_names': sorted(list(data['dst_names'])),
            'person': data['person']
        }
    
    print(f"Loaded DST mappings for {len(result)} items")
    return result

def find_source_label_files():
    """Find all PNG label files in files/labels/ directory."""
    labels_dir = "files/labels"
    if not os.path.exists(labels_dir):
        print(f"Error: Labels directory not found: {labels_dir}")
        return []
    
    label_files = []
    for file in os.listdir(labels_dir):
        if file.endswith('.png'):
            label_files.append(os.path.join(labels_dir, file))
    
    print(f"Found {len(label_files)} PNG label files in {labels_dir}")
    return label_files

def extract_item_id_from_filename(filename):
    """Extract item ID from PNG filename pattern: XXXX_YYYY_1_1_item_1.png"""
    try:
        basename = os.path.basename(filename)
        parts = basename.replace('.png', '').split('_')
        
        # Pattern: order_item_1_1_item_1.png
        if len(parts) >= 2:
            return int(parts[1])  # Second element is item ID
    except (ValueError, IndexError):
        pass
    
    return None

def get_font():
    """Get font for text rendering."""
    try:
        # Try to use a system font
        return ImageFont.truetype("arial.ttf", 14)
    except:
        try:
            return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
        except:
            return ImageFont.load_default()

def process_label_image(image_path, dst_names):
    """Process a single label image to add DST content."""
    try:
        # Open image
        img = Image.open(image_path).convert('RGBA')
        
        # Verify image dimensions (should be 289x162 at 96 DPI)
        if img.size != (289, 162):
            print(f"Warning: {os.path.basename(image_path)} has unexpected size {img.size}, expected (289, 162)")
        
        # Get bounding box of non-transparent content
        bbox = img.getbbox()
        if bbox is None:
            print(f"Warning: {os.path.basename(image_path)} appears to be empty")
            return False
        
        # Create new image with same size
        new_img = Image.new('RGBA', (289, 162), (255, 255, 255, 0))
        
        # Calculate position to place content at bottom
        content_width = bbox[2] - bbox[0]
        content_height = bbox[3] - bbox[1]
        
        # Position content at bottom center
        paste_x = (289 - content_width) // 2
        paste_y = 162 - content_height - 5  # 5px margin from bottom
        
        # Crop original content and paste to new position
        content = img.crop(bbox)
        new_img.paste(content, (paste_x, paste_y), content)
        
        # Prepare DST text
        if len(dst_names) == 1:
            dst_text = dst_names[0]
        else:
            dst_text = " | ".join(dst_names)
        
        # Add DST text at top-left
        draw = ImageDraw.Draw(new_img)
        font = get_font()
        
        # Add text with black color
        text_x = 5  # 5px margin from left
        text_y = 5  # 5px margin from top
        draw.text((text_x, text_y), dst_text, fill=(0, 0, 0, 255), font=font)
        
        # Save processed image
        new_img.save(image_path)
        return True
        
    except Exception as e:
        print(f"Error processing {os.path.basename(image_path)}: {e}")
        return False

def move_and_process_label(source_path, item_id, dst_info, move_files=True):
    """Move/copy label to correct person folder and process it."""
    person = dst_info['person']
    dst_names = dst_info['dst_names']
    
    # Extract DST number from first DST name (e.g., "001A1F09j" -> "001")
    first_dst = dst_names[0] if dst_names else ""
    dst_number = ""
    if first_dst and len(first_dst) >= 3:
        try:
            # Extract first 3 digits
            dst_number = first_dst[:3]
            int(dst_number)  # Verify it's numeric
        except ValueError:
            dst_number = ""
    
    # Create new filename with DST number prefix
    original_filename = os.path.basename(source_path)
    if dst_number:
        new_filename = f"{dst_number}_{original_filename}"
    else:
        new_filename = original_filename
    
    # Create destination path
    dest_dir = f"sorted/{person}/labels"
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, new_filename)
    
    # Move or copy the file
    try:
        if move_files:
            shutil.move(source_path, dest_path)
            action = "moved"
        else:
            shutil.copy2(source_path, dest_path)
            action = "copied"
        
        # Process the image to add DST text
        if process_label_image(dest_path, dst_names):
            print(f"[SUCCESS] {action.capitalize()} and processed: {original_filename} -> {new_filename} -> Person {person} -> DST: {dst_names}")
            return True
        else:
            print(f"[WARNING] {action.capitalize()} but failed to process: {new_filename}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Failed to {action} {original_filename} -> {new_filename}: {e}")
        return False

def main():
    """Main function to process all label files."""
    parser = argparse.ArgumentParser(description='Map DST content to PNG labels based on export log')
    parser.add_argument('--copy', action='store_true', help='Copy files instead of moving (default: move)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("DST LABEL MAPPER")
    print("=" * 60)
    print()
    
    # Show what will happen
    action = "Copy" if args.copy else "Move"
    print("Gan ten DST vao nhan PNG:")
    print("- Doc log: sorted/output/dst_export_log.json")
    print(f"- {action} tu: files/labels/*.png")
    print("- Den: sorted/*/labels/*.png (chi nhung item co DST)")
    print("- Gan DST vao goc tren-trai")
    print("- Multi-face: 'DST1 | DST2 | DST3'")
    print()
    
    confirm = input("Ban co muon tiep tuc? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Da huy bo.")
        return
    print()
    
    print("DST Label Mapper")
    print("================")
    print()
    
    # Load DST mappings
    item_dst_map = load_dst_log()
    if not item_dst_map:
        return
    
    # Find label files in source directory
    label_files = find_source_label_files()
    if not label_files:
        print("No PNG label files found in files/labels/")
        return
    
    # Process each label file
    processed_count = 0
    skipped_count = 0
    
    for label_path in label_files:
        item_id = extract_item_id_from_filename(label_path)
        
        if item_id is None:
            print(f"Could not extract item ID from: {os.path.basename(label_path)}")
            skipped_count += 1
            continue
        
        if item_id not in item_dst_map:
            print(f"No DST mapping found for item {item_id} in {os.path.basename(label_path)} - keeping in files/labels/")
            skipped_count += 1
            continue
        
        dst_info = item_dst_map[item_id]
        if move_and_process_label(label_path, item_id, dst_info, move_files=not args.copy):
            processed_count += 1
        else:
            skipped_count += 1
    
    print("\n" + "="*50)
    print(f"Processing complete!")
    print(f"Processed: {processed_count} files")
    print(f"Skipped: {skipped_count} files")
    print(f"Total: {len(label_files)} files")
    
    # Show examples of multi-face items
    multi_face_items = {k: v for k, v in item_dst_map.items() if len(v['dst_names']) > 1}
    if multi_face_items:
        print(f"\nMulti-face items processed:")
        for item_id, info in sorted(multi_face_items.items()):
            dst_names = info['dst_names']
            person = info['person']
            print(f"  Item {item_id} (Person {person}): {' | '.join(dst_names)}")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()