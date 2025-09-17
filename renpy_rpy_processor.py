#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ren'Py RPY File Processor
Công cụ xử lý file RPY với 3 chế độ:
1. Xuất file dịch & mapping
2. Khôi phục placeholder
3. Gắn dịch trở lại file RPY
"""

import re
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class RenpyProcessor:
    def __init__(self):
        # Regex patterns để tìm dialog trong Ren'Py
        self.dialog_patterns = [
            # Character dialog: character "text"
            re.compile(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s+"(.+)"', re.MULTILINE),
            # Narrator dialog: "text"
            re.compile(r'^(\s*)"(.+)"', re.MULTILINE),
            # Say with expression: character "text" with dissolve
            re.compile(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s+"(.+)"\s+with\s+', re.MULTILINE),
            # Menu choices: "choice text"
            re.compile(r'^(\s*)menu:\s*\n(?:.*\n)*?(\s+)"(.+)":', re.MULTILINE),
        ]
        
        # Pattern cho placeholder - mở rộng để bắt nhiều loại placeholder
        self.placeholder_pattern = re.compile(
            r'(\[.*?\]|\{.*?\}|\\[nt"\\%\']|%\([^)]+\)|%[sdif]|\\u[0-9a-fA-F]{4}|' +
            r'\{color[^}]*\}|\{/color\}|\{size[^}]*\}|\{/size\}|\{b\}|\{/b\}|\{i\}|\{/i\}|' +
            r'\{font[^}]*\}|\{/font\}|\{a[^}]*\}|\{/a\}|\{img[^}]*\}|\{space[^}]*\}|' +
            r'\{w[^}]*\}|\{p[^}]*\}|\{nw\}|\{fast\}|\{slow\}|\{done\}|\{clear\}|' +
            r'\{\{|\}\}|\[lb\]|\[rb\])'
        )
        
        self.placeholder_counter = 0
        self.placeholder_mapping = {}
        
    def extract_dialogs(self, content: str) -> List[Tuple[int, str, str]]:
        """
        Lọc tất cả đoạn hội thoại từ nội dung file RPY
        Returns: List of (line_number, original_text, full_line)
        """
        dialogs = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Bỏ qua comment và dòng trống
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
                
            # Kiểm tra character dialog: character "text"
            match = re.match(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s+"(.+?)"', line)
            if match:
                text = match.group(3)
                dialogs.append((i, text, line))
                continue
                
            # Kiểm tra narrator dialog: "text"
            match = re.match(r'^(\s*)"(.+?)"', line)
            if match:
                text = match.group(2)
                dialogs.append((i, text, line))
                continue
                
            # Kiểm tra menu choice
            if '"' in line and ':' in line:
                match = re.search(r'"(.+?)":', line)
                if match:
                    text = match.group(1)
                    # Chỉ lấy nếu đây có thể là menu choice
                    if line.strip().startswith('"') or (len(line) - len(line.lstrip()) >= 4):
                        dialogs.append((i, text, line))
                        continue
        
        return dialogs
    
    def protect_placeholders(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Thay thế placeholder bằng mã @@id@@
        Returns: (protected_text, mapping)
        """
        protected = text
        local_mapping = {}
        
        def replace_placeholder(match):
            placeholder = match.group(0)
            # Kiểm tra xem placeholder này đã có trong mapping chưa
            for key, value in self.placeholder_mapping.items():
                if value == placeholder:
                    return key
            
            # Tạo key mới
            self.placeholder_counter += 1
            key = f"@@{self.placeholder_counter}@@"
            self.placeholder_mapping[key] = placeholder
            local_mapping[key] = placeholder
            return key
        
        protected = self.placeholder_pattern.sub(replace_placeholder, protected)
        return protected, local_mapping
    
    def mode1_extract_and_protect(self, input_file: str, output_dir: str = '.'):
        """
        Chế độ 1: Xuất file dịch & mapping
        """
        print(f"Chế độ 1: Xử lý file {input_file}")
        
        # Đọc file với UTF-8
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Thử với UTF-8-sig nếu có BOM
            with open(input_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        
        # Reset counter và mapping cho mỗi file mới
        self.placeholder_counter = 0
        self.placeholder_mapping = {}
        
        # Lọc dialog
        dialogs = self.extract_dialogs(content)
        print(f"Tìm thấy {len(dialogs)} đoạn hội thoại")
        
        # Chuẩn bị output
        base_name = Path(input_file).stem
        file_dich_path = os.path.join(output_dir, f"{base_name}_dich.txt")
        file_protected_path = os.path.join(output_dir, f"{base_name}_goc_protected.txt")
        mapping_path = os.path.join(output_dir, f"{base_name}_mapping.json")
        
        # Xuất file_dich.txt và file_goc_protected.txt
        with open(file_dich_path, 'w', encoding='utf-8') as f_dich, \
             open(file_protected_path, 'w', encoding='utf-8') as f_protected:
            
            for line_num, text, full_line in dialogs:
                # Ghi file dịch gốc (chưa protect)
                f_dich.write(f"{line_num}|||{text}\n")
                
                # Protect placeholder và ghi file protected
                protected_text, _ = self.protect_placeholders(text)
                f_protected.write(f"{line_num}|||{protected_text}\n")
        
        # Xuất mapping.json
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(self.placeholder_mapping, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Xuất thành công:")
        print(f"  - {file_dich_path}")
        print(f"  - {file_protected_path}")
        print(f"  - {mapping_path}")
        print(f"  - Tổng số placeholder: {len(self.placeholder_mapping)}")
    
    def mode2_restore_placeholders(self, protected_file: str, mapping_file: str, output_dir: str = '.'):
        """
        Chế độ 2: Khôi phục placeholder
        """
        print(f"Chế độ 2: Khôi phục placeholder")
        
        # Đọc mapping
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        # Đọc file protected
        with open(protected_file, 'r', encoding='utf-8') as f:
            protected_content = f.read()
        
        # Khôi phục placeholder
        restored_content = protected_content
        for key, value in mapping.items():
            restored_content = restored_content.replace(key, value)
        
        # Xuất file
        base_name = Path(protected_file).stem.replace('_goc_protected', '')
        output_file = os.path.join(output_dir, f"{base_name}_dich_final.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(restored_content)
        
        print(f"✅ Khôi phục thành công: {output_file}")
    
    def mode3_apply_translation(self, translation_file: str, original_rpy: str, output_dir: str = '.'):
        """
        Chế độ 3: Gắn dịch trở lại file RPY
        """
        print(f"Chế độ 3: Gắn dịch vào file RPY")
        
        # Đọc file dịch
        translations = {}
        with open(translation_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '|||' in line:
                    parts = line.strip().split('|||', 1)
                    if len(parts) == 2:
                        line_num = int(parts[0])
                        translation = parts[1]
                        translations[line_num] = translation
        
        # Đọc file RPY gốc
        try:
            with open(original_rpy, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(original_rpy, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
        
        # Thay thế dịch
        for line_num, translation in translations.items():
            if 0 < line_num <= len(lines):
                line = lines[line_num - 1]
                
                # Tìm và thay thế text trong dấu ngoặc kép
                # Character dialog
                match = re.match(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*\s+)"(.+?)"(.*)$', line)
                if match:
                    lines[line_num - 1] = f'{match.group(1)}{match.group(2)}"{translation}"{match.group(4)}\n'
                    continue
                
                # Narrator dialog
                match = re.match(r'^(\s*)"(.+?)"(.*)$', line)
                if match:
                    lines[line_num - 1] = f'{match.group(1)}"{translation}"{match.group(3)}\n'
                    continue
                
                # Menu choice
                if '"' in line and ':' in line:
                    line = re.sub(r'"(.+?)":', f'"{translation}":', line, 1)
                    lines[line_num - 1] = line
        
        # Xuất file mới
        base_name = Path(original_rpy).stem
        output_file = os.path.join(output_dir, f"{base_name}_translated.rpy")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"✅ Gắn dịch thành công: {output_file}")
        print(f"  - Tổng số dòng đã dịch: {len(translations)}")

def main():
    processor = RenpyProcessor()
    
    print("=" * 60)
    print("REN'PY RPY FILE PROCESSOR")
    print("=" * 60)
    print("\nChọn chế độ:")
    print("1. Xuất file dịch & mapping")
    print("2. Khôi phục placeholder")
    print("3. Gắn dịch trở lại file RPY")
    print("-" * 40)
    
    try:
        mode = input("\nNhập số chế độ (1/2/3): ").strip()
        
        if mode == '1':
            input_file = input("Nhập đường dẫn file .rpy gốc: ").strip()
            if not os.path.exists(input_file):
                print(f"❌ Lỗi: File {input_file} không tồn tại!")
                return
            
            output_dir = input("Nhập thư mục output (Enter = thư mục hiện tại): ").strip() or '.'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            processor.mode1_extract_and_protect(input_file, output_dir)
            
        elif mode == '2':
            protected_file = input("Nhập đường dẫn file _goc_protected.txt: ").strip()
            mapping_file = input("Nhập đường dẫn file _mapping.json: ").strip()
            
            if not os.path.exists(protected_file):
                print(f"❌ Lỗi: File {protected_file} không tồn tại!")
                return
            if not os.path.exists(mapping_file):
                print(f"❌ Lỗi: File {mapping_file} không tồn tại!")
                return
            
            output_dir = input("Nhập thư mục output (Enter = thư mục hiện tại): ").strip() or '.'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            processor.mode2_restore_placeholders(protected_file, mapping_file, output_dir)
            
        elif mode == '3':
            translation_file = input("Nhập đường dẫn file _dich_final.txt: ").strip()
            original_rpy = input("Nhập đường dẫn file .rpy gốc: ").strip()
            
            if not os.path.exists(translation_file):
                print(f"❌ Lỗi: File {translation_file} không tồn tại!")
                return
            if not os.path.exists(original_rpy):
                print(f"❌ Lỗi: File {original_rpy} không tồn tại!")
                return
            
            output_dir = input("Nhập thư mục output (Enter = thư mục hiện tại): ").strip() or '.'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            processor.mode3_apply_translation(translation_file, original_rpy, output_dir)
            
        else:
            print("❌ Lựa chọn không hợp lệ!")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Đã hủy bởi người dùng")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
