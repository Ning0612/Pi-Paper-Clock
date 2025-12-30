import subprocess
import os
import argparse
import time 
import sys
import threading

# --- Configuration ---
SOURCE_DIR = "src"
INCLUDE_EXTENSIONS = [".py", ".json"]
UPLOAD_IMAGES = True
MPREMOTE_PORT = None
ENABLE_CLEAN = True
ENABLE_RECURSIVE_CLEAN = False  # 新增：是否遞迴清除所有檔案
NO_CONFIG = False  # 新增：是否跳過 config.json


# 用於停止讀取執行緒的事件
stop_reader_event = threading.Event()

def _reader_thread(pipe, output_stream):
    """
    獨立執行緒，用於即時讀取子進程的輸出。
    """
    while not stop_reader_event.is_set():
        try:
            line = pipe.readline()
            if line:
                output_stream.write(line)
                output_stream.flush()
            else:
                if pipe.closed:
                    break
                time.sleep(0.01)
        except ValueError:
            break
        except Exception as e:
            break

def interactive_repl(base_cmd):
    """
    啟動 mpremote repl 並實現即時互動，直到使用者按下 Ctrl+X。
    """
    _clear_current_line()
    print("\n🖥️ 連接到裝置 Terminal (REPL)... 按 Ctrl+X 退出。")
    
    repl_command = base_cmd + ["repl"]
    
    process = subprocess.Popen(
        repl_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True, 
        encoding='latin-1', 
        errors='ignore'
    )

    stdout_thread = threading.Thread(target=_reader_thread, args=(process.stdout, sys.stdout))
    stderr_thread = threading.Thread(target=_reader_thread, args=(process.stderr, sys.stderr))

    stdout_thread.start()
    stderr_thread.start()

    try:
        process.wait()
    except KeyboardInterrupt:
        print("\n捕獲到 Ctrl+C，正在終止 REPL 進程...")
    finally:
        stop_reader_event.set()
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
        if process.stdin:
            process.stdin.close()

        if process.poll() is None:
            process.terminate()
            process.wait(timeout=1)
            if process.poll() is None:
                process.kill()
        
        print("REPL 連接已關閉。")
        stop_reader_event.clear()

def run_command(command, ignore_exists_error=False, display_output=False, capture_output_only=False):
    """
    執行命令並捕獲輸出。
    """
    try:
        result = subprocess.run(command, check=not capture_output_only, capture_output=True, text=True, encoding='latin-1') 
        
        if capture_output_only:
            return result.stdout.strip() if result.stdout else ""

        stdout_str = result.stdout.strip() if result.stdout else ""
        stderr_str = result.stderr.strip() if result.stderr else ""

        if display_output: 
            if stdout_str:
                print(stdout_str)
            if stderr_str and not (ignore_exists_error and "File exists" in stderr_str):
                print(f"[stderr] {stderr_str}")
        return True
    except FileNotFoundError:
        if display_output:
            print("❌ 找不到 mpremote，請執行：pip install mpremote")
        return False
    except subprocess.CalledProcessError as e:
        if display_output:
            print(f"❌ 指令失敗：{' '.join(command)}")
            print(f"[stdout]\n{e.stdout.strip()}")
            if not (ignore_exists_error and "File exists" in e.stderr):
                print(f"[stderr]\n{e.stderr.strip()}")
        return False
    except Exception as e:
        if display_output:
            print(f"❌ 執行命令時發生意外錯誤: {e}")
        return False

def get_mpremote_base():
    return ["mpremote", "connect", MPREMOTE_PORT] if MPREMOTE_PORT else ["mpremote"]

def format_bytes(size):
    """
    格式化檔案大小顯示
    """
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"

def collect_files():
    """
    收集要上傳的檔案，並統計檔案大小
    """
    all_files = []

    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if NO_CONFIG and file == "config.json":
                continue
            if any(file.endswith(ext) for ext in INCLUDE_EXTENSIONS):
                full_path = os.path.join(root, file).replace("\\", "/")
                rel_path = os.path.relpath(full_path, SOURCE_DIR).replace("\\", "/")
                file_size = os.path.getsize(full_path)
                all_files.append((full_path, rel_path, file_size))

    if UPLOAD_IMAGES:
        image_dir = os.path.join(SOURCE_DIR, "image")
        if os.path.exists(image_dir):
            for root, dirs, files in os.walk(image_dir):
                for file in files:
                    if file.endswith(".bin"):
                        full_path = os.path.join(root, file).replace("\\", "/")
                        rel_path = os.path.relpath(full_path, SOURCE_DIR).replace("\\", "/")
                        file_size = os.path.getsize(full_path)
                        all_files.append((full_path, rel_path, file_size))

    return all_files

def ensure_remote_dirs(path, created_dirs):
    """
    確保遠端目錄存在，使用字典記錄已建立的路徑
    """
    base_cmd = get_mpremote_base()
    parts = path.split("/")
    current = ""
    
    for part in parts:
        if not part:
            continue
        current = f"{current}/{part}" if current else part
        
        # 檢查是否已經建立過此路徑
        if current not in created_dirs:
            subprocess.run(base_cmd + ["fs", "mkdir", f":{current}"], capture_output=True, text=True, encoding='latin-1')
            created_dirs[current] = True

