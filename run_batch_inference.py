import json
import shutil
import argparse
from pathlib import Path
from tqdm import tqdm

from financial_text_to_pandas.config import load_config
from financial_text_to_pandas.retrieval.search import run_search
from financial_text_to_pandas.reasoning.intent import extract_intent
from financial_text_to_pandas.types import EvidencePackage
from financial_text_to_pandas.reasoning.evidence import load_evidence_tables
from financial_text_to_pandas.reasoning.orchestrator import FinancialQAOrchestrator, OrchestratorConfig, AgentConfig
from financial_text_to_pandas.submission import create_submission_item

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/run_profile.yaml")
    parser.add_argument("--questions", default="ViFinQA/questions/questions.jsonl")
    parser.add_argument("--output", default="submission")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of questions to process")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    questions_file = Path(args.questions)
    submission_dir = Path(args.output)
    data_dir = submission_dir / "data"

    submission_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

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

    # Checkpoint logic
    output_json = submission_dir / "submission.json"
    results = []
    processed_ids = set()

    if output_json.exists():
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                results = json.load(f)
            processed_ids = {item["id"] for item in results}
            print(f"[INFO] Resuming. Found {len(processed_ids)} already processed questions.")
        except Exception as e:
            print(f"[WARN] Failed to read {output_json}: {e}. Starting fresh.")

    # Load questions
    questions = []
    with open(questions_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            questions.append(json.loads(line))

    if args.limit > 0:
        questions = questions[:args.limit]

    print(f"[INFO] Total questions to process: {len(questions)}")

    for q in tqdm(questions, desc="Processing"):
        qid = q["id"]
        qtext = q["question"]

        if qid in processed_ids:
            continue

        try:
            # 1. Search (BM25 or Hybrid)
            # using BM25 by default here for speed, or hybrid if embedding is ready
            # Fallback to bm25 if hybrid fails
            try:
                tables = run_search(qtext, cfg, method="hybrid", top_k=5)
            except Exception as e:
                tables = run_search(qtext, cfg, method="bm25", top_k=5, no_reranker=True)
                
            # 2. Extract Intent
            intent = extract_intent(qtext)

            # 3. Create Package & Load DataFrames
            package = EvidencePackage(
                query_id=str(qid),
                question=qtext,
                intent=intent,
                tables=tables,
                linked_text_context=[] # Can be populated via BM25 against a text corpus if available
            )
            
            output_root = cfg.output_root
            if not output_root.is_absolute():
                output_root = Path.cwd() / output_root
                
            dfs = load_evidence_tables(package, output_root)

            # 4. Orchestrate
            trace = orchestrator.run(qtext, package, dfs)
            ans = trace.final_answer

            # Prepare fields for SubmissionItem
            evidence_tables = []
            table_refs = []
            report_ids = set()
            
            answer_val = ans.answer if ans and ans.answer is not None else 0.0
            citations = ans.citations if ans and ans.citations else []
            code_gen = ans.code_generated if ans and ans.code_generated else ""

            for i, citation in enumerate(citations):
                var_name = f"df_{i}"
                report_id = citation.table_id
                
                # Make sure csv_path is resolved correctly
                csv_path_str = citation.csv_path
                # Check if it starts with output_root
                if not Path(csv_path_str).is_absolute():
                    csv_path_full = output_root / csv_path_str
                else:
                    csv_path_full = Path(csv_path_str)
                    
                evidence_tables.append((var_name, report_id, csv_path_full.name))
                table_refs.append((report_id, 1)) # Simplified to 1
                report_ids.add(report_id)

                # Copy to submission/data/
                if csv_path_full.exists():
                    shutil.copy2(csv_path_full, data_dir / csv_path_full.name)

            # 5. Build SubmissionItem
            item = create_submission_item(
                question_id=qid,
                question_text=qtext,
                answer=answer_val,
                report_ids=list(report_ids),
                table_refs=table_refs,
                evidence_tables=evidence_tables,
                pandas_query=code_gen
            )

            results.append(item.to_dict())

            # Save incrementally
            with open(output_json, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            processed_ids.add(qid)

        except Exception as e:
            print(f"\n[ERROR] Question {qid} failed: {e}")

    print(f"\n[SUCCESS] Submission files generated at: {submission_dir.absolute()}")

if __name__ == "__main__":
    main()
