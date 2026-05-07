import os


class BatchRenamer:
    """Công cụ đổi tên hàng loạt file và thư mục.
    Thuật toán xử lý bottom-up (từ thư mục con sâu nhất lên thư mục mẹ)
    để tránh lỗi đường dẫn khi đổi tên."""

    def __init__(self, root_dir):
        self.root_dir = os.path.abspath(root_dir)
        self.stats = {"renamed": 0, "skipped": 0, "errors": 0}

    def reset_stats(self):
        self.stats = {"renamed": 0, "skipped": 0, "errors": 0}

    # ──────────────────────────────────────────────
    #  THU THẬP DỮ LIỆU (BOTTOM-UP)
    # ──────────────────────────────────────────────

    def get_files_bottom_up(self):
        """Thu thập tất cả file, từ thư mục con sâu nhất lên."""
        result = []
        for dirpath, _, filenames in os.walk(self.root_dir, topdown=False):
            for f in filenames:
                result.append(os.path.join(dirpath, f))
        return result

    def get_dirs_bottom_up(self):
        """Thu thập tất cả thư mục con (không bao gồm root), từ sâu nhất lên."""
        result = []
        for dirpath, dirnames, _ in os.walk(self.root_dir, topdown=False):
            for d in dirnames:
                result.append(os.path.join(dirpath, d))
        return result

    # ──────────────────────────────────────────────
    #  XEM TRƯỚC & XÁC NHẬN
    # ──────────────────────────────────────────────

    def preview_and_confirm(self, changes):
        if not changes:
            print("\nKhông có mục nào cần đổi tên.")
            return False

        print(f"\nXem trước ({len(changes)} mục):")
        print("-" * 60)
        for old_path, new_path in changes:
            old_name = os.path.basename(old_path)
            new_name = os.path.basename(new_path)
            # Hiển thị đường dẫn tương đối cho dễ đọc
            rel_old = os.path.relpath(old_path, self.root_dir)
            rel_new = os.path.relpath(new_path, self.root_dir)
            print(f"  {rel_old}")
            print(f"    -> {rel_new}")
        print("-" * 60)

        confirm = input(f"\nXác nhận đổi tên {len(changes)} mục? (y/n): ").strip().lower()
        return confirm == "y"

    def execute_renames(self, changes):
        self.reset_stats()
        for old_path, new_path in changes:
            old_name = os.path.basename(old_path)
            new_name = os.path.basename(new_path)
            try:
                if os.path.exists(new_path):
                    print(f"  [Bỏ qua] '{new_name}' đã tồn tại")
                    self.stats["skipped"] += 1
                    continue
                os.rename(old_path, new_path)
                print(f"  [OK] {old_name} -> {new_name}")
                self.stats["renamed"] += 1
            except Exception as e:
                print(f"  [Lỗi] {old_name}: {e}")
                self.stats["errors"] += 1

        s = self.stats
        print(f"\nKết quả: {s['renamed']} thành công | "
              f"{s['skipped']} bỏ qua | {s['errors']} lỗi")

    # ──────────────────────────────────────────────
    #  FILE - THÊM / XÓA TIỀN TỐ
    # ──────────────────────────────────────────────

    def add_prefix_files(self, prefix):
        if not prefix:
            print("Tiền tố không được để trống.")
            return
        files = self.get_files_bottom_up()
        if not files:
            print("Không tìm thấy file nào.")
            return

        changes = []
        for f in files:
            d = os.path.dirname(f)
            name = os.path.basename(f)
            new_name = prefix + name
            changes.append((f, os.path.join(d, new_name)))

        if self.preview_and_confirm(changes):
            self.execute_renames(changes)

    def remove_prefix_files(self, prefix):
        if not prefix:
            print("Tiền tố không được để trống.")
            return
        files = self.get_files_bottom_up()
        if not files:
            print("Không tìm thấy file nào.")
            return

        changes = []
        for f in files:
            d = os.path.dirname(f)
            name = os.path.basename(f)
            if name.startswith(prefix):
                new_name = name[len(prefix):]
                if new_name:
                    changes.append((f, os.path.join(d, new_name)))

        if self.preview_and_confirm(changes):
            self.execute_renames(changes)

    # ──────────────────────────────────────────────
    #  FILE - THÊM / XÓA HẬU TỐ
    # ──────────────────────────────────────────────

    def add_suffix_files(self, suffix):
        if not suffix:
            print("Hậu tố không được để trống.")
            return
        files = self.get_files_bottom_up()
        if not files:
            print("Không tìm thấy file nào.")
            return

        changes = []
        for f in files:
            d = os.path.dirname(f)
            name = os.path.basename(f)
            base, ext = os.path.splitext(name)
            new_name = base + suffix + ext
            changes.append((f, os.path.join(d, new_name)))

        if self.preview_and_confirm(changes):
            self.execute_renames(changes)

    def remove_suffix_files(self, suffix):
        if not suffix:
            print("Hậu tố không được để trống.")
            return
        files = self.get_files_bottom_up()
        if not files:
            print("Không tìm thấy file nào.")
            return

        changes = []
        for f in files:
            d = os.path.dirname(f)
            name = os.path.basename(f)
            base, ext = os.path.splitext(name)
            if base.endswith(suffix):
                new_base = base[:-len(suffix)]
                if new_base:
                    new_name = new_base + ext
                    changes.append((f, os.path.join(d, new_name)))

        if self.preview_and_confirm(changes):
            self.execute_renames(changes)

    # ──────────────────────────────────────────────
    #  THƯ MỤC - THÊM / XÓA TIỀN TỐ
    # ──────────────────────────────────────────────

    def add_prefix_dirs(self, prefix):
        if not prefix:
            print("Tiền tố không được để trống.")
            return
        dirs = self.get_dirs_bottom_up()
        if not dirs:
            print("Không tìm thấy thư mục con nào.")
            return

        changes = []
        for d_path in dirs:
            parent = os.path.dirname(d_path)
            name = os.path.basename(d_path)
            new_name = prefix + name
            changes.append((d_path, os.path.join(parent, new_name)))

        if self.preview_and_confirm(changes):
            self.execute_renames(changes)

    def remove_prefix_dirs(self, prefix):
        if not prefix:
            print("Tiền tố không được để trống.")
            return
        dirs = self.get_dirs_bottom_up()
        if not dirs:
            print("Không tìm thấy thư mục con nào.")
            return

        changes = []
        for d_path in dirs:
            parent = os.path.dirname(d_path)
            name = os.path.basename(d_path)
            if name.startswith(prefix):
                new_name = name[len(prefix):]
                if new_name:
                    changes.append((d_path, os.path.join(parent, new_name)))

        if self.preview_and_confirm(changes):
            self.execute_renames(changes)

    # ──────────────────────────────────────────────
    #  THƯ MỤC - THÊM / XÓA HẬU TỐ
    # ──────────────────────────────────────────────

    def add_suffix_dirs(self, suffix):
        if not suffix:
            print("Hậu tố không được để trống.")
            return
        dirs = self.get_dirs_bottom_up()
        if not dirs:
            print("Không tìm thấy thư mục con nào.")
            return

        changes = []
        for d_path in dirs:
            parent = os.path.dirname(d_path)
            name = os.path.basename(d_path)
            new_name = name + suffix
            changes.append((d_path, os.path.join(parent, new_name)))

        if self.preview_and_confirm(changes):
            self.execute_renames(changes)

    def remove_suffix_dirs(self, suffix):
        if not suffix:
            print("Hậu tố không được để trống.")
            return
        dirs = self.get_dirs_bottom_up()
        if not dirs:
            print("Không tìm thấy thư mục con nào.")
            return

        changes = []
        for d_path in dirs:
            parent = os.path.dirname(d_path)
            name = os.path.basename(d_path)
            if name.endswith(suffix):
                new_name = name[:-len(suffix)]
                if new_name:
                    changes.append((d_path, os.path.join(parent, new_name)))

        if self.preview_and_confirm(changes):
            self.execute_renames(changes)


