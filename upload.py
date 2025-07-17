import subprocess
import os
import argparse
import time 
import sys # 引入 sys 模組用於標準輸入輸出
import threading

# --- Configuration ---
SOURCE_DIR = "src"
INCLUDE_EXTENSIONS = [".py", ".json"]  # 檔案類型白名單
UPLOAD_IMAGES = True # 是否上傳圖片檔案
MPREMOTE_PORT = None  # 如需指定，如 "COM3" 或 "/dev/ttyACM0"
ENABLE_CLEAN = True  # 是否在上傳前清除舊檔

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
            else: # 如果讀到空行，可能是管道關閉或沒有更多數據
                if pipe.closed: # 檢查管道是否已關閉
                    break
                time.sleep(0.01) # 短暫等待，避免忙碌循環
        except ValueError: # 管道可能在讀取時被關閉 (例如，子進程關閉了寫入端)
            break
        except Exception as e:
            # print(f"讀取執行緒發生錯誤: {e}", file=sys.stderr) # 診斷用，實際部署時可註解掉
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

    # 啟動獨立執行緒來即時讀取 stdout 和 stderr
    stdout_thread = threading.Thread(target=_reader_thread, args=(process.stdout, sys.stdout))
    stderr_thread = threading.Thread(target=_reader_thread, args=(process.stderr, sys.stderr))

    stdout_thread.start()
    stderr_thread.start()

    try:
        # 等待子進程結束 (使用者在 mpremote repl 中按下 Ctrl+X)
        process.wait()
    except KeyboardInterrupt:
        print("\n捕獲到 Ctrl+C，正在終止 REPL 進程...")
    finally:
        # 設置事件以停止讀取執行緒
        stop_reader_event.set()
        # 等待讀取執行緒完成
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        
        # 關閉管道
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
        if process.stdin:
            process.stdin.close() # 雖然沒有寫入 stdin，但為完整性也關閉

        # 確保子進程已終止
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=1)
            if process.poll() is None:
                process.kill()
        
        print("REPL 連接已關閉。")
        # 清除事件狀態，以便下次運行時重新開始
        stop_reader_event.clear()


