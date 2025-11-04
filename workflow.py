#!/usr/bin/env python3
"""
Complete Embroidery Management Workflow
Chạy từng bước hoặc tất cả các bước trong quy trình quản lý file thêu.
"""

import os
import sys
import subprocess
from pathlib import Path
from embroidery_sorter.workflow_logger import log_print, logged_input, get_logger

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
    log_print("")
    return True

def run_script_with_input(script_name, description, auto_inputs=None, args=None):
    """Run script with predefined inputs (legacy function - redirects to unified function)."""
    if args:
        # If args are provided, use the original implementation for compatibility
        try:
            cmd = [sys.executable, script_name] + args
            input_text = "\n".join(str(inp) for inp in auto_inputs) + "\n" if auto_inputs else ""
            
            log_print("="*60)
            log_print(f"RUNNING: {description}")
            log_print(f"Script: {script_name}")
            log_print(f"Args: {args}")
            log_print(f"Auto inputs: {auto_inputs}")
            log_print("="*60)
            
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
    else:
        # Use the new unified function
        return run_script_with_auto_inputs(script_name, description, auto_mode="default", auto_inputs=auto_inputs)

def run_script_with_auto_inputs(script_name, description, auto_mode="default", auto_inputs=None):
    """Run script with various auto input modes.
    
    Args:
        script_name: Name of the script to run
        description: Description for logging
        auto_mode: Type of auto mode - "partial", "folder_dialog", "default"
        auto_inputs: Optional list of inputs for default mode
    """
    try:
        log_print("="*60)
        log_print(f"RUNNING: {description}")
        log_print(f"Script: {script_name}")
        log_print("="*60)
        
        # Set environment variables based on auto mode
        env_vars_to_cleanup = []
        
        if auto_mode == "partial":
            log_print("📝 AUTO MODE (PARTIAL):")
            log_print("   ✅ Tự động chọn option '6' và xác nhận 'y'")
            log_print("   👤 Bạn sẽ nhập Range ID thủ công")
            log_print("")
            
            os.environ['PARTIAL_AUTO_MODE'] = '1'
            os.environ['AUTO_OPTION'] = '6'
            os.environ['AUTO_CONFIRM'] = 'y'
            env_vars_to_cleanup = ['PARTIAL_AUTO_MODE', 'AUTO_OPTION', 'AUTO_CONFIRM']
            
        elif auto_mode == "folder_dialog":
            log_print("📝 AUTO MODE (FOLDER DIALOG):")
            log_print("   🗂️ Tự động chọn option '6' (Browse folder dialog)")
            log_print("")
            
            os.environ['AUTO_FOLDER_DIALOG'] = '1'
            os.environ['AUTO_OPTION'] = '6'
            env_vars_to_cleanup = ['AUTO_FOLDER_DIALOG', 'AUTO_OPTION']
            
        elif auto_mode == "default" and auto_inputs:
            log_print("📝 AUTO MODE (INPUTS):")
            log_print(f"   ✅ Auto inputs: {auto_inputs}")
            log_print("")
        
        try:
            # Run the script
            cmd = [sys.executable, script_name]
            
            if auto_mode == "default" and auto_inputs:
                # For default mode with inputs, use the old input method
                input_text = "\n".join(str(inp) for inp in auto_inputs) + "\n"
                result = subprocess.run(
                    cmd,
                    input=input_text,
                    text=True,
                    capture_output=False,
                    cwd=os.getcwd()
                )
            else:
                # For partial and folder_dialog modes, run normally (script checks env vars)
                result = subprocess.run(cmd, cwd=os.getcwd())
            
            return result.returncode == 0
            
        finally:
            # Clean up environment variables
            for var in env_vars_to_cleanup:
                os.environ.pop(var, None)
        
    except Exception as e:
        log_print(f"❌ Error in auto mode '{auto_mode}': {e}")
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


def run_check_completeness():
    """Run check_id_completeness.py and log a short summary."""
    try:
        cmd = [sys.executable, 'check_id_completeness.py']
        log_print('🔎 Running ID completeness check...')
        result = subprocess.run(cmd, cwd=os.getcwd())
        if result.returncode == 0:
            log_print('✅ ID completeness check finished')
            return True
        else:
            log_print('❌ ID completeness check reported issues')
            return False
    except Exception as e:
        log_print(f"❌ Error running completeness check: {e}")
        return False