def _clear_current_line():
    print("\r" + " " * 150 + "\r", end="", flush=True)

def _print_progress_line(current_command, progress, file_size=None, total_width=50):
    """
    顯示進度條，包含檔案大小資訊
    """
    done_width = int(progress / 100 * total_width)
    bar = "█" * done_width + "-" * (total_width - done_width)
    
    size_info = f" ({format_bytes(file_size)})" if file_size else ""
    command_text = f"{current_command}{size_info}"
    
    print(f"\r[{bar}] {progress:.1f}% | {command_text.ljust(80)}", end="", flush=True)

def clean_device():
    """
    清除裝置上的檔案
    """
    if ENABLE_RECURSIVE_CLEAN:
        print("遞迴清除裝置上的所有檔案...")
        clean_all_files()
    else:
        print("清除裝置上指定類型的檔案 {}...".format(INCLUDE_EXTENSIONS))
        clean_specific_files()

def clean_all_files():
    """
    遞迴清除裝置上的所有檔案和目錄
    """
    base_cmd = get_mpremote_base()
    
    def delete_directory_recursively(dir_path):
        """遞迴刪除目錄及其內容，返回上層時才刪除目錄本身"""
        # 列出目錄內容
        proc = subprocess.run(base_cmd + ["fs", "ls", f":{dir_path}"], capture_output=True, text=True, encoding='latin-1')
        if proc.returncode != 0:
            # 目錄可能已經不存在，為空或無法存取
            current_command_text = f"刪除目錄: {dir_path} (可能為空)"
            print(f"\r{current_command_text.ljust(80)}", end="", flush=True)
            return run_command(base_cmd + ["fs", "rmdir", f":{dir_path}"], display_output=False)
        
        # 遍歷目錄內容，立即處理每個項目
        for line in proc.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if len(parts) < 2:
                continue
                
            item_name = parts[-1].rstrip('/')
            if not item_name or item_name in ['', '.', '..']:
                continue
            
            full_path = f"{dir_path}/{item_name}"
            is_directory = parts[0].startswith('d') or line.endswith('/')
            
            if is_directory:
                # 如果是目錄，遞迴進入處理
                current_command_text = f"進入子目錄: {full_path}"
                print(f"\r{current_command_text.ljust(80)}", end="", flush=True)
                
                # 遞迴呼叫，處理子目錄的所有內容
                success = delete_directory_recursively(full_path)
                if not success:
                    print(f"\n❌ 處理子目錄失敗: {full_path}")
                    
                # 遞迴回到這裡時，子目錄已經被刪除了
                
            else:
                # 如果是檔案，直接刪除
                if NO_CONFIG and item_name == "config.json":
                    continue
                current_command_text = f"刪除檔案: {full_path}"
                print(f"\r{current_command_text.ljust(80)}", end="", flush=True)
                success = run_command(base_cmd + ["fs", "rm", f":{full_path}"], display_output=False)
                
        
        # 當前目錄的所有內容都處理完了，現在刪除這個空目錄
        current_command_text = f"刪除已清空的目錄: {dir_path}"
        print(f"\r{current_command_text.ljust(80)}", end="", flush=True)
        success = run_command(base_cmd + ["fs", "rmdir", f":{dir_path}"], display_output=False)
        if not success:
            print(f"\n❌ 刪除目錄失敗: {dir_path}")
        
        return success
    
    # 獲取根目錄的檔案和目錄列表
    proc = subprocess.run(base_cmd + ["fs", "ls", ":"], capture_output=True, text=True, encoding='latin-1')
    if proc.returncode != 0:
        print("Warning: 無法列出根目錄檔案。裝置可能為空或未連接。")
        return
    
    root_files = []
    root_dirs = []
    
    for line in proc.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
            
        parts = line.split()
        if len(parts) < 2:
            continue
        
        item_name = parts[-1].rstrip('/')
        if not item_name or item_name in ['', '.', '..', ':']:
            continue
        
        if parts[0].startswith('d') or line.endswith('/'):
            root_dirs.append(item_name)
        else:
            root_files.append(item_name)
    
    total_items = len(root_files) + len(root_dirs)
    
    if total_items == 0:
        print("沒有找到要清除的檔案或目錄。")
        return

    print(f"找到 {len(root_files)} 個檔案和 {len(root_dirs)} 個目錄要刪除。")
    
    # 先刪除根目錄下的所有檔案
    for f in root_files:
        if NO_CONFIG and f == "config.json":
            continue
        current_command_text = f"刪除根目錄檔案: {f}"
        print(f"\r{current_command_text.ljust(80)}", end="", flush=True)
        
        success = run_command(base_cmd + ["fs", "rm", f":{f}"], display_output=False)
        if not success:
            print(f"\n❌ 刪除檔案失敗: {f}")
    
    # 遞迴處理所有根目錄
    for d in root_dirs:
        current_command_text = f"開始處理目錄樹: {d}"
        print(f"\r{current_command_text.ljust(80)}", end="", flush=True)
        
        # 呼叫遞迴函數，會在處理完所有子內容後刪除目錄
        success = delete_directory_recursively(d)
        if not success:
            print(f"\n❌ 處理目錄樹失敗: {d}")
    
    _clear_current_line()
    print("✅ 檔案清除完成。\n")

