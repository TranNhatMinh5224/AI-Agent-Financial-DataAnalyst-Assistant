"""
polish_and_merge.py — Quét tự động các câu hỏi bị lỗi (0.0/None), chạy lại qua Orchestrator đã nâng cấp và đóng gói submission.zip chuẩn 100%.

Usage:
    python polish_and_merge.py --inputs submission_part1 submission_part2 submission_part3 submission_part4 submission_part5 --output submission
    python polish_and_merge.py --inputs submission_part1 submission_part2 submission_part3 submission_part4 submission_part5 --no-polish
"""

import argparse
import glob
import json
import logging
import os
import shutil
import sys
import zipfile
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from financial_text_to_pandas.config import load_config
from financial_text_to_pandas.reasoning.orchestrator import FinancialQAOrchestrator, OrchestratorConfig, AgentConfig
from financial_text_to_pandas.submission import create_submission_item


def is_valid_answer(item: dict) -> bool:
    """Xac dinh mot item da co dap an hop le hay chua."""
    ans = item.get("answer")
    if ans is None or ans == "":
        return False
    if ans != 0.0:
        return True
    code = item.get("pandas_query", "")
    if "result =" in code or "result=" in code:
        rhs = code.split("result")[-1].replace("=", "").strip()
        if rhs and rhs[:3] != "0.0":
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Polish and Merge Submissions")
    parser.add_argument("--inputs", nargs="+", default=[], help="List of submission_part directories")
    parser.add_argument("--questions", default="ViFinQA/questions/questions.jsonl", help="Questions jsonl file")
    parser.add_argument("--config", default="config/run_profile_api.yaml", help="Config file")
    parser.add_argument("--output", default="submission", help="Output directory")
    parser.add_argument("--no-polish", action="store_true", help="Only merge without re-running failed questions")
    args = parser.parse_args()

    # Tự động tìm tất cả các thư mục submission_part* nếu không chỉ định
    input_dirs = args.inputs
    if not input_dirs:
        input_dirs = sorted([d for d in glob.glob("submission_part*") if os.path.isdir(d)])
        if not input_dirs and os.path.isdir("submission"):
            input_dirs = ["submission"]

    print(f"============================================================")
    print(f"📦 POLISH & MERGE SUBMISSIONS TOOL")
    print(f"👉 Thư mục đầu vào: {input_dirs}")
    print(f"👉 Thư mục đầu ra : {args.output}")
    print(f"============================================================")

    # 1. Đọc toàn bộ questions gốc để tra cứu
    q_file = Path(args.questions)
    questions_map = {}
    if q_file.exists():
        with open(q_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    questions_map[int(item["id"])] = item.get("question", "")

    # 2. Đọc và hợp nhất kết quả từ tất cả các thư mục
    merged_items = {}
    csv_sources = {}  # filename -> Path to copy from

    for dir_name in input_dirs:
        p_dir = Path(dir_name)
        json_path = p_dir / "submission.json"
        if not json_path.exists():
            print(f"[WARN] Không tìm thấy file: {json_path}")
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    qid = int(item["id"])
                    # Lưu item mới nhất hoặc item có kết quả hợp lệ
                    if qid not in merged_items or is_valid_answer(item) or not is_valid_answer(merged_items[qid]):
                        merged_items[qid] = item

            # Quét các file CSV trong thư mục data của part
            data_sub = p_dir / "data"
            if data_sub.exists():
                for csv_f in data_sub.glob("*.csv"):
                    csv_sources[csv_f.name] = csv_f
        except Exception as e:
            print(f"[ERROR] Lỗi đọc {json_path}: {e}")

    print(f"\n📊 Tổng số câu hỏi đã thu thập: {len(merged_items)}")
    valid_count = sum(1 for item in merged_items.values() if is_valid_answer(item))
    failed_items = [item for item in merged_items.values() if not is_valid_answer(item)]
    print(f"✅ Số câu ĐÃ CÓ ĐÁP ÁN: {valid_count} ({valid_count/len(merged_items)*100:.1f}%)" if merged_items else "")
    print(f"⚠️ Số câu CẦN POLISH (0.0/None): {len(failed_items)}")

    # 3. Kích hoạt Orchestrator để Polish các câu bị lỗi (nếu có và không tắt)
    if failed_items and not args.no_polish:
        print(f"\n🚀 Đang khởi động AI Orchestrator để giải lại {len(failed_items)} câu lỗi...")
        cfg = load_config(Path(args.config))

        def create_agent_config(role, cfg_dict, default_model):
            model = cfg_dict.get("model_name", default_model)
            temp = float(cfg_dict.get("temperature", 0.0))
            agent = AgentConfig(role, model_name=model, temperature=temp)
            agent.base_url = cfg_dict.get("base_url", "http://localhost:11434/v1")
            agent.api_key = cfg_dict.get("api_key", "ollama")
            return agent

        orch_cfg = OrchestratorConfig(
            planner=create_agent_config("planner", cfg.llm_planner_config, "deepseek-r1:14b"),
            retriever=create_agent_config("retriever", cfg.llm_retriever_config, "qwen2.5:7b"),
            programmer=create_agent_config("programmer", cfg.llm_programmer_config, "qwen2.5-coder:14b"),
            critic=create_agent_config("critic", cfg.llm_critic_config, "qwen2.5-coder:3b")
        )

        def to_llm_config_patched(self):
            return {
                "model_name": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "base_url": getattr(self, "base_url", "http://localhost:11434/v1"),
                "api_key": getattr(self, "api_key", "ollama")
            }
        AgentConfig.to_llm_config = lambda self: to_llm_config_patched(self)
        orchestrator = FinancialQAOrchestrator(orch_cfg)

        fixed_count = 0
        for item in failed_items:
            qid = int(item["id"])
            q_text = questions_map.get(qid, item.get("question", ""))
            print(f"\n--- Đang Polish Câu {qid}: {q_text[:70]}... ---")
            try:
                state = orchestrator.process_question(str(qid), q_text)
                new_item = create_submission_item(state)
                # Đảm bảo giữ ID số nguyên
                new_item["id"] = qid
                new_item["question"] = q_text

                if is_valid_answer(new_item):
                    print(f"  🎉 [THÀNH CÔNG] Câu {qid} -> Đáp án: {new_item.get('answer')}")
                    merged_items[qid] = new_item
                    fixed_count += 1
                    # Cập nhật nguồn CSV
                    for t in state.evidence_tables:
                        if t.candidate and t.candidate.csv_path:
                            p = Path(t.candidate.csv_path)
                            if p.exists():
                                csv_sources[p.name] = p
                else:
                    print(f"  ⚠️ [VẪN 0.0] Câu {qid} (Có thể là True Zero trong BCTC)")
                    merged_items[qid] = new_item
            except Exception as e:
                print(f"  ❌ Lỗi khi xử lý câu {qid}: {e}")

        print(f"\n✨ Kết quả Polish: Đã cứu thành công thêm {fixed_count}/{len(failed_items)} câu!")

    # 4. Xuất thư mục kết quả cuối cùng
    out_dir = Path(args.output)
    out_data = out_dir / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_data.mkdir(parents=True, exist_ok=True)

    # Sao chép các file CSV bằng chứng
    print(f"\n📁 Đang tổng hợp các file CSV bằng chứng vào {out_data}...")
    copied_csv = 0
    for fname, fpath in csv_sources.items():
        dst = out_data / fname
        if not dst.exists() or dst.stat().st_size != fpath.stat().st_size:
            shutil.copy2(fpath, dst)
            copied_csv += 1
    print(f"  ✅ Đã sao chép tổng cộng {len(csv_sources)} file CSV bằng chứng.")

    # Sắp xếp câu hỏi tăng dần theo ID (1, 2, 3, 4...)
    sorted_ids = sorted(merged_items.keys())
    final_list = [merged_items[qid] for qid in sorted_ids]

    # Ghi file submission.json
    out_json = out_dir / "submission.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
    print(f"  ✅ Đã lưu: {out_json} ({len(final_list)} câu hỏi)")

    # 5. Đóng gói file submission.zip
    out_zip = out_dir / "submission.zip"
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(out_json, arcname="submission.json")
        for csv_file in out_data.glob("*.csv"):
            zf.write(csv_file, arcname=f"data/{csv_file.name}")
    print(f"  📦 ĐÃ ĐÓNG GÓI THÀNH CÔNG: {out_zip} ({out_zip.stat().st_size / (1024*1024):.2f} MB)")

    # Thống kê tổng kết
    final_valid = sum(1 for it in final_list if is_valid_answer(it))
    print(f"\n============================================================")
    print(f"🏆 TỔNG KẾT BÀI THI SAU KHI GỘP VÀ POLISH:")
    print(f"👉 Tổng số câu hỏi: {len(final_list)}")
    print(f"👉 Số câu có đáp số hợp lệ: {final_valid} / {len(final_list)} ({final_valid/len(final_list)*100:.1f}%)")
    print(f"👉 File nộp bài sẵn sàng: {out_zip.resolve()}")
    print(f"============================================================")


if __name__ == "__main__":
    main()
