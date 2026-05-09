import os
import re
import json
import time
from datetime import datetime

# ==========================================
# ⚙️ CẤU HÌNH MẶC ĐỊNH (CÁC THƯ MỤC LÀM VIỆC)
# ==========================================
CHUNK_SIZE = 5000
MAP_DIR = "map/"
EXPORT_DIR = "export/"
IMPORT_DIR = "import/"
PATCHED_DIR = "_patched/"
LOG_DIR = "_logs/"
PLACEHOLDER_PATTERN = "@@{}@@"
DELIMITER = "|||"
ENCODING = "utf-8"

# ==========================================
# 🛠️ CÁC HÀM TIỆN ÍCH & KHỞI TẠO
# ==========================================
def setup_dirs():
    """Khởi tạo cấu trúc thư mục nếu chưa tồn tại"""
    for d in [MAP_DIR, EXPORT_DIR, IMPORT_DIR, PATCHED_DIR, LOG_DIR]:
        os.makedirs(d, exist_ok=True)

def load_progress():
    """Đọc trạng thái progress.json"""
    path = os.path.join(LOG_DIR, "progress.json")
    if os.path.exists(path):
        with open(path, "r", encoding=ENCODING) as f:
            return json.load(f)
    return {}

def save_progress(progress):
    """Lưu trạng thái progress.json"""
    path = os.path.join(LOG_DIR, "progress.json")
    with open(path, "w", encoding=ENCODING) as f:
        json.dump(progress, f, indent=4)

def mask_text(text):
    """Trích xuất placeholder và trả về chuỗi đã mask"""
    masks = []
    # Tìm các tag Ren'Py thông dụng: [var], {b}, {/b}, {color=#fff}
    def repl(match):
        masks.append(match.group(0))
        return PLACEHOLDER_PATTERN.format(len(masks)-1)
    
    masked_text = re.sub(r'(\[.*?\]|\{.*?\})', repl, text)
    return masked_text, masks

def unmask_text(masked_text, masks):
    """Khôi phục placeholder từ chuỗi đã mask"""
    text = masked_text
    for i, mask in enumerate(masks):
        placeholder = PLACEHOLDER_PATTERN.format(i)
        if placeholder not in text:
            raise ValueError(f"unmask_failed: Missing {placeholder} in translated text")
        text = text.replace(placeholder, mask)
    return text

# ==========================================
# 1️⃣ CHỨC NĂNG SCAN & EXPORT
# ==========================================
def cmd_export(source_lang_dir):
    print(f"\n🚀 Bắt đầu quá trình SCAN & EXPORT từ: {source_lang_dir}")
    setup_dirs()
    
    chunk_idx = 1
    current_chunk_data = []
    current_chunk_map = {}
    global_id = 1
    
    # Lấy danh sách file .rpy
    rpy_files = []
    for root, _, files in os.walk(source_lang_dir):
        for file in files:
            if file.endswith(".rpy"):
                rpy_files.append(os.path.join(root, file))
                
    if not rpy_files:
        print("❌ Không tìm thấy file .rpy nào trong thư mục này!")
        return

    for filepath in rpy_files:
        try:
            with open(filepath, "r", encoding=ENCODING) as f:
                lines = f.readlines()
        except Exception as e:
            print(f"❌ Lỗi đọc file {filepath}: {e}")
            continue

        for line_idx, line in enumerate(lines):
            # Regex parse dòng code Ren'Py chứa chuỗi: prefix "text" suffix
            match = re.match(r'^(\s*(?:[a-zA-Z0-9_]+\s+)?)("(.*(?<!\\))"|\'(.*(?<!\\))\')(\s*)$', line)
            
            # Chỉ bắt dòng có thoại (không bắt dòng comment bắt đầu bằng #)
            if match and not line.lstrip().startswith("#"):
                prefix = match.group(1)
                full_quotes = match.group(2)
                original_text = match.group(3) if match.group(3) is not None else match.group(4)
                suffix = match.group(5)
                
                # Unescape quote để xử lý mask dễ hơn
                original_text_unescaped = original_text.replace('\\"', '"').replace("\\'", "'")
                
                masked_text, masks = mask_text(original_text_unescaped)
                str_id = f"{global_id:06d}"
                
                # Lưu vào map
                current_chunk_map[str_id] = {
                    "file": filepath,
                    "line_idx": line_idx,
                    "prefix": prefix,
                    "suffix": suffix,
                    "masks": masks,
                    "original_text": original_text,
                    "quote_char": full_quotes[0]
                }
                
                # Lưu vào export
                current_chunk_data.append(f"{str_id}{DELIMITER}{masked_text}\n")
                global_id += 1
                
                # Flush chunk nếu đạt giới hạn
                if len(current_chunk_data) >= CHUNK_SIZE:
                    save_chunk(chunk_idx, current_chunk_data, current_chunk_map)
                    chunk_idx += 1
                    current_chunk_data = []
                    current_chunk_map = {}
                    
    # Lưu phần còn dư
    if current_chunk_data:
        save_chunk(chunk_idx, current_chunk_data, current_chunk_map)
        
    print(f"✅ EXPORT hoàn tất! Đã tạo {chunk_idx if current_chunk_data else chunk_idx-1} chunks.")

