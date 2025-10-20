#!/usr/bin/env python3
"""
Scan files/ (design and labels) and check that for each order ID the number of files
matches the "item_N" indicated in the filename.

Filename examples handled:
  2655_3023_front_L_Comfort_1_1_item_5.pes  -> order id 2655, items=5
  2149_2445_1_1_item_3.png                  -> order id 2149, items=3

Usage:
  python check_id_completeness.py            # scan files/design and files/labels
  python check_id_completeness.py --dir files --folders design labels --exts pes png

Reports a summary and a detailed list of IDs where actual file count != expected.
"""
from __future__ import annotations
import argparse
import os
import re
from collections import defaultdict
from typing import Dict, List, Tuple

# Capture optional faces info like _2_1_ (total_faces=2, face_index=1) before item_N
FILENAME_RE = re.compile(
    r"^(?P<order>\d+)_+(?P<subid>\d+).*item_(?P<items>\d+)\.(?P<ext>[^.]+)$",
    re.IGNORECASE,
)
# More robust face extractor: find a pair of digits like _2_1_ that appears before item_ in the filename
FACE_RE = re.compile(r"_(?P<faces_total>\d+)_(?P<face_index>\d+)(?=[^/]*item_)", re.IGNORECASE)


def scan_folder(folder: str, exts: List[str]) -> Dict[str, List[Tuple[str, int, int, int, int, str]]]:
    """
    Return a mapping order_id -> list of tuples
    (filename, subid, items, faces_total, face_index, ext)
    """
    mapping: Dict[str, List[Tuple[str, int, int, int, int, str]]] = defaultdict(list)
    if not os.path.isdir(folder):
        return mapping
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        m = FILENAME_RE.match(name)
        if not m:
            # skip files that don't match pattern
            continue
        ext = m.group('ext').lower()
        if exts and ext not in exts:
            continue
        order = m.group('order')
        subid = int(m.group('subid'))
        items = int(m.group('items'))
        # Try to robustly extract face info (e.g., _2_1_ before item_)
        face_m = FACE_RE.search(name)
        if face_m:
            faces_total_i = int(face_m.group('faces_total'))
            face_index_i = int(face_m.group('face_index'))
        else:
            faces_total_i = 1
            face_index_i = 1
        mapping[order].append((name, subid, items, faces_total_i, face_index_i, ext))
    return mapping


def analyze_mapping(mapping: Dict[str, List[Tuple[str, int, int, int, int, str]]], is_label: bool = False) -> List[Dict]:
    """
    For each order id produce a dict with analysis fields:
      order, expected_items, faces_per_item, expected_files, actual, per_subid info, missing_subids (guessed)
    """
    results = []
    for order, files in sorted(mapping.items(), key=lambda x: int(x[0])):
        filenames = [f[0] for f in files]
        # unique subids correspond to individual items
        subids = sorted({f[1] for f in files})
        items_vals = sorted({f[2] for f in files})
        faces_vals = sorted({f[3] for f in files})

        expected_items = items_vals[-1] if items_vals else None
        faces_per_item = faces_vals[-1] if faces_vals else 1

        expected_files = (expected_items or 0) * (faces_per_item or 1)
        actual = len(files)

        # Build per-subid info: found face indexes and observed faces_total per subid
        per_subid_info: Dict[int, Dict[str, object]] = {}
        for (_, subid, _items, faces_total_i, face_index_i, _ext) in files:
            info = per_subid_info.setdefault(subid, {'found': set(), 'faces_total_obs': set()})
            info['found'].add(face_index_i)
            info['faces_total_obs'].add(faces_total_i)

        # Determine expected faces per subid using observed per-subid faces_total if available, otherwise use faces_per_item
        per_subid_expected = {}
        per_subid_missing = {}
        for sid, info in per_subid_info.items():
            # prefer the maximum observed faces_total for that subid
            faces_expected = max(info['faces_total_obs']) if info['faces_total_obs'] else faces_per_item
            per_subid_expected[sid] = faces_expected
            missing = [i for i in range(1, faces_expected + 1) if i not in info['found']]
            if missing:
                per_subid_missing[sid] = missing

        # If unique subids < expected_items, try to guess missing subids by numeric range
        missing_subids = []
        if expected_items is not None and len(subids) < expected_items and subids:
            start = min(subids)
            candidate = list(range(start, start + expected_items))
            missing_subids = [s for s in candidate if s not in subids]

        # Compute expected_files as sum of expected faces for present subids plus guessed missing subids
        # For labels folder, consider uniqueness of subids as the primary check
        if is_label:
            # expected items from item_N, actual_items = number of unique subids
            actual_items = len(subids)
            # If unique subids < expected_items -> missing
            missing_subids = []
            if expected_items is not None and actual_items < expected_items and subids:
                start = min(subids)
                candidate = list(range(start, start + expected_items))
                missing_subids = [s for s in candidate if s not in subids]
            expected_files_precise = expected_items or 0
            results.append({
                'order': order,
                'expected_items': expected_items,
                'faces_per_item': faces_per_item,
                'expected_files': expected_files_precise,
                'actual': actual_items,
                'filenames': filenames,
                'subids': subids,
                'per_subid_missing': {},
                'missing_subids': missing_subids,
            })
        else:
            expected_files_precise = sum(per_subid_expected.values())
            if missing_subids:
                expected_files_precise += len(missing_subids) * (faces_per_item or 1)
            results.append({
                'order': order,
                'expected_items': expected_items,
                'faces_per_item': faces_per_item,
                'expected_files': expected_files_precise,
                'actual': actual,
                'filenames': filenames,
                'subids': subids,
                'per_subid_missing': per_subid_missing,
                'missing_subids': missing_subids,
            })
    return results


