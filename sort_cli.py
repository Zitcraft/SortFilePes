"""
Main CLI interface for embroidery sorter - refactored version using modular components
"""

import argparse
import sys
import shutil
from pathlib import Path

from embroidery_sorter import (
    EmbroideryCore, 
    TimeEstimator, 
    WorkloadAssignment, 
    FileOperations, 
    Exporters,
    Config
)


def main(argv=None):
    """Main CLI function using modular components"""
    p = argparse.ArgumentParser(description="Group PES files by design hash (8 chars) using modular library.")
    p.add_argument("--src", "-s", default="files/design", help="Source folder to scan for .pes files")
    p.add_argument("--dst", "-d", default="sorted", help="Destination root for grouped folders")
    p.add_argument("--copy", action="store_true", default=False, help="Copy files instead of moving (default: move)")
    p.add_argument("--csv", default="sorted/output/assignment.csv", help="Write assignment CSV to this path")
    p.add_argument("--xlsx", default="sorted/output/assignment.xlsx", help="Write assignment XLSX (Excel) to this path")
    p.add_argument("--people", type=int, default=Config.DEFAULT_PEOPLE_COUNT, help="Number of people to assign work to")
    args = p.parse_args(argv)
    
    print("=" * 60)
    print("EMBROIDERY FILE SORTER")
    print("=" * 60)
    print()
    
    # Show what will happen
    print("Phân loại file thêu:")
    print("- Nguồn: files/design/ (file .pes)")
    print("- Đích: sorted/ (phân loại A/B/C)")
    print("- Sao chép nhãn từ files/labels/ vào sorted/*/labels/")
    print("- Tạo CSV/XLSX với folder_order và unique_hashes")
    print()
    
    confirm = input("Bạn có muốn tiếp tục? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Đã hủy bỏ.")
        return
    print()

    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()

    if not src.exists():
        print(f"Source folder does not exist: {src}")
        return 2

    print(f"Scanning source: {src}")
    print(f"Output will be placed under: {dst} (move files: {not args.copy})")

    # Initialize components
    time_estimator = TimeEstimator()
    workload_assignment = WorkloadAssignment({
        'people_count': args.people,
        'person_labels': Config.DEFAULT_PERSON_LABELS[:args.people] if args.people <= len(Config.DEFAULT_PERSON_LABELS) else [f"Person_{i+1}" for i in range(args.people)]
    })

    # 1) Scan files and compute hash
    file_meta = EmbroideryCore.scan_pes_files(src)
    if not file_meta:
        print("No .pes files found.")
        return 0

    # 2) Estimate seconds for each file
    print("Estimating embroidery time for each file (this may load PES files)...")
    file_meta = time_estimator.estimate_time_for_files(file_meta)

    # 3) Build components so that same hash or same id_item stay together
    comps = workload_assignment.make_components(file_meta)

    # 4) Assign components to people balancing adjusted time
    assignment, buckets = workload_assignment.assign_components_to_people(file_meta, comps)

    # 5) Add person assignment info to metadata
    file_meta = workload_assignment.add_person_assignments(file_meta, assignment)

    # 6) Move/copy files into person folders under dst
    updated_meta = FileOperations.group_into_person_folders(
        file_meta, dst, move=not args.copy, person_labels=workload_assignment.person_labels
    )
    
    # 7) Build summary report
    # Note: Labels will be processed later by map_dst_labels.py
    summary = workload_assignment.get_assignment_summary(updated_meta)

    # Print assignment summary
    print(f"\nAssignment summary ({args.people} groups {', '.join(workload_assignment.person_labels)}):")
    for label in workload_assignment.person_labels:
        data = summary.get(label, {})
        file_count = data.get("file_count", 0)
        total_seconds = data.get("total_seconds", 0.0)
        print(f"Group {label}: {file_count} file(s), estimated {TimeEstimator.human_readable(total_seconds)} total")

    # 8) Export CSV if requested (timestamped) - Save to output folder in sorted directory
    if args.csv:
        output_dir = dst / "output"
        output_dir.mkdir(exist_ok=True)
        csv_path = output_dir / Path(args.csv).name
        csv_path_ts = FileOperations.timestamped_path(csv_path)
        Exporters.export_csv(updated_meta, csv_path_ts, summary=summary)

    # 9) Export XLSX if requested (timestamped) - Save to output folder in sorted directory
    if args.xlsx:
        output_dir = dst / "output"
        output_dir.mkdir(exist_ok=True)
        xlsx_path = output_dir / Path(args.xlsx).name
        xlsx_path_ts = FileOperations.timestamped_path(xlsx_path)
        Exporters.export_xlsx(updated_meta, xlsx_path_ts, summary=summary, person_labels=workload_assignment.person_labels)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())