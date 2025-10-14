"""
Core embroidery pattern processing functionality
"""

import hashlib
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import Config

try:
    from pyembroidery.EmbPattern import EmbPattern
except Exception:
    EmbPattern = None


class EmbroideryCore:
    """Core functionality for embroidery pattern analysis and hashing"""
    
    @staticmethod
    def canonical_bytes_from_pattern(pat) -> bytes:
        """Return a stable, canonical bytes representation for hashing.
        
        Uses integer-rounded coordinates for stitches and thread color/catalog metadata.
        """
        parts = []
        # Stitches: use integer-rounded coords to avoid float precision differences
        for s in getattr(pat, "stitches", []):
            x = int(round(s[0]))
            y = int(round(s[1]))
            cmd = int(s[2])
            parts.append(f"S:{x},{y},{cmd}")

        # Threads: include color and catalog/description values if present
        for t in getattr(pat, "threadlist", []):
            color = getattr(t, "color", 0)
            catalog = getattr(t, "catalog_number", "") or ""
            desc = getattr(t, "description", "") or ""
            parts.append(f"T:{int(color)}|{catalog}|{desc}")

        # Extras: include common extras that may affect appearance
        extras = getattr(pat, "extras", {}) or {}
        if extras:
            for k in sorted(extras.keys()):
                parts.append(f"E:{k}={extras[k]}")

        canonical = ";".join(parts).encode("utf-8")
        return canonical

    @staticmethod
    def hash_file_by_pattern(path: Path) -> str:
        """Compute an 8-char hex hash for a PES file path.
        
        Tries to load with pyembroidery. If unavailable or fails, falls back to raw file sha256.
        """
        # Try using pyembroidery if available
        if EmbPattern is not None:
            try:
                pat = EmbPattern(str(path))
                cb = EmbroideryCore.canonical_bytes_from_pattern(pat)
                h = hashlib.sha256(cb).hexdigest()[:Config.DEFAULT_HASH_LENGTH]
                return h
            except Exception:
                # Continue to fallback
                pass

        # Fallback: hash raw file bytes
        with path.open("rb") as f:
            data = f.read()
        return hashlib.sha256(data).hexdigest()[:Config.DEFAULT_HASH_LENGTH]

    @staticmethod
    def scan_pes_files(src: Path) -> List[Dict[str, Any]]:
        """Scan source tree and return metadata list for each PES file.
        
        Returns list of dicts with keys: path (Path), name, hash8, id_item (str or None)
        """
        files = []
        for root, _dirs, fnames in os.walk(src):
            for fname in fnames:
                if not fname.lower().endswith(".pes"):
                    continue
                full = Path(root) / fname
                try:
                    h8 = EmbroideryCore.hash_file_by_pattern(full)
                except Exception as e:
                    print(f"Failed hashing {full}: {e}", file=sys.stderr)
                    continue

                # parse id_item: assume format like 1827_2081_... -> take second field
                parts = fname.split("_")
                id_item = parts[1] if len(parts) > 1 else None

                files.append({
                    "path": full, 
                    "name": fname, 
                    "hash": h8, 
                    "id_item": id_item
                })
        return files

    @staticmethod
    def scan_pes_files_from_sorted(sorted_dir: Path) -> List[Dict[str, Any]]:
        """Scan PES files from sorted structure (sorted/*/pes/*/*.pes or sorted/*/*/*.pes).
        
        Handles both new structure with pes subdirectories and legacy flat structure.
        Returns list of dicts with keys: path (Path), name, hash8, id_item (str or None)
        """
        files = []
        
        # Check if sorted directory exists
        if not sorted_dir.exists():
            print(f"Sorted directory does not exist: {sorted_dir}")
            return files
        
        # Scan person folders (A, B, C, D, etc.)
        for person_dir in sorted_dir.glob("[A-Z]*"):
            if not person_dir.is_dir():
                continue
                
            print(f"Scanning person folder: {person_dir.name}")
            
            # Check for pes subdirectory structure first
            pes_dir = person_dir / "pes"
            if pes_dir.exists():
                # New structure: sorted/A/pes/001_hash8/*.pes
                for hash_dir in pes_dir.glob("*_*"):
                    if not hash_dir.is_dir():
                        continue
                    
                    # Scan PES files in this hash folder
                    for pes_file in hash_dir.glob("*.pes"):
                        try:
                            h8 = EmbroideryCore.hash_file_by_pattern(pes_file)
                        except Exception as e:
                            print(f"Failed hashing {pes_file}: {e}", file=sys.stderr)
                            continue

                        # parse id_item: assume format like 1827_2081_... -> take second field
                        parts = pes_file.name.split("_")
                        id_item = parts[1] if len(parts) > 1 else None

                        files.append({
                            "path": pes_file, 
                            "name": pes_file.name, 
                            "hash": h8, 
                            "id_item": id_item
                        })
            else:
                # Legacy structure: sorted/A/001_hash8/*.pes (flat in person folder)
                for hash_dir in person_dir.glob("*_*"):
                    if not hash_dir.is_dir():
                        continue
                    
                    # Scan PES files in this hash folder
                    for pes_file in hash_dir.glob("*.pes"):
                        try:
                            h8 = EmbroideryCore.hash_file_by_pattern(pes_file)
                        except Exception as e:
                            print(f"Failed hashing {pes_file}: {e}", file=sys.stderr)
                            continue

                        # parse id_item: assume format like 1827_2081_... -> take second field
                        parts = pes_file.name.split("_")
                        id_item = parts[1] if len(parts) > 1 else None

                        files.append({
                            "path": pes_file, 
                            "name": pes_file.name, 
                            "hash": h8, 
                            "id_item": id_item
                        })
        
        print(f"Found {len(files)} PES files in sorted structure")
        return files

    @staticmethod
    def parse_id_item_from_filename(filename: str, index: int = 1) -> Optional[str]:
        """Parse id_item from filename by splitting on underscore and taking specified index.
        
        Args:
            filename: The filename to parse
            index: Index position after splitting on '_' (default: 1 for second element)
        
        Returns:
            id_item string or None if not found
        """
        parts = filename.split("_")
        return parts[index] if len(parts) > index else None