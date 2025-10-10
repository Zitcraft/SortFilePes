"""
File operations for organizing and managing embroidery files
"""

import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from .config import Config


class FileOperations:
    """Handles file organization, moving, and folder creation"""
    
    @staticmethod
    def calculate_folder_order(file_meta: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate folder order for each hash based on first-seen order"""
        order = {}
        index = 1
        for m in file_meta:
            h8 = m.get("hash")
            if h8 and h8 not in order:
                order[h8] = index
                index += 1
        return order
    
    @staticmethod
    def timestamped_path(p: Path) -> Path:
        """Return a new Path that appends YYYYMMDD_HHMMSS before the suffix."""
        ts = datetime.now().strftime(Config.TIMESTAMP_FORMAT)
        return p.with_name(f"{p.stem}_{ts}{p.suffix}")

    @staticmethod
    def group_into_person_folders(file_meta: List[Dict[str, Any]], 
                                dst: Path, 
                                move: bool = True, 
                                person_labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Place files into dst/<PersonLabel>/{NNN_hash8}/ folders according to file_meta['person'].
        
        Keeps numbering stable by assigning an index to each unique hash in first-seen order.
        Returns updated_meta list with dst_path set.
        """
        if person_labels is None:
            person_labels = Config.DEFAULT_PERSON_LABELS
        dst.mkdir(parents=True, exist_ok=True)

        order = {}
        index = 1
        updated_meta = []

        # determine order by first-seen hash
        for m in file_meta:
            h8 = m["hash"]
            if h8 not in order:
                order[h8] = index
                index += 1

        for m in file_meta:
            person_idx = m.get("person")
            if person_idx is None or not (0 <= person_idx < len(person_labels)):
                # default to first person if unassigned
                person_idx = 0
            label = person_labels[person_idx]
            h8 = m["hash"]
            grp_name = f"{order[h8]:03d}_{h8}"
            grp_path = dst / label / grp_name
            grp_path.mkdir(parents=True, exist_ok=True)

            dest = grp_path / m["name"]
            dest = FileOperations._ensure_unique_filename(dest)

            if move:
                shutil.move(str(m["path"]), str(dest))
            else:
                shutil.copy2(str(m["path"]), str(dest))

            newm = dict(m)
            newm["dst_path"] = dest
            newm["person_label"] = label
            updated_meta.append(newm)
            print(f"Assigned {m['name']} -> {label}/{grp_name}/")

        return updated_meta

    @staticmethod
    def group_and_move_files(file_meta: List[Dict[str, Any]], 
                           dst: Path, 
                           move: bool = True) -> tuple[List[Dict[str, Any]], Dict[str, Path]]:
        """Create hash-group folders under dst and move/copy files there. 
        
        Returns mapping hash->folder and updated paths.
        """
        dst.mkdir(parents=True, exist_ok=True)
        order = {}
        index = 1
        hash_folder = {}

        updated_meta = []
        for m in file_meta:
            h8 = m["hash"]
            if h8 not in order:
                order[h8] = index
                index += 1
            grp_name = f"{order[h8]:03d}_{h8}"
            grp_path = dst / grp_name
            grp_path.mkdir(parents=True, exist_ok=True)

            dest = grp_path / m["name"]
            dest = FileOperations._ensure_unique_filename(dest)

            if move:
                shutil.move(str(m["path"]), str(dest))
            else:
                shutil.copy2(str(m["path"]), str(dest))

            newm = dict(m)
            newm["dst_path"] = dest
            updated_meta.append(newm)
            hash_folder[h8] = grp_path
            print(f"Assigned {m['name']} -> {grp_name}/")

        return updated_meta, hash_folder

    @staticmethod
    def _ensure_unique_filename(dest: Path) -> Path:
        """Ensure filename is unique by appending number if needed"""
        if not dest.exists():
            return dest
            
        base = dest.stem
        ext = dest.suffix
        parent = dest.parent
        i = 1
        while True:
            new_name = f"{base}_{i}{ext}"
            new_dest = parent / new_name
            if not new_dest.exists():
                return new_dest
            i += 1