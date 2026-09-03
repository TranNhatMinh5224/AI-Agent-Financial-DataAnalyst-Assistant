from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class WorkspaceBase(BaseModel):
    name: str

class WorkspaceCreate(WorkspaceBase):
    pass

class Workspace(WorkspaceBase):
    id: str
    created_at: datetime
    config_data: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True

class DocumentBase(BaseModel):
    filename: str

class Document(DocumentBase):
    id: str
    workspace_id: str
    status: str
    uploaded_at: datetime

    class Config:
        orm_mode = True

class ChatMessage(BaseModel):
    role: str
    content: str
    trace_data: Optional[Dict[str, Any]] = None

class ChatSessionBase(BaseModel):
    workspace_id: str

class ChatSession(ChatSessionBase):
    id: str
    created_at: datetime
    messages: List[ChatMessage] = []

    class Config:
        orm_mode = True