def clean_specific_files():
    """
    清除指定類型的檔案
    """
    base_cmd = get_mpremote_base()

    proc = subprocess.run(base_cmd + ["fs", "ls", "-r", ":"], capture_output=True, text=True, encoding='latin-1')
    if proc.returncode != 0:
        print("Warning: 無法列出檔案。裝置可能為空或未連接。")
        return

    all_remote_files_raw = proc.stdout.strip().splitlines()
    
    files_to_delete = []
    for line in all_remote_files_raw:
        line = line.strip()
        if not line:
            continue
            
        parts = line.split()
        if len(parts) < 2:
            continue
            
        # 取最後一個部分作為檔案名
        file_name = parts[-1]
        
        # 跳過目錄和無效檔案名
        if (not file_name or 
            file_name == ':' or 
            file_name.endswith('/') or 
            file_name in ['', '.', '..'] or
            parts[0].startswith('d')):
            continue

        # 檢查檔案副檔名
        if any(file_name.endswith(ext) for ext in INCLUDE_EXTENSIONS):
            if NO_CONFIG and file_name == "config.json":
                continue
            files_to_delete.append(file_name)

    if not files_to_delete:
        print("沒有找到符合條件的檔案要清除。")
        return

    print(f"找到 {len(files_to_delete)} 個檔案要刪除。")
    for i, f in enumerate(files_to_delete):
        progress_percent = ((i + 1) / len(files_to_delete)) * 100
        current_command_text = f"刪除檔案: {f}"
        _print_progress_line(current_command_text, progress_percent)

        success = run_command(base_cmd + ["fs", "rm", f":{f}"], display_output=False)
        if not success:
            _clear_current_line()
            print(f"❌ 刪除失敗: {f}")
    
    _clear_current_line()
    print("✅ 檔案清除完成。\n")

def reset_device():
    _clear_current_line()
    print("\n🔄 重啟裝置...")
    base_cmd = get_mpremote_base()
    run_command(base_cmd + ["reset"], display_output=True)

def upload_files():
    base_cmd = get_mpremote_base()

    file_list = collect_files()
    total_files = len(file_list)
    total_size = sum(file_size for _, _, file_size in file_list)
    
    print(f"📦 共 {total_files} 個檔案要上傳，總大小: {format_bytes(total_size)}")

    # 建立目錄記錄字典
    created_dirs = {}
    uploaded_size = 0

    for i, (local_path, remote_path, file_size) in enumerate(file_list):
        current_file_num = i + 1
        
        # 根據檔案大小計算進度
        progress_percent = (uploaded_size / total_size) * 100 if total_size > 0 else 0

        # 建立目錄
        dirs = os.path.dirname(remote_path)
        if dirs:
            current_command_text = f"建立目錄: :{dirs}"
            _print_progress_line(current_command_text, progress_percent)
            ensure_remote_dirs(dirs, created_dirs)

        # 上傳檔案
        cmd = base_cmd + ["fs", "cp", local_path, f":{remote_path}"]
        current_command_text = f"上傳檔案: {remote_path}"
        _print_progress_line(current_command_text, progress_percent, file_size)
        
        if not run_command(cmd, display_output=False):
            _clear_current_line()
            print(f"❌ 上傳失敗: {remote_path}")
            return
        
        uploaded_size += file_size
        
    _clear_current_line()
    print(f"\n✅ 上傳完成。總共上傳 {format_bytes(total_size)}")

    # 重啟裝置
    reset_device()

    print("等待裝置重啟並初始化...")
    time.sleep(5) 

    # 進入互動式 REPL
    print("\n現在您可以進入裝置 Terminal (REPL)... 按 Ctrl+X 退出。")
    interactive_repl(base_cmd)

def parse_args():
    parser = argparse.ArgumentParser(description="Upload files to Pico W.")
    parser.add_argument("--no-images", action="store_false", dest="upload_images", default=True, help="Do not upload image files.")
    parser.add_argument("--recursive-clean", action="store_true", dest="recursive_clean", default=False, help="遞迴清除裝置上的所有檔案 (包含目錄)")
    parser.add_argument("--no-clean", action="store_false", dest="enable_clean", default=True, help="跳過清除檔案步驟")
    parser.add_argument("--no-config", action="store_true", dest="no_config", default=False, help="不要上傳也不要刪除 config.json")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    
    UPLOAD_IMAGES = args.upload_images
    ENABLE_RECURSIVE_CLEAN = args.recursive_clean
    ENABLE_CLEAN = args.enable_clean
    NO_CONFIG = args.no_config

    print("--- Pico W 自動部署開始 ---")

    if ENABLE_CLEAN:
        clean_device()

    upload_files()