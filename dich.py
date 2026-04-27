import os
import re
import json
import glob
import math

# --- CẤU HÌNH ---
CHUNK_SIZE = 5000
MAP_FILE = "translation_map.json"
EXPORT_PREFIX = "export_source"
IMPORT_PREFIX = "import_translated"

# Regex để nhận diện các thẻ của Ren'py: [biến], {thẻ}, %s, %(biến)s
TAG_PATTERN = re.compile(r'(\[[^\]]+\]|\{[^\}]+\}|%s|%\([^)]+\)[a-z])')

def mask_text(text):
    """Thay thế các thẻ code thành @@0@@, @@1@@..."""
    masks = {}
    masked_text = text
    matches = TAG_PATTERN.findall(text)
    
    for i, match in enumerate(matches):
        placeholder = f"@@{i}@@"
        masks[placeholder] = match
        masked_text = masked_text.replace(match, placeholder, 1)
        
    return masked_text, masks

def unmask_text(text, masks):
    """Khôi phục các thẻ code từ @@0@@, @@1@@... về nguyên bản"""
    for placeholder, original in masks.items():
        text = text.replace(placeholder, original)
    return text

def scan_and_export():
    print("\n--- BƯỚC 1: QUÉT VÀ XUẤT DỮ LIỆU ---")
    folder_path = input("Nhập đường dẫn đến thư mục ngôn ngữ (VD: game/tl/vietnamese): ").strip()
    
    if not os.path.exists(folder_path):
        print("❌ Không tìm thấy thư mục. Vui lòng kiểm tra lại đường dẫn.")
        return

    rpy_files = glob.glob(os.path.join(folder_path, "**", "*.rpy"), recursive=True)
    if not rpy_files:
        print("❌ Không tìm thấy file .rpy nào trong thư mục này.")
        return

    translation_map = {}
    export_lines = []
    line_id = 1

    for filepath in rpy_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for idx in range(len(lines)):
            line = lines[idx]
            stripped = line.lstrip()
            
            # CHỈ lấy nội dung từ các dòng có comment (bắt đầu bằng #) và có dấu ngoặc kép
            if stripped.startswith('#') and '"' in stripped:
                
                # Bỏ qua các dòng comment cấu trúc của Ren'py (ví dụ: # game/script.rpy:10)
                if stripped.startswith('# game/') or stripped.startswith('# TODO:'):
                    continue

                first_quote = line.find('"')
                last_quote = line.rfind('"')
                
                if first_quote != -1 and last_quote != -1 and first_quote != last_quote:
                    # Lấy text gốc để mang đi dịch
                    source_text = line[first_quote + 1:last_quote]
                    
                    if not source_text.strip():
                        continue

                    # TÌM DÒNG CHỨA BẢN DỊCH BÊN DƯỚI (dòng mc "")
                    target_idx = -1
                    for j in range(idx + 1, len(lines)):
                        next_line = lines[j]
                        next_stripped = next_line.lstrip()
                        
                        if not next_stripped:
                            continue # Bỏ qua dòng trống
                        if next_stripped.startswith('#'):
                            break # Nếu gặp comment mới thì dừng (nghĩa là không có dòng dịch)
                            
                        # Nếu tìm thấy dòng có chứa ngoặc kép mà không có dấu #
                        if '"' in next_stripped:
                            target_idx = j
                            break
                            
                    # Nếu tìm thấy dòng đích để chèn bản dịch
                    if target_idx != -1:
                        target_line = lines[target_idx]
                        t_first_quote = target_line.find('"')
                        t_last_quote = target_line.rfind('"')
                        
                        # Cắt lấy tiền tố (VD: '    mc "') và hậu tố (VD: '"\n') của dòng chèn dịch
                        prefix = target_line[:t_first_quote + 1]
                        suffix = target_line[t_last_quote:]
                        
                        # Bọc các biến code lại
                        masked_text, masks = mask_text(source_text)
                        
                        # LƯU VỊ TRÍ CỦA DÒNG BÊN DƯỚI (dòng mục tiêu)
                        translation_map[str(line_id)] = {
                            "file": filepath,
                            "line_idx": target_idx,
                            "prefix": prefix,
                            "suffix": suffix,
                            "masks": masks
                        }
                        
                        # Xuất dòng gốc ra cho file txt
                        export_lines.append(f"{line_id}|||{masked_text}")
                        line_id += 1

    # Lưu translation_map.json
    with open(MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(translation_map, f, ensure_ascii=False, indent=4)
    print(f"✔️ Đã tạo {MAP_FILE} thành công.")

    # Chunking: Chia nhỏ file nếu vượt quá CHUNK_SIZE
    total_lines = len(export_lines)
    if total_lines == 0:
        print("⚠️ Không có dòng thoại nào cần dịch.")
        return

    if total_lines <= CHUNK_SIZE:
        with open(f"{EXPORT_PREFIX}.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(export_lines))
        print(f"✔️ Đã xuất {total_lines} dòng ra {EXPORT_PREFIX}.txt.")
    else:
        num_chunks = math.ceil(total_lines / CHUNK_SIZE)
        for i in range(num_chunks):
            chunk = export_lines[i * CHUNK_SIZE : (i + 1) * CHUNK_SIZE]
            part_name = f"{EXPORT_PREFIX}_part{i+1:03d}.txt"
            with open(part_name, "w", encoding="utf-8") as f:
                f.write("\n".join(chunk))
        print(f"✔️ Đã xuất {total_lines} dòng và chia thành {num_chunks} file (part001, part002...).")

def merge_and_import():
    print("\n--- BƯỚC 3: CHÈN BẢN DỊCH VÀO GAME ---")
    
    if not os.path.exists(MAP_FILE):
        print(f"❌ Không tìm thấy {MAP_FILE}. Hãy chạy lệnh Export trước.")
        return

    with open(MAP_FILE, 'r', encoding='utf-8') as f:
        translation_map = json.load(f)

    # Tìm các file dịch
    txt_files = glob.glob(f"{IMPORT_PREFIX}*.txt")
    if not txt_files:
        print(f"⚠️ Không tìm thấy file {IMPORT_PREFIX}*.txt. Sẽ thử tìm các file {EXPORT_PREFIX}*.txt...")
        txt_files = glob.glob(f"{EXPORT_PREFIX}*.txt")
        
    if not txt_files:
        print("❌ Không tìm thấy bất kỳ file txt nào để import.")
        return

    print(f"🔄 Đã tìm thấy {len(txt_files)} file dịch. Đang tiến hành gộp và xử lý...")
    
    translated_data = {}
    for txt_file in txt_files:
        with open(txt_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if "|||" in line:
                    parts = line.split("|||", 1)
                    t_id = parts[0].strip()
                    t_text = parts[1].strip()
                    translated_data[t_id] = t_text

    files_to_update = {}
    success_count = 0

    for t_id, mapped_info in translation_map.items():
        if t_id in translated_data:
            filepath = mapped_info["file"]
            line_idx = mapped_info["line_idx"]
            
            if filepath not in files_to_update:
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        files_to_update[filepath] = f.readlines()
                else:
                    continue
            
            # Tiền xử lý bản dịch
            raw_translated_text = translated_data[t_id]
            safe_translated_text = raw_translated_text.replace('"', "'")
            final_text = unmask_text(safe_translated_text, mapped_info["masks"])
            
            # Chèn đúng vào vị trí prefix và suffix của dòng mục tiêu (dòng mc "")
            new_line = mapped_info["prefix"] + final_text + mapped_info["suffix"]
            files_to_update[filepath][line_idx] = new_line
            success_count += 1

    # Ghi đè vào các file .rpy
    for filepath, lines in files_to_update.items():
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    print(f"✔️ Thành công! Đã chèn {success_count} dòng dịch vào các file .rpy gốc.")

def main():
    while True:
        print("\n" + "="*40)
        print(" CÔNG CỤ XỬ LÝ DỊCH THUẬT REN'PY ")
        print("="*40)
        print("1. Scan & Export (Quét thư mục và xuất file txt)")
        print("2. Import (Gộp file txt và ghi đè vào game)")
        print("3. Thoát")
        
        choice = input("👉 Nhập lựa chọn của bạn (1/2/3): ").strip()
        
        if choice == '1':
            scan_and_export()
        elif choice == '2':
            merge_and_import()
        elif choice == '3':
            print("Tạm biệt!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ. Vui lòng nhập 1, 2 hoặc 3.")

if __name__ == "__main__":
    main()