def run_command(command, ignore_exists_error=False, display_output=False, capture_output_only=False):
    """
    執行命令並捕獲輸出。
    :param command: 要執行的命令列表。
    :param ignore_exists_error: 是否忽略 "File exists" 錯誤。
    :param display_output: 是否直接在控制台顯示標準輸出和錯誤輸出。
                           如果為 False，輸出將被捕獲但不顯示，由調用者處理。
    :param capture_output_only: 如果為 True，則只返回 stdout 內容，不列印也不檢查錯誤。
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

def collect_files():
    all_files = []

    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if any(file.endswith(ext) for ext in INCLUDE_EXTENSIONS):
                full_path = os.path.join(root, file).replace("\\", "/")
                rel_path = os.path.relpath(full_path, SOURCE_DIR).replace("\\", "/")
                all_files.append((full_path, rel_path))

    if UPLOAD_IMAGES:
        image_dir = os.path.join(SOURCE_DIR, "image")
        if os.path.exists(image_dir):
            for root, dirs, files in os.walk(image_dir):
                for file in files:
                    if file.endswith(".bin"):
                        full_path = os.path.join(root, file).replace("\\", "/")
                        rel_path = os.path.relpath(full_path, SOURCE_DIR).replace("\\", "/")
                        all_files.append((full_path, rel_path))

    return all_files

def ensure_remote_dirs(path):
    base_cmd = get_mpremote_base()
    parts = path.split("/")
    current = ""
    for part in parts:
        if not part:
            continue
        current = f"{current}/{part}" if current else part
        subprocess.run(base_cmd + ["fs", "mkdir", f":{current}"], capture_output=True, text=True, encoding='latin-1')


def _clear_current_line():
    print("\r" + " " * 150 + "\r", end="", flush=True)

def _print_progress_line(current_command, progress, total_width=50):
    done_width = int(progress / 100 * total_width)
    bar = "█" * done_width + "-" * (total_width - done_width)
    print(f"\r[{bar}] {progress:.1f}% | {current_command.ljust(80)}", end="", flush=True)


def clean_device():
    print("Cleaning device: Deleting files with extensions {}...".format(INCLUDE_EXTENSIONS))
    base_cmd = get_mpremote_base()

    proc = subprocess.run(base_cmd + ["fs", "ls", "-r", ":"], capture_output=True, text=True, encoding='latin-1')
    if proc.returncode != 0:
        print("Warning: Could not list files. Maybe device is empty or not connected.")
        return

    all_remote_files_raw = proc.stdout.strip().splitlines()
    
    files_to_delete = []
    for line in all_remote_files_raw:
        parts = line.strip().split(maxsplit=1)
        if len(parts) < 2:
            continue
        file_name = parts[1]

        if any(file_name.endswith(ext) for ext in INCLUDE_EXTENSIONS):
            files_to_delete.append(file_name)

    if not files_to_delete:
        print("No matching files found to clean.")
        return

    print(f"Found {len(files_to_delete)} files to delete.")
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

def get_device_space_info():
    """
    獲取裝置的總空間、使用空間和剩餘可用空間。
    """
    _clear_current_line()
    print("\n📊 獲取裝置空間資訊...")
    base_cmd = get_mpremote_base()
    
    df_output = run_command(base_cmd + ["fs", "df"], capture_output_only=True)

    if not df_output:
        print("❌ 無法獲取裝置空間資訊。")
        print("請檢查裝置是否已連接並可被 mpremote 偵測到。")
        return

    print("\n--- mpremote fs df 原始輸出 ---")
    print(df_output)
    print("-------------------------------\n")

    lines = df_output.splitlines()
    if len(lines) < 2:
        print("❌ 無法解析裝置空間資訊。輸出行數不足。")
        return

    data_line = lines[1].strip()
    parts = data_line.split()

    if len(parts) >= 5:
        try:
            total_blocks = int(parts[1]) * 1024
            used_blocks = int(parts[2]) * 1024
            available_blocks = int(parts[3]) * 1024

            def format_bytes(size):
                if size < 1024:
                    return f"{size} B"
                elif size < 1024 * 1024:
                    return f"{size / 1024:.2f} KB"
                else:
                    return f"{size / (1024 * 1024):.2f} MB"

            print(f"總空間: {format_bytes(total_blocks)}")
            print(f"使用空間: {format_bytes(used_blocks)}")
            print(f"剩餘可用空間: {format_bytes(available_blocks)}")
        except ValueError:
            print("❌ 解析裝置空間數值時發生錯誤。")
            print(f"嘗試解析的行: '{data_line}'")
    else:
        print(f"❌ 無法解析裝置空間資訊的格式。預期的列數不足。實際列數: {len(parts)}")
        print(f"嘗試解析的行: '{data_line}'")

    print("")

def upload_files():
    base_cmd = get_mpremote_base()
    print("--- Pico W 自動部署開始 ---")

    if ENABLE_CLEAN:
        clean_device()

    file_list = collect_files()
    total_files = len(file_list)
    print(f"📦 共 {total_files} 個檔案要上傳")

    for i, (local_path, remote_path) in enumerate(file_list):
        current_file_num = i + 1
        progress_percent = (current_file_num / total_files) * 100

        dirs = os.path.dirname(remote_path)
        if dirs:
            current_command_text = f"建立目錄: :{dirs}"
            _print_progress_line(current_command_text, progress_percent)
            ensure_remote_dirs(dirs)

        cmd = base_cmd + ["fs", "cp", local_path, f":{remote_path}"]
        current_command_text = f"上傳檔案: {remote_path}"
        _print_progress_line(current_command_text, progress_percent)
        
        if not run_command(cmd, display_output=False):
            _clear_current_line()
            print(f"❌ 上傳失敗: {remote_path}")
            return
        
    _clear_current_line()
    print("\n✅ 上傳完成。") # 這裡只顯示上傳完成
    

    # 重啟裝置
    reset_device()

    print("等待裝置重啟並初始化...")
    time.sleep(5) 

    # 進入互動式 REPL
    print("\n現在您可以進入裝置 Terminal (REPL)... 按 Ctrl+X 退出。")
    interactive_repl(base_cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload files to Pico W.")
    parser.add_argument("--no-images", action="store_false", dest="upload_images", default=True,
                        help="Do not upload image files.")
    args = parser.parse_args()
    UPLOAD_IMAGES = args.upload_images
    upload_files()