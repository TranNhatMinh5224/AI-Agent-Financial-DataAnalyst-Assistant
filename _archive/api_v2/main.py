import uuid
import asyncio
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from typing import List

from . import models, schemas
from .database import engine, get_db

# Tạo bảng DB
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Financial Analyst API (Production)", version="2.0")

# Cấu hình CORS cho Frontend Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "Backend is running", "version": "2.0"}

# --- WORKSPACE ROUTER ---

@app.post("/workspaces", response_model=schemas.Workspace)
def create_workspace(workspace: schemas.WorkspaceCreate, db: Session = Depends(get_db)):
    db_workspace = models.Workspace(
        id=f"ws_{uuid.uuid4().hex[:12]}",
        name=workspace.name
    )
    db.add(db_workspace)
    db.commit()
    db.refresh(db_workspace)
    return db_workspace

@app.get("/workspaces", response_model=List[schemas.Workspace])
def get_workspaces(db: Session = Depends(get_db)):
    return db.query(models.Workspace).all()

# --- UPLOAD & INGESTION ROUTER ---

from .core.storage import minio_client
from .core.ocr_worker import process_document_with_paddleocr

@app.post("/workspaces/{workspace_id}/upload", response_model=schemas.Document)
def upload_document(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    object_name = f"{workspace_id}/{doc_id}_{file.filename}"
    
    # Upload to MinIO
    try:
        minio_client.upload_file(file, object_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi upload lên MinIO: {str(e)}")
        
    db_doc = models.Document(
        id=doc_id,
        workspace_id=workspace_id,
        filename=file.filename,
        status="indexing"
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # Trigger background task cho PaddleOCR & Ingestion
    background_tasks.add_task(process_document_with_paddleocr, workspace_id, doc_id, object_name, db)
    
    return db_doc

# --- CHAT ROUTER (SSE STREAMING) ---

class ChatRequest(schemas.BaseModel):
    message: str

@app.post("/workspaces/{workspace_id}/chat/stream")
async def chat_stream(workspace_id: str, req: ChatRequest, db: Session = Depends(get_db)):
    """
    Stream response to frontend using SSE (Server-Sent Events)
    """
    workspace = db.query(models.Workspace).filter(models.Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    async def event_generator():
        # Simulated multi-agent streaming
        yield {"event": "status", "data": "Agent Planner đang phân tích yêu cầu..."}
        await asyncio.sleep(1)
        yield {"event": "status", "data": "Agent Retriever đang tìm kiếm dữ liệu trong Qdrant..."}
        await asyncio.sleep(1)
        yield {"event": "status", "data": "Agent Programmer đang sinh code Pandas..."}
        
        trace_data = {
            "code": "import pandas as pd\n\ndf = pd.read_csv('data.csv')\nans = df['Revenue'].sum()\nprint(ans)"
        }
        yield {"event": "trace", "data": str(trace_data)}
        
        await asyncio.sleep(2)
        
        final_answer = f"Dựa trên dữ liệu, câu trả lời cho '{req.message}' đã được tính toán."
        # Stream the tokens
        for word in final_answer.split():
            yield {"event": "message", "data": word + " "}
            await asyncio.sleep(0.1)
            
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_generator())