def run_sort_step():
    """Run sorting step with configuration."""
    log_print("📋 Cấu hình phân loại:")
    log_print("   1 = Một người (folder A)")
    log_print("   2 = Hai người (folders A, B)")
    log_print("   3 = Ba người (folders A, B, C)")
    log_print("   4 = Bốn người (folders A, B, C, D) - mặc định")
    
    while True:
        try:
            folders = logged_input("Nhập số người (1-4, mặc định 4): ").strip()
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
    log_print("📊 TRẠNG THÁI THU MỤC:")
    
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
        ("map_dst_labels.py", "Gắn nhãn DST"),
        ("check_id_completeness.py", "Kiểm tra tính đầy đủ ID"),
        ("list_label_ids.py", "Liệt kê ID từ labels")
    ]
    
    log_print("👉 Các bước có thể chạy:")
    for i, (script, desc) in enumerate(steps, 1):
        log_print(f"   {i}. {desc}")
    
    while True:
        try:
            choice = logged_input("Chọn bước (1-6) hoặc 'b' để quay lại: ").strip().lower()
            
            if choice == 'b':
                return
            
            step_num = int(choice)
            if 1 <= step_num <= 6:
                script, description = steps[step_num - 1]
                
                if step_num == 2:  # Sort step needs special handling
                    success = run_sort_step()
                elif step_num == 6:  # List label IDs - auto select folder dialog
                    log_print("🗂️ Auto-selecting folder dialog for label ID extraction...")
                    success = run_script_with_auto_inputs(script, description, auto_mode="folder_dialog")
                else:
                    success = run_script(script, description)
                    # If this was the download step, run completeness check
                    if script == 'download_from_dropbox.py' and success:
                        run_check_completeness()
                
                if success:
                    log_print(f"✅ {description} completed successfully!")
                else:
                    log_print(f"❌ {description} failed!")
                break
            else:
                log_print("❌ Vui lòng chọn số từ 1-6")
                
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
    
    log_print("🚀 Chạy tất cả các bước tự động...")
    # confirm = logged_input("Bạn có chắc chắn? (y/N): ").strip().lower()
    
    # if confirm != 'y':
    #     log_print("❌ Hủy bỏ")
    #     return
    
    failed_steps = []
    
    for i, (script, description, special) in enumerate(steps, 1):
        log_print(f"📍 Đang chạy bước {i}/4: {description}")
        
        if special == "special" and script == "sort_cli.py":
            success = run_sort_step()
        elif special == "auto_download" and script == "download_from_dropbox.py":
            # Auto input "6" and "y" only, then let user manually input start/end IDs
            log_print("🤖 Auto mode: Download script")
            log_print("📝 Tự động chọn option 6 và xác nhận 'y'")
            
            success = run_script_with_auto_inputs(script, description, auto_mode="partial")
        
        else:
            success = run_script(script, description)
        # After download step, run completeness check
        if script == 'download_from_dropbox.py' and success:
            run_check_completeness()
        
        if not success:
            failed_steps.append(f"Bước {i}: {description}")
    
    log_print(f"{'='*60}")
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
    
    log_print("Quy trình hoàn chỉnh (4 bước):")
    log_print("1. 📥 Tải file từ Dropbox")
    # log_print("   - Download .pes files → files/design/")
    # log_print("   - Download labels → files/labels/")
    
    log_print("2. 📂 Phân loại file")
    # log_print("   - Phân tích và nhóm file .pes")
    # log_print("   - Tạo folders A/B/C trong sorted/")
    # log_print("   - Di chuyển files vào folders (move)")
    # log_print("   - Labels ở lại files/labels/ (sẽ xử lý ở bước 4)")
    # log_print("   - Tạo CSV/XLSX reports")
    
    log_print("3. 🎯 Xuất file DST")
    # log_print("   - Chuyển .pes → .dst với tên XXXYLZMDD")
    # log_print("   - Xử lý multi-face items")
    # log_print("   - Lưu vào sorted/*/dst/")
    
    log_print("4. 🏷️  Gắn nhãn DST")
    # log_print("   - Đọc DST mapping log")
    # log_print("   - Di chuyển labels có DST vào sorted/*/labels/")
    # log_print("   - Gắn tên DST vào PNG labels")
    # log_print("   - Multi-face: 'DST1 | DST2 | DST3'")
    # log_print("   - Labels không có DST ở lại files/labels/")
    log_print("")
    
    # Check requirements
    log_print("Checking requirements...")
    if not check_requirements():
        sys.exit(1)
    
    while True:
        log_print("👉 Chọn tùy chọn:")
        log_print("   1. Chạy từng bước (có xác nhận cho mỗi bước)")
        log_print("   2. Chạy tất cả (auto mode)")
        log_print("   3. Chạy bước cụ thể")
        log_print("   4. Hiển thị trạng thái thư mục")
        
        choice = logged_input("Nhập lựa chọn (1-4) hoặc 'q' để thoát: ").strip().lower()
        
        if choice == 'q':
            log_print("👋 Tạm biệt!")
            break
        elif choice == '1':
            # Manual step by step
            run_all_steps()
        elif choice == '2':
            # Auto mode
            run_all_steps()
            break
        elif choice == '3':
            # Individual step
            run_individual_step()
        elif choice == '4':
            # Show status
            show_status()
        else:
            log_print("❌ Lựa chọn không hợp lệ. Vui lòng thử lại.")

if __name__ == "__main__":
    main()