import os
import re
import json
import time
from datetime import datetime

# ==========================================
# ⚙️ CẤU HÌNH MẶC ĐỊNH
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
    path = os.path.join(LOG_DIR, "progress.json")
    if os.path.exists(path):
        with open(path, "r", encoding=ENCODING) as f:
            return json.load(f)
    return {}

def save_progress(progress):
    path = os.path.join(LOG_DIR, "progress.json")
    with open(path, "w", encoding=ENCODING) as f:
        json.dump(progress, f, indent=4)

def mask_text(text):
    masks = []
    def repl(match):
        masks.append(match.group(0))
        return PLACEHOLDER_PATTERN.format(len(masks)-1)
    
    masked_text = re.sub(r'(\[.*?\]|\{.*?\})', repl, text)
    return masked_text, masks

def unmask_text(masked_text, masks):
    text = masked_text
    for i, mask in enumerate(masks):
        placeholder = PLACEHOLDER_PATTERN.format(i)
        if placeholder not in text:
            raise ValueError(f"unmask_failed: Missing {placeholder} in translated text")
        text = text.replace(placeholder, mask)
    return text

# ==========================================
# 1️⃣ CHỨC NĂNG SCAN & EXPORT (CẬP NHẬT THEO LOGIC REN'PY CHUẨN)
# ==========================================
def cmd_export(source_lang_dir):
    print(f"\n🚀 Bắt đầu quá trình SCAN & EXPORT từ: {source_lang_dir}")
    setup_dirs()
    
    chunk_idx = 1
    current_chunk_data = []
    current_chunk_map = {}
    global_id = 1
    
    # Lấy danh sách chỉ quét file .rpy
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

        for idx in range(len(lines)):
            line = lines[idx]
            stripped = line.lstrip()

            # Chỉ lấy nội dung từ các dòng có comment (bắt đầu bằng #) và có dấu ngoặc kép
            if stripped.startswith('#') and '"' in stripped:
                
                # Bỏ qua các dòng comment cấu trúc của Ren'py
                if stripped.startswith('# game/') or stripped.startswith('# TODO:'):
                    continue

                first_quote = line.find('"')
                last_quote = line.rfind('"')
                
                if first_quote != -1 and last_quote != -1 and first_quote != last_quote:
                    # Lấy text gốc để mang đi dịch
                    source_text = line[first_quote + 1:last_quote]
                    
                    if not source_text.strip():
                        continue

                    # Tìm dòng chứa bản dịch bên dưới
                    target_idx = -1
                    for j in range(idx + 1, len(lines)):
                        next_line = lines[j]
                        next_stripped = next_line.lstrip()
                        
                        if not next_stripped:
                            continue 
                        if next_stripped.startswith('#'):
                            break 
                            
                        # Nếu tìm thấy dòng có chứa ngoặc kép mà không có dấu #
                        if '"' in next_stripped:
                            target_idx = j
                            break
                            
                    # Nếu tìm thấy dòng đích để chèn bản dịch
                    if target_idx != -1:
                        target_line = lines[target_idx]
                        t_first_quote = target_line.find('"')
                        t_last_quote = target_line.rfind('"')
                        
                        # An toàn kiểm tra ngoặc ở target line
                        if t_first_quote != -1 and t_last_quote != -1 and t_first_quote != t_last_quote:
                            # prefix và suffix đã bao gồm ngoặc kép bên trong
                            prefix = target_line[:t_first_quote + 1]
                            suffix = target_line[t_last_quote:]
                            
                            # Unescape source text trước khi mask
                            source_text_unescaped = source_text.replace('\\"', '"')
                            
                            # Bọc các biến code lại
                            masked_text, masks = mask_text(source_text_unescaped)
                            
                            str_id = f"{global_id:06d}"
                            
                            current_chunk_map[str_id] = {
                                "file": filepath,
                                "line_idx": target_idx,  # Lưu trữ dòng đích (để import đúng chỗ)
                                "prefix": prefix,
                                "suffix": suffix,
                                "masks": masks,
                                "original_text": source_text
                            }
                            
                            current_chunk_data.append(f"{str_id}{DELIMITER}{masked_text}\n")
                            global_id += 1
                            
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
        
        # SỬ DỤNG enumerate ĐỂ LẤY SỐ DÒNG CỦA FILE TXT (BẮT ĐẦU TỪ 1)
        for import_line_idx, line_raw in enumerate(import_lines, start=1):
            # Dùng strip() trống để xóa cả \n, \r và khoảng trắng vô tình lọt vào đầu/cuối dòng
            line = line_raw.strip() 
            if not line: continue
            
            parts = line.split(DELIMITER, 1)
            if len(parts) < 2:
                log_error(errors, "malformed_line", "NO_ID", f"import_{part_name}.txt", import_line_idx, "", line, "Thiếu delimiter |||")
                skipped_count += 1
                continue
                
            # Đảm bảo gọt sạch khoảng trắng xung quanh ID 
            # (VD: lỡ tay gõ "000001 |||" -> vẫn nhận đúng "000001")
            item_id = parts[0].strip() 
            translated_text = parts[1] # Giữ nguyên text, vì đôi khi dịch cần khoảng trắng
            
            if item_id in import_data:
                log_error(errors, "duplicated_id", item_id, f"import_{part_name}.txt", import_line_idx, "", translated_text, "Kept last, skipped previous")
            
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
                
            # Cần escape % theo cấu trúc Ren'Py và escape double quote (" -> \")
            final_text = translated_unmasked.replace('%', '\\%').replace('"', '\\"')
            
            # CẬP NHẬT: prefix và suffix đã tự bao gồm ngoặc kép ("), nên không cần bọc thêm nữa
            final_line = f"{map_info['prefix']}{final_text}{map_info['suffix']}"
            
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
# 🚀 MENU TƯƠNG TÁC
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
