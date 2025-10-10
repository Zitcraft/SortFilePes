"""
Workload assignment functionality for distributing embroidery work among people
"""

from typing import List, Dict, Any, Optional, Tuple

from .config import Config


class WorkloadAssignment:
    """Handles workload assignment and balancing for embroidery work"""
    
    def __init__(self, config_params: Optional[Dict[str, Any]] = None):
        """Initialize with configuration parameters"""
        if config_params is None:
            config_params = Config.get_assignment_params()
        
        self.people_count = config_params.get('people_count', Config.DEFAULT_PEOPLE_COUNT)
        self.person_labels = config_params.get('person_labels', Config.DEFAULT_PERSON_LABELS.copy())
        self.duplicate_reduction = config_params.get('duplicate_reduction', Config.DUPLICATE_REDUCTION_SECONDS)

    def make_components(self, file_meta: List[Dict[str, Any]]) -> List[List[int]]:
        """Build connected components where files sharing hash or id_item are linked.
        
        Returns list of components; each component is list of indices into file_meta.
        """
        n = len(file_meta)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra = find(a)
            rb = find(b)
            if ra != rb:
                parent[rb] = ra

        hash_map = {}
        id_map = {}
        for i, m in enumerate(file_meta):
            hash_map.setdefault(m["hash"], []).append(i)
            if m.get("id_item"):
                id_map.setdefault(m["id_item"], []).append(i)

        for lst in hash_map.values():
            for i in range(1, len(lst)):
                union(lst[0], lst[i])
        for lst in id_map.values():
            for i in range(1, len(lst)):
                union(lst[0], lst[i])

        comps = {}
        for i in range(n):
            r = find(i)
            comps.setdefault(r, []).append(i)
        return list(comps.values())

    def assign_components_to_people(self, file_meta: List[Dict[str, Any]], 
                                  comps: List[List[int]]) -> Tuple[List[int], List[float]]:
        """Assign components to people buckets balancing adjusted time.
        
        Duplicate reduction: for each hash inside a component, reduce duplicate_reduction per duplicate beyond first.
        Returns assignment list mapping file index -> person index and bucket totals.
        """
        comp_times = []
        for comp in comps:
            # base sum
            s = sum(file_meta[i]["seconds"] for i in comp)
            # reduction per-hash inside comp
            counts = {}
            for i in comp:
                counts[file_meta[i]["hash"]] = counts.get(file_meta[i]["hash"], 0) + 1
            reduction = sum((cnt - 1) * self.duplicate_reduction for cnt in counts.values() if cnt > 1)
            adjusted = max(0.0, s - reduction)
            comp_times.append((comp, adjusted))

        # sort components by descending adjusted time
        comp_times.sort(key=lambda x: x[1], reverse=True)

        buckets = [0.0] * self.people_count
        assignment = [0] * len(file_meta)  # Initialize with zeros

        for comp, t in comp_times:
            # choose person with minimal current load
            person = min(range(self.people_count), key=lambda p: buckets[p])
            buckets[person] += t
            for idx in comp:
                assignment[idx] = person

        return assignment, buckets

    def add_person_assignments(self, file_meta: List[Dict[str, Any]], 
                             assignment: List[int]) -> List[Dict[str, Any]]:
        """Add person assignment info to file metadata"""
        updated_meta = []
        for i, m in enumerate(file_meta):
            new_m = dict(m)
            person_idx = assignment[i]
            new_m["person"] = person_idx
            if person_idx < len(self.person_labels):
                new_m["person_label"] = self.person_labels[person_idx]
            else:
                new_m["person_label"] = f"Person_{person_idx}"
            updated_meta.append(new_m)
        return updated_meta

    def get_assignment_summary(self, file_meta: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Generate summary statistics per person"""
        summary = {}
        
        # Group files by person
        people_files = {label: [] for label in self.person_labels}
        for m in file_meta:
            label = m.get("person_label", self.person_labels[0])
            if label in people_files:
                people_files[label].append(m)
        
        # Calculate statistics for each group
        for label in self.person_labels:
            files = people_files[label]
            total_secs = sum(m.get("seconds", 0.0) for m in files)
            
            # Calculate unique id_items and unique hashes
            id_items = set()
            unique_hashes = set()
            counts = {}
            for m in files:
                hash_val = m.get("hash")
                if hash_val:
                    unique_hashes.add(hash_val)
                counts[hash_val] = counts.get(hash_val, 0) + 1
                if m.get("id_item") is not None:
                    id_items.add(m.get("id_item"))
            
            # Calculate adjusted time with duplicate reduction
            reduction = sum((cnt - 1) * self.duplicate_reduction for cnt in counts.values() if cnt > 1)
            adjusted = max(0.0, total_secs - reduction)
            
            summary[label] = {
                "file_count": len(files),
                "total_seconds": total_secs,
                "adjusted_seconds": adjusted,
                "unique_id_items": len(id_items),
                "unique_hashes": len(unique_hashes),
            }
        
        return summary