# ══════════════════════════════════════════════════
#  MENU CHÍNH
# ══════════════════════════════════════════════════

def print_menu():
    print("\n" + "=" * 55)
    print("   CÔNG CỤ ĐỔI TÊN HÀNG LOẠT FILE & THƯ MỤC")
    print("=" * 55)
    print("  ┌─ FILE ──────────────────────────────────────┐")
    print("  │  1. Thêm tiền tố vào tên file               │")
    print("  │  2. Xóa tiền tố khỏi tên file               │")
    print("  │  3. Thêm hậu tố vào tên file                │")
    print("  │  4. Xóa hậu tố khỏi tên file                │")
    print("  ├─ THƯ MỤC ──────────────────────────────────┤")
    print("  │  5. Thêm tiền tố vào tên thư mục            │")
    print("  │  6. Xóa tiền tố khỏi tên thư mục            │")
    print("  │  7. Thêm hậu tố vào tên thư mục             │")
    print("  │  8. Xóa hậu tố khỏi tên thư mục             │")
    print("  ├─────────────────────────────────────────────┤")
    print("  │  9. Đổi thư mục làm việc                    │")
    print("  │  0. Thoát                                   │")
    print("  └─────────────────────────────────────────────┘")
    print("=" * 55)


def input_path():
    while True:
        target = input("\nNhập đường dẫn thư mục: ").strip().strip('"')
        if not target:
            print("Đường dẫn không được để trống.")
            continue
        if not os.path.isdir(target):
            print(f"'{target}' không phải thư mục hợp lệ. Thử lại.")
            continue
        return target


def main():
    print("\n" + "=" * 55)
    print("   CÔNG CỤ ĐỔI TÊN HÀNG LOẠT FILE & THƯ MỤC")
    print("   Thuật toán: Bottom-up (con -> mẹ)")
    print("=" * 55)

    target = input_path()
    renamer = BatchRenamer(target)

    while True:
        print_menu()
        choice = input("  Chọn chức năng (0-9): ").strip()

        if choice == "1":
            prefix = input("  Nhập tiền tố cần thêm: ")
            renamer.add_prefix_files(prefix)
        elif choice == "2":
            prefix = input("  Nhập tiền tố cần xóa: ")
            renamer.remove_prefix_files(prefix)
        elif choice == "3":
            suffix = input("  Nhập hậu tố cần thêm: ")
            renamer.add_suffix_files(suffix)
        elif choice == "4":
            suffix = input("  Nhập hậu tố cần xóa: ")
            renamer.remove_suffix_files(suffix)
        elif choice == "5":
            prefix = input("  Nhập tiền tố cần thêm: ")
            renamer.add_prefix_dirs(prefix)
        elif choice == "6":
            prefix = input("  Nhập tiền tố cần xóa: ")
            renamer.remove_prefix_dirs(prefix)
        elif choice == "7":
            suffix = input("  Nhập hậu tố cần thêm: ")
            renamer.add_suffix_dirs(suffix)
        elif choice == "8":
            suffix = input("  Nhập hậu tố cần xóa: ")
            renamer.remove_suffix_dirs(suffix)
        elif choice == "9":
            target = input_path()
            renamer = BatchRenamer(target)
            print(f"\nĐã chuyển sang: {target}")
        elif choice == "0":
            print("\nTạm biệt!")
            break
        else:
            print("  Lựa chọn không hợp lệ. Chọn từ 0-9.")


if __name__ == "__main__":
    main()
