"""
Time estimation functionality for embroidery patterns
"""

from pathlib import Path
from typing import Dict, Any, Optional

from .config import Config

try:
    from pyembroidery.EmbPattern import EmbPattern
except Exception:
    EmbPattern = None


class TimeEstimator:
    """Time estimation for embroidery patterns"""
    
    def __init__(self, config_params: Optional[Dict[str, float]] = None):
        """Initialize with configuration parameters"""
        if config_params is None:
            config_params = Config.get_time_params()
        
        self.stitches_per_minute = config_params.get('stitches_per_minute', Config.STITCHES_PER_MINUTE)
        self.color_change_seconds = config_params.get('color_change_seconds', Config.COLOR_CHANGE_SECONDS)
        self.trim_seconds = config_params.get('trim_seconds', Config.TRIM_SECONDS)
        self.jump_seconds = config_params.get('jump_seconds', Config.JUMP_SECONDS)

    @staticmethod
    def human_readable(seconds: float) -> str:
        """Convert seconds to a human-friendly string (Xm Ys)."""
        m, s = divmod(int(round(seconds)), 60)
        return f"{m}m {s}s" if m else f"{s}s"

    def estimate_embroidery_time_for_path(self, path: Path) -> float:
        """Estimate embroidery seconds for a PES file, based on stitches, colors, trims, jumps.
        
        Returns seconds (float).
        """
        # Load pattern
        if EmbPattern is None:
            # If pyembroidery not available, fallback to 0
            return 0.0

        pattern = EmbPattern()
        # try several loader methods (some pyembroidery versions differ)
        for method_name in ("load", "read", "open"):
            method = getattr(pattern, method_name, None)
            if callable(method):
                try:
                    method(str(path))
                    break
                except Exception:
                    continue
        else:
            return 0.0

        return self._calculate_time_from_pattern(pattern)

    def _calculate_time_from_pattern(self, pattern) -> float:
        """Calculate time from loaded pattern object"""
        stitches = len(getattr(pattern, "stitches", []) or [])

        thread_list = getattr(pattern, "threadlist", None) or getattr(pattern, "threads", None)
        color_changes = len(thread_list) if thread_list else 0

        trims = jumps = 0
        for item in getattr(pattern, "stitches", []) or []:
            try:
                cmd = item[2]
            except Exception:
                cmd = 0
            if cmd == Config.TRIM_CODE:
                trims += 1
            elif cmd == Config.JUMP_CODE:
                jumps += 1

        stitch_time = stitches / self.stitches_per_minute * 60.0
        color_time = color_changes * self.color_change_seconds
        trim_time = trims * self.trim_seconds
        jump_time = jumps * self.jump_seconds

        total_seconds = stitch_time + color_time + trim_time + jump_time
        return float(total_seconds)

    def estimate_time_for_files(self, file_meta_list: list) -> list:
        """Estimate time for a list of file metadata and add 'seconds' field"""
        updated_meta = []
        for m in file_meta_list:
            try:
                sec = self.estimate_embroidery_time_for_path(m["path"])
            except Exception:
                sec = 0.0
            
            new_m = dict(m)
            new_m["seconds"] = sec
            updated_meta.append(new_m)
        
        return updated_meta