def save_chunk(chunk_idx, data, mapping):
    part_name = f"part{chunk_idx:03d}"
    
    with open(os.path.join(EXPORT_DIR, f"export_{part_name}.txt"), "w", encoding=ENCODING) as f:
        f.writelines(data)
        
    with open(os.path.join(MAP_DIR, f"{part_name}.json"), "w", encoding=ENCODING) as f:
        json.dump(mapping, f, indent=4, ensure_ascii=False)
        
    progress = load_progress()
    progress[part_name] = "PENDING"
    save_progress(progress)

# ==========================================
# 3️⃣ & 4️⃣ VALIDATION, IMPORT & LOGGING
# ==========================================
def log_error(errors_list, error_type, item_id, file, line_idx, original, translated, note):
    errors_list.append({
        "id": item_id,
        "file": file,
        "line_idx": line_idx,
        "error_type": error_type,
        "original_text": original,
        "translated_text": translated,
        "note": note
    })

def cmd_import(target_chunk=None):
    print("\n📥 Bắt đầu quá trình VALIDATION & IMPORT...")
    setup_dirs()
    progress = load_progress()
    
    chunks_to_run = []
    if target_chunk:
        chunks_to_run = [target_chunk]
    else:
        chunks_to_run = [k for k, v in progress.items() if v != "DONE"]
        
    if not chunks_to_run:
        print("✅ Tất cả các chunk đã DONE hoặc chưa có file export nào.")
        return

    for part_name in chunks_to_run:
        start_time = time.time()
        map_file = os.path.join(MAP_DIR, f"{part_name}.json")
        import_file = os.path.join(IMPORT_DIR, f"import_{part_name}.txt")
        
        if not os.path.exists(map_file) or not os.path.exists(import_file):
            print(f"⚠️ Bỏ qua {part_name}: Thiếu file map hoặc file chưa được đặt vào thư mục import.")
            continue
            
        print(f"⏳ Đang xử lý {part_name}...")
        
        with open(map_file, "r", encoding=ENCODING) as f:
            chunk_map = json.load(f)
            
        with open(import_file, "r", encoding=ENCODING) as f:
            import_lines = f.readlines()

        import_data = {}
        errors = []
        success_count = 0
        skipped_count = 0
        
        for line_raw in import_lines:
            line = line_raw.strip('\n')
            if not line: continue
            
            parts = line.split(DELIMITER, 1)
            if len(parts) < 2:
                log_error(errors, "malformed_line", "UNKNOWN", "UNKNOWN", -1, "", line, "Thiếu delimiter |||")
                skipped_count += 1
                continue
                
            item_id, translated_text = parts[0], parts[1]
            
            if item_id in import_data:
                log_error(errors, "duplicated_id", item_id, "UNKNOWN", -1, "", translated_text, "Kept last, skipped previous")
            
            import_data[item_id] = translated_text
            
        file_updates = {}
        
        for item_id, map_info in chunk_map.items():
            file_path = map_info["file"]
            line_idx = map_info["line_idx"]
            original_text = map_info["original_text"]
            masks = map_info["masks"]
            
            if item_id not in import_data:
                log_error(errors, "missing_in_import", item_id, file_path, line_idx, original_text, "", "ID không có trong file dịch")
                skipped_count += 1
                continue
                
            translated_masked = import_data[item_id]
            
            expected_mask_count = len(masks)
            actual_mask_count = sum(1 for i in range(expected_mask_count) if PLACEHOLDER_PATTERN.format(i) in translated_masked)
            
            if actual_mask_count != expected_mask_count:
                log_error(errors, "placeholder_mismatch", item_id, file_path, line_idx, original_text, translated_masked, f"Expect {expected_mask_count}, got {actual_mask_count}")
                skipped_count += 1
                continue
                
            try:
                translated_unmasked = unmask_text(translated_masked, masks)
            except ValueError as e:
                log_error(errors, "unmask_failed", item_id, file_path, line_idx, original_text, translated_masked, str(e))
                skipped_count += 1
                continue
                
            final_text = translated_unmasked.replace('%', '\\%')
            quote_char = map_info["quote_char"]
            if quote_char == '"':
                final_text = final_text.replace('"', '\\"')
            elif quote_char == "'":
                final_text = final_text.replace("'", "\\'")
                
            final_line = f"{map_info['prefix']}{quote_char}{final_text}{quote_char}{map_info['suffix']}\n"
            
            if file_path not in file_updates:
                file_updates[file_path] = {}
            file_updates[file_path][line_idx] = final_line

        for file_path, updates in file_updates.items():
            patched_file_path = os.path.join(PATCHED_DIR, file_path)
            os.makedirs(os.path.dirname(patched_file_path), exist_ok=True)
            
            src_file_path = patched_file_path if os.path.exists(patched_file_path) else file_path
            
            if not os.path.exists(src_file_path):
                print(f"🔥 CRITICAL: Không tìm thấy file gốc {src_file_path}")
                continue
                
            try:
                with open(src_file_path, "r", encoding=ENCODING) as f:
                    file_lines = f.readlines()
                    
                for line_idx, new_line in updates.items():
                    if line_idx >= len(file_lines):
                        log_error(errors, "line_idx_out_of_range", "UNKNOWN", file_path, line_idx, "", "", f"Max index: {len(file_lines)-1}")
                        skipped_count += 1
                    else:
                        file_lines[line_idx] = new_line
                        success_count += 1
                        
                with open(patched_file_path, "w", encoding=ENCODING) as f:
                    f.writelines(file_lines)
            except Exception as e:
                print(f"🔥 Lỗi xử lý file {file_path}: {e}")
                continue

        elapsed = int(time.time() - start_time)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        if errors:
            with open(os.path.join(LOG_DIR, f"errors_{part_name}.json"), "w", encoding=ENCODING) as f:
                json.dump(errors, f, indent=4, ensure_ascii=False)
                
        summary_text = f"✅ Processed: {success_count} | ⏭️ Skipped: {skipped_count} | ⏱️ {elapsed}s"
        with open(os.path.join(LOG_DIR, f"summary_{part_name}.txt"), "w", encoding=ENCODING) as f:
            f.write(summary_text)
            
        print(f"  └─ {summary_text}")
        
        progress[part_name] = "DONE" if skipped_count == 0 else "REVIEW_NEEDED"
        save_progress(progress)

