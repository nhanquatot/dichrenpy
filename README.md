🎮 Tính năng chính:
Chế độ 1 - Xuất file dịch & mapping:

Lọc tất cả đoạn hội thoại từ file .rpy
Xuất 3 file:

file_dich.txt: Dạng số_dòng|||nội_dung (gốc chưa protect)
file_goc_protected.txt: Đã thay placeholder bằng @@id@@
mapping.json: Lưu mapping giữa @@id@@ và placeholder gốc



Chế độ 2 - Khôi phục placeholder:

Đọc file protected và mapping
Khôi phục tất cả placeholder về dạng ban đầu
Xuất file_dich_final.txt

Chế độ 3 - Gắn dịch vào RPY:

Đọc file dịch và file RPY gốc
Thay thế nội dung trong dấu "" bằng bản dịch
Xuất file .rpy mới với nội dung đã dịch

🛡️ Placeholder được bảo vệ:

Variables: {user_name}, [variable]
Escape sequences: \n, \t, \", \\
Format strings: %(name)s, %d, %s
Ren'Py tags: {color}, {size}, {b}, {i}, {font}, v.v.
Special tags: {w}, {p}, {nw}, {fast}, {slow}
Brackets: {{, }}, [lb], [rb]

📋 Cách sử dụng:

Lưu code vào file (ví dụ: renpy_processor.py)
Chạy script: python renpy_processor.py
Chọn chế độ và nhập thông tin file theo hướng dẫn

🎯 Ví dụ workflow:
bash# Bước 1: Xuất và bảo vệ
Chế độ 1 → Nhập: game.rpy
→ Xuất: game_dich.txt, game_goc_protected.txt, game_mapping.json

# Bước 2: Dịch file game_goc_protected.txt
(Dịch thủ công hoặc dùng tool khác)

# Bước 3: Khôi phục placeholder
Chế độ 2 → Nhập: game_goc_protected.txt (đã dịch), game_mapping.json
→ Xuất: game_dich_final.txt

# Bước 4: Gắn dịch vào RPY
Chế độ 3 → Nhập: game_dich_final.txt, game.rpy
→ Xuất: game_translated.rpy
✅ Điểm mạnh:

Xử lý đầy đủ UTF-8 và UTF-8-BOM
Bắt được nhiều loại dialog trong Ren'Py
Bảo vệ toàn diện các placeholder phổ biến
Giao diện console thân thiện
Xử lý lỗi và exception đầy đủ

Tool này sẽ giúp bạn dễ dàng quản lý quá trình dịch game Ren'Py một cách chuyên nghiệp và an toàn!
