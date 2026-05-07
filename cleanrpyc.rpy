import os
import glob

def scan_and_delete_rpyc(root_dir):
    """Quét và xóa tất cả file .rpyc từ thư mục gốc trở xuống."""
    pattern = os.path.join(root_dir, "**", "*.rpyc")
    rpyc_files = glob.glob(pattern, recursive=True)

    if not rpyc_files:
        print(f"\nKhông tìm thấy file .rpyc nào trong '{os.path.abspath(root_dir)}'.")
        return

    print(f"\nTìm thấy {len(rpyc_files)} file .rpyc trong '{os.path.abspath(root_dir)}':\n")

    for filepath in rpyc_files:
        print(f"  {filepath}")

    confirm = input(f"\nBạn có chắc muốn xóa {len(rpyc_files)} file? (y/n): ").strip().lower()
    if confirm != "y":
        print("Đã hủy.")
        return

    deleted = 0
    failed = 0

    for filepath in rpyc_files:
        try:
            os.remove(filepath)
            print(f"  [Đã xóa] {filepath}")
            deleted += 1
        except PermissionError:
            print(f"  [Lỗi quyền] {filepath}")
            failed += 1
        except OSError as e:
            print(f"  [Lỗi] {filepath} — {e}")
            failed += 1

    print(f"\nKết quả: {deleted} đã xóa, {failed} lỗi.")


if __name__ == "__main__":
    print("=" * 50)
    print("  Công cụ xóa file .rpyc")
    print("=" * 50)

    while True:
        target = input("\nNhập đường dẫn thư mục: ").strip().strip('"')

        if not target:
            print("Đường dẫn không được để trống.")
            continue

        if not os.path.isdir(target):
            print(f"'{target}' không phải thư mục hợp lệ. Hãy thử lại.")
            continue

        break

    scan_and_delete_rpyc(target)
