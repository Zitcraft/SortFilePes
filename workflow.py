
#!/usr/bin/env python3
"""
Complete Embroidery Management Workflow
Chạy từng bước hoặc tất cả các bước trong quy trình quản lý file thêu.
"""

import os
import sys
import subprocess
from pathlib import Path
import logging
from datetime import datetime

def move_pes_folders():
    """Gom tất cả các thư mục con có file pes vào thư mục pes trong từng A, B, C, D."""
    base_sorted = Path("sorted")
    group_folders = ["A", "B", "C", "D"]
    pes_folder_name = "pes"
    pes_count = 0
    for group in group_folders:
        group_path = base_sorted / group
        if not group_path.exists() or not group_path.is_dir():
            continue
        pes_path = group_path / pes_folder_name
        pes_path.mkdir(exist_ok=True)
        # Duyệt tất cả thư mục con trong group
        for sub in group_path.iterdir():
            if sub.is_dir() and sub.name != pes_folder_name:
                pes_files = list(sub.glob("*.pes"))
                if pes_files:
                    # Di chuyển toàn bộ thư mục vào pes
                    dest = pes_path / sub.name
                    if dest.exists():
                        log_print(f"⚠️ Thư mục đã tồn tại: {dest}, bỏ qua!")
                        continue
                    sub.rename(dest)
                    pes_count += 1
                    log_print(f"Đã di chuyển {sub} vào {pes_path}")
    log_print(f"\n✅ Đã gom {pes_count} thư mục có file pes vào pes/ trong từng nhóm.")

# Setup logging
def setup_logging():
    """Setup logging to both console and file."""
    log_file = "workflow_log.txt"
    
    # Create logger
    logger = logging.getLogger('workflow')
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    simple_formatter = logging.Formatter('%(message)s')
    
    # File handler - detailed logging
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler - simple output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

def log_print(message):
    """Print to console and log to file."""
    logger.info(message)

def log_error(message):
    """Print error to console and log to file."""
    logger.error(message)

def log_debug(message):
    """Log debug info (file only)."""
    logger.debug(message)
import logging
from datetime import datetime

def run_script(script_name, description):
    """Run a Python script and handle errors."""
    log_print(f"\n{'='*60}")
    log_print(f"RUNNING: {description}")
    log_print(f"Script: {script_name}")
    log_print(f"{'='*60}")
    
    log_debug(f"Starting script: {script_name}")
    
    try:
        # Run script interactively (no capture_output) so user can see prompts
        result = subprocess.run([sys.executable, script_name], check=True)
        log_print(f"✅ {description} completed successfully!")
        log_debug(f"Script {script_name} completed with return code 0")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"❌ {description} failed with error code {e.returncode}")
        log_debug(f"Script {script_name} failed with return code {e.returncode}")
        return False
    except KeyboardInterrupt:
        log_error(f"🛑 {description} interrupted by user")
        log_debug(f"Script {script_name} interrupted by user")
        return False

def check_requirements():
    """Check if required directories and files exist."""
    log_print("Checking requirements...")
    
    required_scripts = [
        "download_from_dropbox.py",
        "sort_cli.py", 
        "export_dst.py",
        "map_dst_labels.py"
    ]
    
    missing_scripts = []
    for script in required_scripts:
        if not os.path.exists(script):
            missing_scripts.append(script)
    
    if missing_scripts:
        log_error(f"❌ Missing required scripts: {', '.join(missing_scripts)}")
        return False
    
    log_print("✅ All required scripts found")
    return True

