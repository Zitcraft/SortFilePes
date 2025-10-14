
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
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

def log_print(message):
    """Print and log message."""
    # print(message)
    logger.info(message)

def check_requirements():
    """Check if all required scripts exist."""
    required_scripts = [
        "download_from_dropbox.py",
        "sort_cli.py", 
        "export_dst.py",
        "map_dst_labels.py"
    ]
    
    missing = []
    for script in required_scripts:
        if not os.path.exists(script):
            missing.append(script)
    
    if missing:
        log_print(f"❌ Missing required scripts: {', '.join(missing)}")
        return False
    
    log_print("✅ All required scripts found")
    return True

def run_script_with_input(script_name, description, auto_inputs=None, args=None):
    """Run script with predefined inputs."""
    try:
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
        
        # Prepare input string
        input_text = ""
        if auto_inputs:
            input_text = "\n".join(str(inp) for inp in auto_inputs) + "\n"
        
        log_print("="*60)
        log_print(f"RUNNING: {description}")
        log_print(f"Script: {script_name}")
        log_print(f"Auto inputs: {auto_inputs}")
        log_print("="*60)
        
        # Run with input
        result = subprocess.run(
            cmd,
            input=input_text,
            text=True,
            capture_output=False,
            cwd=os.getcwd()
        )
        
        return result.returncode == 0
        
    except Exception as e:
        log_print(f"❌ Error running {script_name}: {e}")
        return False

def run_script_with_partial_input(script_name, description, auto_inputs=None):
    """Run script with partial automation - auto '5' and 'y', then user input for start/end."""
    try:
        log_print("="*60)
        log_print(f"RUNNING: {description}")
        log_print(f"Script: {script_name}")
        log_print("="*60)
        
        log_print("📝 AUTO MODE:")
        log_print("   ✅ Tự động chọn option '5' và xác nhận 'y'")
        log_print("   👤 Bạn sẽ nhập start ID và end ID sau khi thấy API range")
        log_print("")
        
        # Set environment variable to signal partial auto mode to the download script
        os.environ['PARTIAL_AUTO_MODE'] = '1'
        os.environ['AUTO_OPTION'] = '5'
        os.environ['AUTO_CONFIRM'] = 'y'
        
        try:
            # Run the script normally - it will check environment variables
            cmd = [sys.executable, script_name]
            result = subprocess.run(cmd, cwd=os.getcwd())
            return result.returncode == 0
        finally:
            # Clean up environment variables
            os.environ.pop('PARTIAL_AUTO_MODE', None)
            os.environ.pop('AUTO_OPTION', None)
            os.environ.pop('AUTO_CONFIRM', None)
        
    except Exception as e:
        log_print(f"❌ Error in partial auto mode: {e}")
        log_print("🔄 Falling back to fully interactive mode...")
        return run_script(script_name, description)

def run_script(script_name, description, args=None):
    """Run script interactively."""
    try:
        cmd = [sys.executable, script_name]
        if args:
            cmd.extend(args)
        
        log_print("="*60)
        log_print(f"RUNNING: {description}")
        log_print(f"Script: {script_name}")
        log_print("="*60)
        
        result = subprocess.run(cmd, cwd=os.getcwd())
        return result.returncode == 0
        
    except Exception as e:
        log_print(f"❌ Error running {script_name}: {e}")
        return False

def run_sort_step():
    """Run sorting step with configuration."""
    log_print("\n📋 Cấu hình phân loại:")
    log_print("   1 = Một người (folder A)")
    log_print("   2 = Hai người (folders A, B)")
    log_print("   3 = Ba người (folders A, B, C)")
    log_print("   4 = Bốn người (folders A, B, C, D) - mặc định")
    
    while True:
        try:
            folders = input("\nNhập số người (1-4, mặc định 4): ").strip()
            if not folders:
                folders = "4"
            
            folders_int = int(folders)
            if 1 <= folders_int <= 4:
                break
            else:
                log_print("❌ Vui lòng nhập số từ 1-4")
        except ValueError:
            log_print("❌ Vui lòng nhập số hợp lệ")
    
    # Run sort_cli.py with folder count
    return run_script("sort_cli.py", "Phân loại file thêu", ["--people", folders])

def show_status():
    """Show current directory status."""
    log_print("\n📊 TRẠNG THÁI THU MỤC:")
    
    dirs_to_check = [
        ("files/design", "Design files (.pes)"),
        ("files/labels", "Label files (.png/.pdf/.jpg/.svg)"),
        ("sorted", "Sorted folders"),
        ("sorted/A/dst", "DST files - Team A"),
        ("sorted/B/dst", "DST files - Team B"),
        ("sorted/C/dst", "DST files - Team C"),
        ("sorted/D/dst", "DST files - Team D"),
        ("sorted/A/labels", "Labels - Team A"),
        ("sorted/B/labels", "Labels - Team B"),
        ("sorted/C/labels", "Labels - Team C"),
        ("sorted/D/labels", "Labels - Team D"),
    ]
    
    for dir_path, description in dirs_to_check:
        if os.path.exists(dir_path):
            files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
            log_print(f"📁 {description}: {len(files)} files")
        else:
            log_print(f"📁 {description}: Chưa tồn tại")

