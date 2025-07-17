import subprocess
import os
import argparse
import time 

# --- Configuration ---
SOURCE_DIR = "src"
INCLUDE_EXTENSIONS = [".py", ".json"]  # 檔案類型白名單
UPLOAD_IMAGES = True # 是否上傳圖片檔案
MPREMOTE_PORT = None  # 如需指定，如 "COM3" 或 "/dev/ttyACM0"
ENABLE_CLEAN = True  # 是否在上傳前清除舊檔

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
        # 關鍵修改：將 encoding 從 'utf-8' 改為 'latin-1'，以便處理所有單一字節的數據
        # 這有助於避免 UnicodeDecodeError，特別是當裝置輸出非標準字元時
        result = subprocess.run(command, check=not capture_output_only, capture_output=True, text=True, encoding='latin-1') 
        
        if capture_output_only:
            return result.stdout.strip()

        # 確保 result.stdout 不是 None 才進行 strip() 操作
        stdout_str = result.stdout.strip() if result.stdout else ""
        stderr_str = result.stderr.strip() if result.stderr else ""

        if display_output and stdout_str:
            print(stdout_str)
        if display_output and stderr_str:
            if not (ignore_exists_error and "File exists" in stderr_str):
                print(f"[stderr] {stderr_str}")
        return True
    except FileNotFoundError:
        if display_output:
            print("❌ 找不到 mpremote，請執行：pip install mpremote")
        return False
    except subprocess.CalledProcessError as e:
        if ignore_exists_error and "File exists" in e.stderr:
            return True
        if display_output:
            print(f"❌ 指令失敗：{' '.join(command)}")
            print(f"[stdout]\n{e.stdout.strip()}")
            print(f"[stderr]\n{e.stderr.strip()}")
        return False
    except Exception as e: # 捕獲其他潛在異常，例如 UnicodeDecodeError (雖然已改 encoding 但仍可作為備用)
        if display_output:
            print(f"❌ 執行命令時發生意外錯誤: {e}")
        return False


def get_mpremote_base():
    return ["mpremote", "connect", MPREMOTE_PORT] if MPREMOTE_PORT else ["mpremote"]

def collect_files():
    all_files = []

    # Collect Python and JSON files
    for root, dirs, files in os.walk(SOURCE_DIR):
        for file in files:
            if any(file.endswith(ext) for ext in INCLUDE_EXTENSIONS):
                full_path = os.path.join(root, file).replace("\\", "/")
                rel_path = os.path.relpath(full_path, SOURCE_DIR).replace("\\", "/")
                all_files.append((full_path, rel_path))

    # Collect image files if UPLOAD_IMAGES is True
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
    """遞迴建立遠端目錄結構，如 image/custom"""
    base_cmd = get_mpremote_base()
    parts = path.split("/")
    current = ""
    for part in parts:
        if not part:
            continue
        current = f"{current}/{part}" if current else part
        # 執行 mkdir 但不顯示其輸出，因為我們在主迴圈控制顯示
        subprocess.run(base_cmd + ["fs", "mkdir", f":{current}"], capture_output=True, text=True, encoding='latin-1') # 這裡也改為 latin-1


def _clear_current_line():
    """清空當前控制台行"""
    # 移動游標到行首，然後用空格覆蓋整行，再將游標移回行首
    print("\r" + " " * 150 + "\r", end="", flush=True) # 假設一行最多150個字元

def _print_progress_line(current_command, progress, total_width=50):
    """
    輔助函式：列印進度條和當前指令。
    :param current_command: 當前正在執行的指令文字。
    :param progress: 介於 0 到 100 之間的進度百分比。
    :param total_width: 進度條的總寬度（字元數）。
    """
    done_width = int(progress / 100 * total_width)
    bar = "█" * done_width + "-" * (total_width - done_width)
    # 使用 \r 確保在同一行更新
    print(f"\r[{bar}] {progress:.1f}% | {current_command.ljust(80)}", end="", flush=True)


def clean_device():
    print("Cleaning device: Deleting files with extensions {}...".format(INCLUDE_EXTENSIONS))
    base_cmd = get_mpremote_base()

    # Recursively list all files from the root directory
    # 這裡也改為 latin-1
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

        # 執行刪除命令，但不讓它直接列印輸出，避免干擾進度條
        success = run_command(base_cmd + ["fs", "rm", f":{f}"], display_output=False)
        if not success:
            # 如果刪除失敗，清除進度條行，然後列印錯誤訊息
            _clear_current_line()
            print(f"❌ 刪除失敗: {f}")
            # 可以選擇在此處終止，或繼續嘗試刪除其他檔案
    _clear_current_line() # 完成刪除後，清空最後一行進度條
    print("✅ 檔案清除完成。\n") # 清除完成後列印確認訊息並換行