# ==========================================
# 🚀 MENU TƯƠNG TÁC (INTERACTIVE ENTRYPOINT)
# ==========================================
def main_menu():
    setup_dirs()
    while True:
        print("\n" + "="*50)
        print("🎮 DỰ ÁN: CÔNG CỤ DỊCH GAME REN'PY")
        print("="*50)
        print("1. [EXPORT] Trích xuất text từ thư mục game")
        print("2. [IMPORT] Import toàn bộ các phần chưa hoàn thành")
        print("3. [IMPORT] Import lại một phần cụ thể (VD: part001)")
        print("0. Thoát")
        print("-" * 50)
        
        choice = input("👉 Nhập lựa chọn của bạn (0-3): ").strip()
        
        if choice == '1':
            source_dir = input("📂 Nhập đường dẫn thư mục chứa file .rpy (VD: game/tl/vietnamese): ").strip()
            # Bỏ dấu nháy kép nếu người dùng copy paste từ Windows
            source_dir = source_dir.strip('"').strip("'")
            if os.path.exists(source_dir):
                cmd_export(source_dir)
            else:
                print("❌ Đường dẫn không tồn tại, vui lòng kiểm tra lại!")
        
        elif choice == '2':
            cmd_import(None)
            
        elif choice == '3':
            part_target = input("🧩 Nhập tên phần muốn import (VD: part001): ").strip()
            if part_target:
                cmd_import(part_target)
            else:
                print("❌ Tên phần không được để trống!")
                
        elif choice == '0':
            print("👋 Đã thoát chương trình. Hẹn gặp lại!")
            break
            
        else:
            print("❌ Lựa chọn không hợp lệ. Vui lòng thử lại!")

if __name__ == "__main__":
    main_menu()