def print_report(title: str, results: List[Dict]):
    print('\n' + '=' * 60)
    print(title)
    print('=' * 60)
    total = len(results)
    # incomplete if expected_files known and mismatch
    incomplete = [r for r in results if r['expected_files'] is not None and r['actual'] != r['expected_files']]
    no_expected = [r for r in results if r['expected_items'] is None]
    print(f'Total distinct order IDs scanned: {total}')
    print(f'IDs with missing/extra files: {len(incomplete)}')
    # print(f'IDs where "item_N" could not be extracted: {len(no_expected)}')

    # if incomplete:
    #     print('\n-- Detailed mismatches --')
    #     for r in incomplete:
    #         print(f"Order ID: {r['order']}: expected {r['expected_items']} items x {r['faces_per_item']} faces = {r['expected_files']} files, found {r['actual']}")
    #         if r['missing_subids']:
    #             print(f"  Missing item subids (guessed): {r['missing_subids']}")
    #         # Do not print per-subid face missing details (keeps report concise).
    #         # show a short file sample (up to 6)
    #         sample = sorted(r['filenames'])[:6]
    #         print('  Sample present files:')
    #         for fn in sample:
    #             print('   -', fn)
    #         if len(r['filenames']) > len(sample):
    #             print(f"   ... and {len(r['filenames'])-len(sample)} more files")
    #         print('')

    if no_expected:
        print("\n-- Files that didn't match the expected filename pattern --")
        for r in no_expected:
            print(f"Order ID: {r['order']}, files: {len(r['filenames'])}")

    # Print a concise list of IDs with mismatches
    if incomplete:
        ids = [int(r['order']) for r in incomplete]
        ids.sort()
        print('\nSummary - IDs with mismatches:', ids)


def main():
    parser = argparse.ArgumentParser(description='Check order IDs have expected number of files in files/ folders')
    parser.add_argument('--dir', default='files', help='Base files directory (default: files)')
    parser.add_argument('--folders', nargs='+', default=['design', 'labels'], help='Subfolders to scan (default: design labels)')
    parser.add_argument('--exts', nargs='+', default=['pes', 'png'], help='Extensions to consider (default: pes png)')
    parser.add_argument('--report-csv', help='Optional CSV path to write a per-order report')
    args = parser.parse_args()

    base = os.path.abspath(args.dir)
    all_results = {}

    for folder in args.folders:
        path = os.path.join(base, folder)
        mapping = scan_folder(path, [e.lower() for e in args.exts])
        is_label = folder.lower() == 'labels'
        results = analyze_mapping(mapping, is_label=is_label)
        print_report(f"Scan results for: {path}", results)
        all_results[folder] = results

    # Optionally write CSV
    if args.report_csv:
        try:
            import csv
            with open(args.report_csv, 'w', newline='', encoding='utf-8') as fh:
                writer = csv.writer(fh)
                writer.writerow(['folder', 'order', 'expected_items', 'faces_per_item', 'expected_files', 'actual', 'subids', 'missing_subids', 'per_subid_missing', 'filenames'])
                for folder, results in all_results.items():
                    for r in results:
                        per_subid_missing_str = '|'.join(f"{k}:{','.join(map(str,v))}" for k,v in r.get('per_subid_missing', {}).items())
                        writer.writerow([
                            folder,
                            r['order'],
                            r.get('expected_items'),
                            r.get('faces_per_item'),
                            r.get('expected_files'),
                            r.get('actual'),
                            ';'.join(map(str, r.get('subids', []))),
                            ';'.join(map(str, r.get('missing_subids', []))),
                            per_subid_missing_str,
                            '|'.join(r.get('filenames', [])),
                        ])
            print('\nCSV report written to', args.report_csv)
        except Exception as e:
            print('Failed to write CSV report:', e)


if __name__ == '__main__':
    main()
