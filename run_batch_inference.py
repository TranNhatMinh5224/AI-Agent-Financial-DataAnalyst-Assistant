import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import argparse
import logging
import sys
from pathlib import Path
from tqdm import tqdm

# Đảm bảo UTF-8 encoding trên Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đảm bảo Python nhận diện được thư mục src
sys.path.append(str(Path(__file__).parent / "src"))

from financial_text_to_pandas.config import load_config
from financial_text_to_pandas.retrieval.search import run_search
from financial_text_to_pandas.reasoning.intent import extract_intent
from financial_text_to_pandas.types import EvidencePackage
from financial_text_to_pandas.reasoning.evidence import load_evidence_tables
from financial_text_to_pandas.reasoning.orchestrator import FinancialQAOrchestrator, OrchestratorConfig, AgentConfig
from financial_text_to_pandas.submission import create_submission_item

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/run_profile_api.yaml")
    parser.add_argument("--questions", default="ViFinQA/questions/questions.jsonl")
    parser.add_argument("--output", default="submission")
    parser.add_argument("--start", type=int, default=1, help="Start question number (1-indexed, e.g. --start 501)")
    parser.add_argument("--workers", type=int, default=1, help="Number of concurrent workers")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of questions to process (e.g. --limit 500)")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    questions_file = Path(args.questions)
    submission_dir = Path(args.output)
    data_dir = submission_dir / "data"

    submission_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Setup Logging (Đưa ra thư mục gốc để không bị Zip nhầm vào bài thi)
    log_file = Path("inference_log.txt")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logging.info(f"Started batch inference. Logs saved to {log_file}")

    # Initialize Orchestrator
    # We pass the model names from the new 4-config layout
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
    
    # Inject base_url into the to_llm_config dynamically so llm.py can pick it up
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

    # ── Smart Resume: chỉ skip câu đã có kết quả thực, chạy lại câu lỗi ──────
    output_json = submission_dir / "submission.json"
    results = []
    processed_ids = set()   # IDs câu đã THÀNH CÔNG → sẽ skip
    failed_ids   = set()    # IDs câu đã chạy nhưng LỖI  → sẽ chạy lại

    def _is_successful(item: dict) -> bool:
        """Câu được coi là thành công nếu có kết quả số hợp lệ khác 0.0,
        hoặc là 0.0 nhưng có code gán kết quả thực sự (result = ...)."""
        ans = item.get("answer")
        if ans is None or ans == "":
            return False
        if ans != 0.0:
            return True
        # Nếu là 0.0, kiểm tra xem có code gán biến result thực sự hay không
        code = item.get("pandas_query", "")
        return "result =" in code or "result=" in code

    if output_json.exists():
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                existing = json.load(f)

            for item in existing:
                qid = item["id"]
                if _is_successful(item):
                    processed_ids.add(qid)
                    results.append(item)   # Giữ lại kết quả tốt
                else:
                    failed_ids.add(qid)    # Sẽ chạy lại, KHÔNG đưa vào results

            logging.info(
                f"[INFO] Resume: {len(processed_ids)} câu OK (skip), "
                f"{len(failed_ids)} câu lỗi (chạy lại)."
            )
        except Exception as e:
            logging.warning(f"[WARN] Failed to read {output_json}: {e}. Starting fresh.")

    # Load questions
    questions = []
    with open(questions_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            questions.append(json.loads(line))

    # Determine start and limit (hỗ trợ chia việc chạy song song trên nhiều máy)
    start_idx = max(0, args.start - 1)
    questions = questions[start_idx:]

    limit = args.limit
    if limit == 0 and getattr(cfg, 'inference_limit_questions', None):
        limit = cfg.inference_limit_questions

    if limit and limit > 0:
        questions = questions[:limit]

    logging.info(f"[INFO] Total questions to process: {len(questions)}")

    file_lock = threading.Lock()
    
    def process_question(q):
        qid = q["id"]
        qtext = q["question"]

        if qid in processed_ids:
            return None, qid

        logging.info(f"--- Processing Question {qid} ---")
        try:
            try:
                tables = run_search(qtext, cfg, method="bm25", top_k=80, no_reranker=True)
            except Exception as e:
                logging.warning(f"Search failed: {e}")
                tables = []
                
            intent = extract_intent(qtext)
            package = EvidencePackage(
                query_id=str(qid), question=qtext, intent=intent, tables=tables, linked_text_context=[]
            )
            
            output_root_path = cfg.output_root
            if not output_root_path.is_absolute():
                output_root_path = Path.cwd() / output_root_path
                
            dfs = load_evidence_tables(package, output_root_path)
            trace = orchestrator.run(qtext, package, dfs, run_config=cfg, output_root=output_root_path)
            ans = trace.final_answer

            logging.info(trace.summary())

            evidence_tables = []
            table_refs = []
            report_ids = set()
            
            answer_val = ans.answer if (ans and ans.answer is not None) else None
            citations = ans.citations if ans and ans.citations else []
            code_gen = ans.code_generated if ans and ans.code_generated else ""

            if answer_val is None:
                reason = "Không rõ nguyên nhân"
                if ans:
                    if ans.error_type == "I_INSUFFICIENT_EVIDENCE":
                        reason = "Lỗi Tìm kiếm (Retriever)"
                    elif ans.error_type == "E_NUMERICAL_EXTRACTION":
                        reason = "Lỗi Grounding"
                    elif ans.error_type in ("T_TECHNICAL_ERROR", "C_CALCULATION_ERROR"):
                        reason = "Lỗi Sandbox"
                    elif getattr(ans, 'verification_status', '') == "invalid":
                        reason = "Lỗi Kiểm chứng (Critic)"
                logging.warning(f"⚠️ [CẢNH BÁO] Câu {qid} KHÔNG CÓ KẾT QUẢ! Nguyên nhân: {reason}")
                answer_val = 0.0

            for i, citation in enumerate(citations):
                var_name = f"df_{i}"
                report_id = citation.table_id
                csv_path_str = citation.csv_path
                if not Path(csv_path_str).is_absolute():
                    csv_path_full = output_root_path / csv_path_str
                else:
                    csv_path_full = Path(csv_path_str)
                    
                evidence_tables.append((var_name, report_id, csv_path_full.name))
                table_refs.append((report_id, 1))
                report_ids.add(report_id)

                if csv_path_full.is_file():
                    with file_lock:
                        import shutil
                        shutil.copy2(csv_path_full, data_dir / csv_path_full.name)

            item = create_submission_item(
                question_id=qid, question_text=qtext, answer=answer_val,
                report_ids=list(report_ids), table_refs=table_refs, evidence_tables=evidence_tables, pandas_query=code_gen
            )
            return item.to_dict(), qid

        except Exception as e:
            logging.error(f"[ERROR] Question {qid} failed catastrophically: {e}", exc_info=True)
            return None, qid

    if args.workers > 1:
        logging.info(f"Starting ThreadPoolExecutor with {args.workers} workers...")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_q = {executor.submit(process_question, q): q for q in questions}
            for future in tqdm(as_completed(future_to_q), total=len(questions), desc="Processing (Parallel)"):
                result, qid = future.result()
                if result:
                    with file_lock:
                        results.append(result)
                        temp_file = output_json.with_suffix(".tmp")
                        with open(temp_file, "w", encoding="utf-8") as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)
                        temp_file.replace(output_json)
                        processed_ids.add(qid)
    else:
        for q in tqdm(questions, desc="Processing (Sequential)"):
            result, qid = process_question(q)
            if result:
                results.append(result)
                temp_file = output_json.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                temp_file.replace(output_json)
                processed_ids.add(qid)

    # ── ĐÓNG GÓI VÀ BÁO THỨC ──
    logging.info(f"\n[SUCCESS] Tất cả câu hỏi đã xử lý xong. Đang nén file submission.zip...")
    try:
        from financial_text_to_pandas.submission import validate_submission_zip
        import zipfile
        
        zip_path = submission_dir.parent / "submission.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(output_json, "submission.json")
            for csv_file in data_dir.glob("*.csv"):
                zf.write(csv_file, f"data/{csv_file.name}")
        
        is_valid, errors = validate_submission_zip(zip_path)
        if is_valid:
            logging.info(f"✅ Gói nộp bài hợp lệ. File được lưu tại: {zip_path.absolute()}")
        else:
            logging.warning(f"⚠️ Gói nộp bài có lỗi format: {errors}")
            
        # Báo thức khi xong (Chỉ chạy trên Windows)
        import winsound
        winsound.Beep(1000, 500)  # Tần số 1000Hz, ngân 500ms
        winsound.Beep(1200, 500)
        winsound.Beep(1500, 1000)
    except Exception as e:
        logging.error(f"Lỗi khi đóng gói ZIP: {e}")

if __name__ == "__main__":
    main()
