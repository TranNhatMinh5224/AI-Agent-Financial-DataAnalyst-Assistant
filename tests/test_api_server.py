"""
tests/test_api_server.py — Tests for the FastAPI server.
"""

from fastapi.testclient import TestClient
from financial_text_to_pandas.api.server import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_qa_answer_endpoint():
    response = client.post("/qa/answer", json={"question": "Tài sản AAA năm 2023"})
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "answer" in data
    assert "verification_status" in data

def test_feedback_endpoint():
    payload = {
        "run_id": "test-123",
        "question": "test",
        "answer": 10.0,
        "retrieved_table_ids": [],
        "grounded_cells_json": "[]",
        "selected_cells_json": "[]",
        "reasoning_strategy": "test",
        "verifier_status": "valid",
        "user_rating": "up",
        "user_comment": "good",
        "error_type": None
    }
    response = client.post("/feedback", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