def show_workflow():
    """Show the complete workflow steps."""
    log_print("=" * 60)
    log_print("EMBROIDERY MANAGEMENT WORKFLOW")
    log_print("=" * 60)
    log_print("")
    log_print("Quy trình hoàn chỉnh (4 bước):")
    log_print("")
    log_print("1. 📥 Tải file từ Dropbox")
    log_print("   - Download .pes files → files/design/")
    log_print("   - Download labels → files/labels/")
    log_print("")
    log_print("2. 📂 Phân loại file")
    log_print("   - Phân tích và nhóm file .pes")
    log_print("   - Tạo folders A/B/C trong sorted/")
    log_print("   - Di chuyển files vào folders (move)")
    log_print("   - Labels ở lại files/labels/ (sẽ xử lý ở bước 4)")
    log_print("   - Tạo CSV/XLSX reports")
    log_print("")
    log_print("3. 🎯 Xuất file DST")
    log_print("   - Chuyển .pes → .dst với tên XXXYLZMDD")
    log_print("   - Xử lý multi-face items") 
    log_print("   - Lưu vào sorted/*/dst/")
    log_print("")
    log_print("4. 🏷️  Gắn nhãn DST")
    log_print("   - Đọc DST mapping log")
    log_print("   - Di chuyển labels có DST vào sorted/*/labels/")
    log_print("   - Gắn tên DST vào PNG labels")
    log_print("   - Multi-face: 'DST1 | DST2 | DST3'")
    log_print("   - Labels không có DST ở lại files/labels/")
    log_print("")

def main():
    """Main workflow controller."""
    # Log session start
    log_debug("="*60)
    log_debug(f"WORKFLOW SESSION STARTED: {datetime.now()}")
    log_debug("="*60)
    
    show_workflow()
    
    if not check_requirements():
        return 1
    
    log_print("Chọn tùy chọn:")
    log_print("1. Chạy từng bước (có xác nhận cho mỗi bước)")
    log_print("2. Chạy tất cả (auto mode)")
    log_print("3. Chạy bước cụ thể")
    log_print("4. Hiển thị trạng thái thư mục")
    log_print("")
    
    choice = input("Nhập lựa chọn (1-4) hoặc 'q' để thoát: ").strip()
    log_debug(f"User choice: {choice}")
    
    if choice == 'q':
        log_print("Đã thoát.")
        log_debug("Session ended by user")
        return 0
    
    elif choice == '1':
        # Run step by step with confirmation
        run_step_by_step()
    
    elif choice == '2':
        # Run all automatically
        run_all_auto()
    
    elif choice == '3':
        # Run specific step
        run_specific_step()
    
    elif choice == '4':
        # Show directory status
        show_directory_status()
    
    else:
        log_error("Lựa chọn không hợp lệ.")
        return 1
    
    log_debug(f"WORKFLOW SESSION ENDED: {datetime.now()}")
    log_debug("="*60)
    return 0

def run_step_by_step():
    """Run each step with user confirmation."""
    steps = [
        ("download_from_dropbox.py", "Tải file từ Dropbox"),
        ("sort_cli.py", "Phân loại file thêu"),
        ("export_dst.py", "Xuất file DST"),
        ("map_dst_labels.py", "Gắn nhãn DST")
    ]
    
    log_debug("Starting step-by-step execution")
    
    for i, (script, description) in enumerate(steps, 1):
        log_print(f"\n🔄 Bước {i}/4: {description}")
        proceed = input(f"Chạy '{script}'? (y/N/q): ").strip().lower()
        log_debug(f"Step {i} user input: {proceed}")
        
        if proceed == 'q':
            log_print("Đã dừng quy trình.")
            log_debug("Step-by-step execution stopped by user")
            break
        elif proceed in ['y', 'yes']:
            success = run_script(script, description)
            if not success:
                log_print(f"⚠️  Bước {i} thất bại. Tiếp tục?")
                cont = input("Tiếp tục với bước tiếp theo? (y/N): ").strip().lower()
                log_debug(f"Step {i} failed, continue input: {cont}")
                if cont not in ['y', 'yes']:
                    break
        else:
            log_print(f"⏭️  Bỏ qua bước {i}")
            log_debug(f"Step {i} skipped")

