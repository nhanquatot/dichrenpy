import os
import glob
import re

def convert_utf8_bom():
    """Chuyển tất cả file .txt trong thư mục từ UTF-8-BOM sang UTF-8"""
    files = glob.glob("*.txt")
    converted_count = 0
    for filepath in files:
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            # Kiểm tra BOM: b'\xef\xbb\xbf'
            if content.startswith(b'\xef\xbb\xbf'):
                text = content.decode('utf-8')
                with open(filepath, 'wb') as f:
                    f.write(text.encode('utf-8'))
                converted_count += 1
        except Exception as e:
            print(f"⚠️ Lỗi xử lý file {filepath}: {e}")
    print(f"✅ Đã chuyển đổi thành công {converted_count} file từ UTF-8-BOM sang UTF-8.")

def merge_files():
    """Gộp các file import_part*.txt thành import.txt theo đúng thứ tự số, sau đó xóa file gốc"""
    pattern = re.compile(r'^import_part\d+\.txt$')
    files = [f for f in os.listdir('.') if pattern.match(f)]
    
    if not files:
        print("❌ Không tìm thấy file nào khớp mẫu import_part*.txt")
        return

    # Sắp xếp tự nhiên theo số (hỗ trợ cả 001, 1, 002, 2...)
    files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
    
    output_file = "import.txt"
    if os.path.exists(output_file):
        confirm = input(f"⚠️ File '{output_file}' đã tồn tại. Gán đè? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ Đã hủy thao tác.")
            return

    with open(output_file, 'w', encoding='utf-8') as out_f:
        for f in files:
            with open(f, 'r', encoding='utf-8') as in_f:
                for line in in_f:
                    out_f.write(line)
                    # Đảm bảo mỗi file phần kết thúc bằng xuống dòng, tránh dính dòng
                    if not line.endswith('\n'):
                        out_f.write('\n')

    # Xóa file gốc sau khi gộp thành công
    for f in files:
        os.remove(f)
    print(f"✅ Đã gộp {len(files)} file thành '{output_file}' và xóa các file gốc.")

def split_file():
    """Cắt file txt thành các file nhỏ 5000 dòng, đặt tên import_part001.txt, import_part002.txt..."""
    filename = input("📁 Nhập tên file cần cắt (mặc định: import.txt): ").strip()
    if not filename:
        filename = "import.txt"
        
    if not os.path.exists(filename):
        print(f"❌ File '{filename}' không tồn tại.")
        return

    lines_per_chunk = 5000
    chunk_num = 1
    line_count = 0
    out_f = None

    try:
        with open(filename, 'r', encoding='utf-8') as in_f:
            for line in in_f:
                if line_count % lines_per_chunk == 0:
                    if out_f:
                        out_f.close()
                    out_filename = f"import_part{chunk_num:03d}.txt"
                    out_f = open(out_filename, 'w', encoding='utf-8')
                    chunk_num += 1
                out_f.write(line)
                line_count += 1
        if out_f:
            out_f.close()
        print(f"✅ Đã cắt thành công thành {chunk_num - 1} file (mỗi file {lines_per_chunk} dòng).")
    except Exception as e:
        print(f"❌ Lỗi khi cắt file: {e}")

def fix_delimiter():
    """Kiểm tra & sửa cấu trúc line|||text. Đảm bảo số line đúng với vị trí dòng, bù trừ nếu thiếu/sai delimiter"""
    filename = input("📁 Nhập tên file cần kiểm tra/sửa (mặc định: import.txt): ").strip()
    if not filename:
        filename = "import.txt"
        
    if not os.path.exists(filename):
        print(f"❌ File '{filename}' không tồn tại.")
        return

    out_filename = f"fixed_{filename}"
    fixed_count = 0
    
    with open(filename, 'r', encoding='utf-8') as in_f, open(out_filename, 'w', encoding='utf-8') as out_f:
        for line_num, line in enumerate(in_f, 1):
            raw = line.rstrip('\n\r')
            sep_idx = raw.find('|||')
            
            if sep_idx != -1:
                # Nếu có |||, lấy phần text phía sau
                text = raw[sep_idx+3:].strip()
            else:
                # Nếu mất |||, coi toàn bộ dòng là text
                text = raw.strip()
                fixed_count += 1
            
            # Ghi lại với định chuẩn: số_dòng_đúng|||text
            out_f.write(f"{line_num:06d}|||{text}\n")
            
    print(f"✅ Đã kiểm tra và sửa {fixed_count} dòng thiếu/sai DELIMITER.")
    print(f"💾 Kết quả đã lưu thành '{out_filename}' (File gốc vẫn được giữ nguyên).")

def main():
    print("⚠️ LƯU Ý: Nên sao lưu (backup) thư mục chứa file trước khi chạy các chức năng 2, 3, 4.")
    while True:
        print("\n" + "="*45)
        print("📦 MENU XỬ LÝ FILE TXT NHẬP LIỆU")
        print("="*45)
        print("1. Chuyển UTF-8-BOM ➔ UTF-8 (tất cả file .txt)")
        print("2. Gộp import_part*.txt ➔ import.txt (xóa file gốc)")
        print("3. Cắt file txt ➔ từng file 5000 dòng (import_part001...)")
        print("4. Kiểm tra & sửa lỗi DELIMITER '|||' + đánh số dòng")
        print("0. Thoát chương trình")
        print("="*45)
        
        choice = input("👉 Chọn chức năng (0-4): ").strip()
        
        if choice == '1':
            convert_utf8_bom()
        elif choice == '2':
            merge_files()
        elif choice == '3':
            split_file()
        elif choice == '4':
            fix_delimiter()
        elif choice == '0':
            print("👋 Thoát chương trình. Chúc bạn làm việc hiệu quả!")
            break
        else:
            print("❌ Lựa chọn không hợp lệ. Vui lòng nhập số từ 0 đến 4.")

if __name__ == "__main__":
    main()
