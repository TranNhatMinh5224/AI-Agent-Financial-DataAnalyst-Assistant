"""
feedback.py — Append-only feedback logger.
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

class FeedbackRequest(BaseModel):
    run_id: str
    question: str
    answer: float
    retrieved_table_ids: List[str]
    grounded_cells_json: str
    selected_cells_json: str
    reasoning_strategy: str
    verifier_status: str
    user_rating: str
    user_comment: str
    error_type: Optional[str]

def log_feedback(eval_root: Path, feedback: FeedbackRequest):
    """Append feedback to the log."""
    log_path = eval_root / "feedback_log.jsonl"
    
    entry = feedback.model_dump()
    entry["created_at"] = datetime.now().isoformat()
    
    with open(log_path, mode="a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