def run_all_auto():
    """Run all steps automatically."""
    log_print("\n🚀 Chạy tất cả các bước tự động...")
    confirm = input("Bạn có chắc chắn? (y/N): ").strip().lower()
    log_debug(f"Auto run confirmation: {confirm}")
    
    if confirm not in ['y', 'yes']:
        log_print("Đã hủy bỏ.")
        log_debug("Auto run cancelled by user")
        return
    
    steps = [
        ("download_from_dropbox.py", "Tải file từ Dropbox"),
        ("sort_cli.py", "Phân loại file thêu"),
        ("export_dst.py", "Xuất file DST"),
        ("map_dst_labels.py", "Gắn nhãn DST")
    ]
    failed_steps = []
    log_debug("Starting automatic execution of all steps")
    for i, (script, description) in enumerate(steps, 1):
        log_print(f"\n📍 Đang chạy bước {i}/4: {description}")
        success = run_script(script, description)
        if not success:
            failed_steps.append(f"Bước {i}: {description}")
    # Sau khi hoàn thành các bước chính, gom thư mục pes
    log_print("\nBổ sung: Gom các thư mục có file pes...")
    move_pes_folders()
    log_print(f"\n{'='*60}")
    log_print("KẾT QUẢ CUỐI CÙNG")
    log_print(f"{'='*60}")
    if failed_steps:
        log_error(f"❌ {len(failed_steps)} bước thất bại:")
        for step in failed_steps:
            log_error(f"   - {step}")
    else:
        log_print("✅ Tất cả 4 bước hoàn thành thành công!")
        log_print("\n🎉 Quy trình hoàn chỉnh! Kiểm tra thư mục 'sorted/' để xem kết quả.")
    log_debug(f"Auto execution completed. Failed steps: {len(failed_steps)}")

def run_specific_step():
    """Run a specific step."""
    steps = [
        ("download_from_dropbox.py", "Tải file từ Dropbox"),
        ("sort_cli.py", "Phân loại file thêu"),
        ("export_dst.py", "Xuất file DST"),
        ("map_dst_labels.py", "Gắn nhãn DST")
    ]
    
    log_print("\nChọn bước để chạy:")
    for i, (script, description) in enumerate(steps, 1):
        log_print(f"{i}. {description} ({script})")
    log_print("")
    
    try:
        choice = int(input("Nhập số bước (1-4): ").strip())
        log_debug(f"Specific step choice: {choice}")
        
        if 1 <= choice <= 4:
            script, description = steps[choice - 1]
            run_script(script, description)
        else:
            log_error("Số bước không hợp lệ.")
    except ValueError:
        log_error("Vui lòng nhập số.")

def show_directory_status():
    """Show current directory status."""
    log_print(f"\n{'='*60}")
    log_print("TRẠNG THÁI THỦ MỤC")
    log_print(f"{'='*60}")
    
    dirs_to_check = [
        ("files/", "Thư mục dữ liệu chính"),
        ("files/design/", "File .pes từ Dropbox"),
        ("files/labels/", "File nhãn từ Dropbox"),
        ("sorted/", "Kết quả phân loại"),
        ("sorted/A/", "File người A"),
        ("sorted/B/", "File người B"), 
        ("sorted/C/", "File người C"),
        ("sorted/output/", "CSV/XLSX/JSON reports")
    ]
    
    log_debug("Checking directory status")
    
    for dir_path, description in dirs_to_check:
        path = Path(dir_path)
        if path.exists():
            if path.is_dir():
                file_count = len(list(path.iterdir())) if path.is_dir() else 0
                log_print(f"✅ {description:30} ({file_count} items)")
                log_debug(f"Directory {dir_path}: {file_count} items")
            else:
                log_print(f"❓ {description:30} (not a directory)")
                log_debug(f"Path {dir_path} exists but is not a directory")
        else:
            log_print(f"❌ {description:30} (not found)")
            log_debug(f"Directory {dir_path} not found")
    
    # Check for specific file types
    log_print("")
    log_print("Chi tiết file:")
    
    file_checks = [
        ("files/design/*.pes", "PES files"),
        ("files/labels/*.png", "PNG labels"),
        ("sorted/*/dst/*.dst", "DST files"),
        ("sorted/output/*.csv", "CSV reports"),
        ("sorted/output/*.xlsx", "Excel reports"),
        ("sorted/output/*.json", "JSON logs")
    ]
    
    for pattern, description in file_checks:
        files = list(Path().glob(pattern))
        log_print(f"   {description:20}: {len(files)} files")
        log_debug(f"File pattern {pattern}: {len(files)} files")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)