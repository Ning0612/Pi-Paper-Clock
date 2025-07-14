import subprocess
import os
import argparse

# --- Configuration ---
SOURCE_DIR = "src"
INCLUDE_EXTENSIONS = [".py", ".json"]  # 檔案類型白名單
UPLOAD_IMAGES = True # 是否上傳圖片檔案
MPREMOTE_PORT = None  # 如需指定，如 "COM3" 或 "/dev/ttyACM0"
ENABLE_CLEAN = True  # 是否在上傳前清除舊檔

def run_command(command, ignore_exists_error=False):
    print(f"\n> Executing: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        if result.stdout.strip():
            print(result.stdout)
        if result.stderr.strip():
            if not (ignore_exists_error and "File exists" in result.stderr):
                print(f"[stderr] {result.stderr}")
        return True
    except FileNotFoundError:
        print("❌ 找不到 mpremote，請執行：pip install mpremote")
        return False
    except subprocess.CalledProcessError as e:
        if ignore_exists_error and "File exists" in e.stderr:
            return True
        print(f"❌ 指令失敗：{' '.join(command)}")
        print(f"[stdout]\n{e.stdout}")
        print(f"[stderr]\n{e.stderr}")
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
        run_command(base_cmd + ["fs", "mkdir", f":{current}"])

def clean_device():
    print("🧹 清除裝置上舊有檔案...")
    base_cmd = get_mpremote_base()

    result = subprocess.run(base_cmd + ["fs", "ls"], capture_output=True, text=True, encoding='utf-8')
    lines = result.stdout.strip().splitlines()
    for line in lines:
        parts = line.strip().split()  # 通常格式為 "[size] filename"
        if len(parts) == 2:
            filename = parts[1]
        else:
            filename = parts[0]
        if filename and filename != ":":
            run_command(base_cmd + ["fs", "rm", f":{filename}"])

def reset_device():
    print("\n🔄 重啟裝置...")
    base_cmd = get_mpremote_base()
    run_command(base_cmd + ["reset"])

def upload_files():
    base_cmd = get_mpremote_base()
    print("--- Pico W 自動部署開始 ---")

    if ENABLE_CLEAN:
        clean_device()

    file_list = collect_files()
    print(f"📦 共 {len(file_list)} 個檔案要上傳")

    for local_path, remote_path in file_list:
        # 自動建立子資料夾（先切出目錄部分）
        dirs = os.path.dirname(remote_path)
        if dirs:
            ensure_remote_dirs(dirs)

        # 上傳檔案
        cmd = base_cmd + ["fs", "cp", local_path, f":{remote_path}"]
        if not run_command(cmd):
            print(f"❌ 上傳失敗：{remote_path}")
            return
        
    print("\n✅ 上傳完成。你可以使用 `mpremote repl` 進入裝置。")
    reset_device()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload files to Pico W.")
    parser.add_argument("--no-images", action="store_false", dest="upload_images", default=True,
                        help="Do not upload image files.")
    args = parser.parse_args()
    UPLOAD_IMAGES = args.upload_images
    upload_files()
