"""
server.py — FastAPI server exposing the system.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from financial_text_to_pandas.config import load_config
from financial_text_to_pandas.api.feedback import log_feedback, FeedbackRequest
from financial_text_to_pandas.reasoning.answer import run_reasoning_pipeline
from financial_text_to_pandas.types import Candidate, EvidenceTable
from financial_text_to_pandas.reasoning.intent import extract_intent

app = FastAPI(title="Financial Text-to-Pandas QA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
ui_dir = Path(__file__).parent.parent / "ui"
app.mount("/ui", StaticFiles(directory=ui_dir, html=True), name="ui")

# A simple in-memory storage for runs (in a real app this would be Redis/DB)
# The requirement says "The API reads artifacts. It does not introduce a database storage layer."
# We will just keep it in memory for the demo UI.
RUNS = {}

class QARequest(BaseModel):
    question: str
    
class QAResponse(BaseModel):
    run_id: str
    answer: float
    unit: Optional[str]
    verification_status: str
    error_type: Optional[str]
    trace: str
    code_generated: Optional[str]

@app.post("/qa/answer", response_model=QAResponse)
def qa_answer(req: QARequest):
    """Run the QA pipeline end-to-end."""
    cfg = load_config(Path("config/run_profile.yaml"))
    
    from financial_text_to_pandas.retrieval.search import run_search
    
    try:
        # Run Phase 2: Retrieval
        # We use mock_embeddings=True by default for quick demo unless specified otherwise,
        # but since Qwen is active, let's just use BM25 to be safe and fast if embeddings aren't generated.
        tables = run_search(req.question, cfg, method="bm25", top_k=5, no_reranker=True)
    except Exception as e:
        print(f"Retrieval Error: {e}")
        tables = []
        
    # Run Phase 3: Reasoning pipeline
    ans = run_reasoning_pipeline(req.question, tables, cfg.output_root, cfg.llm_config)
    
    run_id = str(uuid.uuid4())
    RUNS[run_id] = {
        "question": req.question,
        "answer": ans
    }
    
    return QAResponse(
        run_id=run_id,
        answer=ans.answer,
        unit=ans.unit,
        verification_status=ans.verification_status,
        error_type=ans.error_type,
        trace=ans.trace,
        code_generated=ans.code_generated
    )

@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    eval_root = Path("artifacts/evaluation")
    eval_root.mkdir(parents=True, exist_ok=True)
    log_feedback(eval_root, req)
    return {"status": "ok"}
    
@app.get("/")
def health_check():
    return {"status": "ok"}
