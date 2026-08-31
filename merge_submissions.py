"""
merge_submissions.py — Ghép các kết quả chạy song song từ nhiều máy thành 1 submission.zip hoàn chỉnh.

Cách dùng:
    python merge_submissions.py --inputs submission_part1 submission_part2 --output submission
    
Script sẽ:
1. Đọc tất cả submission.json từ các thư mục input.
2. Hợp nhất kết quả theo question id (ưu tiên kết quả khác 0.0 nếu có trùng).
3. Sắp xếp danh sách câu hỏi theo thứ tự tăng dần (1, 2, 3, ... 1012).
4. Gom tất cả các file CSV bảng biểu từ các thư mục data/ vào submission/data/.
5. Tự động nén thành file submission.zip và kiểm tra format hợp lệ theo chuẩn ban tổ chức.
"""

import json
import shutil
import zipfile
import argparse
import sys
from pathlib import Path

# Đảm bảo UTF-8 trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from financial_text_to_pandas.submission import validate_submission_zip


def main():
    parser = argparse.ArgumentParser(description="Merge multiple partial submissions into one.")
    parser.add_argument(
        "--inputs", 
        nargs="+", 
        required=True, 
        help="Danh sách các thư mục kết quả cần gộp (ví dụ: --inputs submission_part1 submission_part2)"
    )
    parser.add_argument(
        "--output", 
        default="submission", 
        help="Thư mục xuất kết quả cuối cùng (mặc định: submission)"
    )
    parser.add_argument(
        "--zip-file", 
        default="submission.zip", 
        help="Tên file zip nén cuối cùng (mặc định: submission.zip)"
    )
    args = parser.parse_args()

    out_dir = Path(args.output)
    data_out_dir = out_dir / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    data_out_dir.mkdir(parents=True, exist_ok=True)

    merged_items = {}
    total_csv_copied = 0

    print("=" * 60)
    print("  BẮT ĐẦU GỘP CÁC PHẦN NỘP BÀI (SUBMISSION MERGER)")
    print("=" * 60)

    for inp_str in args.inputs:
        inp_dir = Path(inp_str)
        if not inp_dir.exists():
            print(f"⚠️ [BỎ QUA] Thư mục không tồn tại: {inp_dir}")
            continue

        json_path = inp_dir / "submission.json"
        if not json_path.exists():
            print(f"⚠️ [BỎ QUA] Không tìm thấy submission.json trong {inp_dir}")
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                items = json.load(f)
            print(f"📁 Đọc từ {inp_dir}: {len(items)} câu hỏi.")
        except Exception as e:
            print(f"❌ Lỗi đọc {json_path}: {e}")
            continue

        # Ghép items
        for item in items:
            qid = item["id"]
            if qid not in merged_items:
                merged_items[qid] = item
            else:
                # Nếu đã có, ưu tiên giữ kết quả có đáp án khác 0.0
                curr_ans = merged_items[qid].get("answer")
                new_ans = item.get("answer")
                if curr_ans in (0.0, None, "") and new_ans not in (0.0, None, ""):
                    merged_items[qid] = item

        # Copy các file CSV trong data/
        inp_data = inp_dir / "data"
        if inp_data.exists():
            for csv_file in inp_data.glob("*.csv"):
                dest = data_out_dir / csv_file.name
                if not dest.exists():
                    shutil.copy2(csv_file, dest)
                    total_csv_copied += 1

    if not merged_items:
        print("❌ Không có câu hỏi nào được gộp!")
        return

    # Sắp xếp câu hỏi theo thứ tự ID tăng dần
    sorted_items = sorted(merged_items.values(), key=lambda x: int(x["id"]))

    out_json = out_dir / "submission.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(sorted_items, f, ensure_ascii=False, indent=2)

    print("-" * 60)
    valid_count = sum(1 for x in sorted_items if x.get("answer") not in (0.0, None, ""))
    print(f"✅ Đã gộp thành công:")
    print(f"   - Tổng số câu hỏi: {len(sorted_items)}")
    print(f"   - Số câu có đáp án hợp lệ: {valid_count} ({valid_count/len(sorted_items)*100:.1f}%)")
    print(f"   - Tổng số file CSV bảng biểu: {len(list(data_out_dir.glob('*.csv')))}")
    print(f"   - File JSON đã lưu: {out_json.absolute()}")

    # Đóng gói zip
    zip_path = Path(args.zip_file)
    print(f"📦 Đang nén file {zip_path.name}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(out_json, "submission.json")
        for csv_file in data_out_dir.glob("*.csv"):
            zf.write(csv_file, f"data/{csv_file.name}")

    is_valid, errors = validate_submission_zip(zip_path)
    if is_valid:
        print(f"🎉 HOÀN THÀNH! Gói nộp bài hợp lệ: {zip_path.absolute()}")
    else:
        print(f"⚠️ Cảnh báo kiểm tra định dạng gói nộp bài: {errors}")
    print("=" * 60)


if __name__ == "__main__":
    main()