def reset_device():
    _clear_current_line() # 清除當前可能的進度條
    print("\n🔄 重啟裝置...")
    base_cmd = get_mpremote_base()
    # 這裡也改為 latin-1
    run_command(base_cmd + ["reset"], display_output=True) # 顯示 reset 命令的輸出

def get_device_space_info():
    """
    獲取裝置的總空間、使用空間和剩餘可用空間。
    """
    _clear_current_line() # 清除當前可能的進度條
    print("\n📊 獲取裝置空間資訊...")
    base_cmd = get_mpremote_base()
    
    # 執行 mpremote fs df 並捕獲輸出
    df_output = run_command(base_cmd + ["fs", "df"], capture_output_only=True)

    if not df_output:
        print("❌ 無法獲取裝置空間資訊。")
        print("請檢查裝置是否已連接並可被 mpremote 偵測到。") # 新增提示
        return

    # *** 新增：列印 mpremote fs df 的原始輸出，以利診斷 ***
    print("\n--- mpremote fs df 原始輸出 ---")
    print(df_output)
    print("-------------------------------\n")
    # *************************************************

    # 解析 df_output
    # 預期輸出格式類似:
    # Filesystem                  1K-blocks      Used  Available Use% Mounted on
    # <block_device_name>              xxxx      yyyy       zzzz   xx% /flash
    lines = df_output.splitlines()
    if len(lines) < 2:
        print("❌ 無法解析裝置空間資訊。輸出行數不足。") # 修改提示
        return

    data_line = lines[1].strip() # 假設資料在第二行
    parts = data_line.split()

    if len(parts) >= 5:
        try:
            total_blocks = int(parts[1]) * 1024 # 轉換為 Bytes
            used_blocks = int(parts[2]) * 1024 # 轉換為 Bytes
            available_blocks = int(parts[3]) * 1024 # 轉換為 Bytes

            def format_bytes(size):
                # 格式化 Bytes 為更易讀的單位 (KB, MB)
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
            print(f"嘗試解析的行: '{data_line}'") # 顯示哪一行導致解析失敗
    else:
        print(f"❌ 無法解析裝置空間資訊的格式。預期的列數不足。實際列數: {len(parts)}") # 修改提示
        print(f"嘗試解析的行: '{data_line}'") # 顯示哪一行導致解析失敗

    print("") # 顯示完資訊後換行

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

        # 自動建立子資料夾（先切出目錄部分）
        dirs = os.path.dirname(remote_path)
        if dirs:
            current_command_text = f"建立目錄: :{dirs}"
            _print_progress_line(current_command_text, progress_percent)
            ensure_remote_dirs(dirs) # ensure_remote_dirs 內部不列印輸出

        # 上傳檔案
        cmd = base_cmd + ["fs", "cp", local_path, f":{remote_path}"]
        current_command_text = f"上傳檔案: {remote_path}"
        _print_progress_line(current_command_text, progress_percent)
        
        # 執行上傳命令，不讓它直接列印輸出
        if not run_command(cmd, display_output=False):
            _clear_current_line() # 上傳失敗時，清除進度條行
            print(f"❌ 上傳失敗: {remote_path}")
            return # 終止上傳流程
        
    _clear_current_line() # 上傳完成後，清空最後一行進度條
    print("\n✅ 上傳完成。你可以使用 `mpremote repl` 進入裝置。") 
    
    # 在這裡顯示裝置空間資訊
    get_device_space_info() # 新增的函式呼叫

    reset_device()

    print("等待裝置重啟並初始化...")
    time.sleep(5) 

    _clear_current_line() # 清除可能的舊進度條
    print("\n🖥️ 連接到裝置 Terminal (REPL)... 按 Ctrl+X 退出。")
    # 這裡也改為 latin-1
    run_command(base_cmd + ["repl"], display_output=True) # repl 命令的輸出需要直接顯示


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload files to Pico W.")
    parser.add_argument("--no-images", action="store_false", dest="upload_images", default=True,
                        help="Do not upload image files.")
    args = parser.parse_args()
    UPLOAD_IMAGES = args.upload_images
    upload_files()