def run_individual_step():
    """Run individual step."""
    steps = [
        ("download_from_dropbox.py", "Tải file từ Dropbox"),
        ("sort_cli.py", "Phân loại file thêu"),
        ("export_dst.py", "Xuất file DST"),
        ("map_dst_labels.py", "Gắn nhãn DST")
    ]
    
    log_print("\nCác bước có thể chạy:")
    for i, (script, desc) in enumerate(steps, 1):
        log_print(f"{i}. {desc}")
    
    while True:
        try:
            choice = input("\nChọn bước (1-4) hoặc 'b' để quay lại: ").strip().lower()
            
            if choice == 'b':
                return
            
            step_num = int(choice)
            if 1 <= step_num <= 4:
                script, description = steps[step_num - 1]
                
                if step_num == 2:  # Sort step needs special handling
                    success = run_sort_step()
                else:
                    success = run_script(script, description)
                
                if success:
                    log_print(f"✅ {description} completed successfully!")
                else:
                    log_print(f"❌ {description} failed!")
                break
            else:
                log_print("❌ Vui lòng chọn số từ 1-4")
                
        except ValueError:
            log_print("❌ Vui lòng nhập số hợp lệ")

def run_all_steps():
    """Run all steps automatically."""
    steps = [
        ("download_from_dropbox.py", "Tải file từ Dropbox", "auto_download"),
        ("sort_cli.py", "Phân loại file thêu", "special"),
        ("export_dst.py", "Xuất file DST", "auto_confirm"),
        ("map_dst_labels.py", "Gắn nhãn DST", "auto_confirm")
    ]
    
    log_print("\n🚀 Chạy tất cả các bước tự động...")
    confirm = input("Bạn có chắc chắn? (y/N): ").strip().lower()
    
    if confirm != 'y':
        log_print("❌ Hủy bỏ")
        return
    
    failed_steps = []
    
    for i, (script, description, special) in enumerate(steps, 1):
        log_print(f"\n📍 Đang chạy bước {i}/4: {description}")
        
        if special == "special" and script == "sort_cli.py":
            success = run_sort_step()
        elif special == "auto_download" and script == "download_from_dropbox.py":
            # Auto input "5" and "y" only, then let user manually input start/end IDs
            log_print("🤖 Auto mode: Download script")
            log_print("📝 Tự động chọn option 5 và xác nhận 'y'")
            log_print("📝 Sau đó bạn sẽ thấy API range và nhập start/end ID thủ công")
            
            # Use auto inputs: only 5 (option) and y (confirm), then interactive for start/end
            auto_inputs = ["5", "y"]  # Only auto input option and confirm
            success = run_script_with_partial_input(script, description, auto_inputs)
        
        else:
            success = run_script(script, description)
        
        if not success:
            failed_steps.append(f"Bước {i}: {description}")
    
    log_print(f"\n{'='*60}")
    if failed_steps:
        log_print("❌ CÁC BƯỚC BỊ LỖI:")
        for step in failed_steps:
            log_print(f"   • {step}")
    else:
        log_print("✅ TẤT CẢ CÁC BƯỚC HOÀN THÀNH THÀNH CÔNG!")
    log_print(f"{'='*60}")

def main():
    """Main workflow function."""
    log_print("="*60)
    log_print("EMBROIDERY MANAGEMENT WORKFLOW")
    log_print("="*60)
    
    log_print("\nQuy trình hoàn chỉnh (4 bước):")
    log_print("\n1. 📥 Tải file từ Dropbox")
    log_print("   - Download .pes files → files/design/")
    log_print("   - Download labels → files/labels/")
    
    log_print("\n2. 📂 Phân loại file")
    log_print("   - Phân tích và nhóm file .pes")
    log_print("   - Tạo folders A/B/C trong sorted/")
    log_print("   - Di chuyển files vào folders (move)")
    log_print("   - Labels ở lại files/labels/ (sẽ xử lý ở bước 4)")
    log_print("   - Tạo CSV/XLSX reports")
    
    log_print("\n3. 🎯 Xuất file DST")
    log_print("   - Chuyển .pes → .dst với tên XXXYLZMDD")
    log_print("   - Xử lý multi-face items")
    log_print("   - Lưu vào sorted/*/dst/")
    
    log_print("\n4. 🏷️  Gắn nhãn DST")
    log_print("   - Đọc DST mapping log")
    log_print("   - Di chuyển labels có DST vào sorted/*/labels/")
    log_print("   - Gắn tên DST vào PNG labels")
    log_print("   - Multi-face: 'DST1 | DST2 | DST3'")
    log_print("   - Labels không có DST ở lại files/labels/")
    
    # Check requirements
    log_print("\nChecking requirements...")
    if not check_requirements():
        sys.exit(1)
    
    while True:
        log_print("\nChọn tùy chọn:")
        log_print("1. Chạy từng bước (có xác nhận cho mỗi bước)")
        log_print("2. Chạy tất cả (auto mode)")
        log_print("3. Chạy bước cụ thể")
        log_print("4. Hiển thị trạng thái thư mục")
        
        choice = input("\nNhập lựa chọn (1-4) hoặc 'q' để thoát: ").strip().lower()
        
        if choice == 'q':
            log_print("👋 Tạm biệt!")
            break
        elif choice == '1':
            # Manual step by step
            run_all_steps()
        elif choice == '2':
            # Auto mode
            run_all_steps()
        elif choice == '3':
            # Individual step
            run_individual_step()
        elif choice == '4':
            # Show status
            show_status()
        else:
<<<<<<< HEAD
            log_print("❌ Lựa chọn không hợp lệ. Vui lòng thử lại.")
=======
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
>>>>>>> 33758f461ed244b281fd68aeed2356a19662c9a8

if __name__ == "__main__":
    main()