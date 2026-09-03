import os
import json
import uuid
import datetime
from pathlib import Path

# Thư mục gốc chứa toàn bộ Workspaces
WORKSPACES_ROOT = Path(os.getcwd()) / "data_workspaces"

def get_workspaces():
    if not WORKSPACES_ROOT.exists():
        WORKSPACES_ROOT.mkdir(parents=True)
        return []
        
    workspaces = []
    for d in WORKSPACES_ROOT.iterdir():
        if d.is_dir():
            meta_path = d / "metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        workspaces.append(meta)
                except:
                    pass
    
    # Sắp xếp để vifinqa_core luôn lên đầu
    workspaces.sort(key=lambda x: (x.get("id") != "vifinqa_core", x.get("created_at", "")))
    return workspaces

def create_workspace(name: str, description: str = ""):
    if not WORKSPACES_ROOT.exists():
        WORKSPACES_ROOT.mkdir(parents=True)
        
    # Tạo ID duy nhất
    ws_id = f"proj_{uuid.uuid4().hex[:8]}"
    
    ws_dir = WORKSPACES_ROOT / ws_id
    ws_dir.mkdir(parents=True)
    
    (ws_dir / "uploads").mkdir()
    (ws_dir / "artifacts").mkdir()
    (ws_dir / "artifacts" / "tables_csv").mkdir(parents=True)
    
    meta = {
        "id": ws_id,
        "name": name,
        "description": description,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(ws_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        
    return ws_id, meta

def get_workspace_artifacts_path(ws_id: str) -> Path:
    return WORKSPACES_ROOT / ws_id / "artifacts"

def get_workspace_uploads_path(ws_id: str) -> Path:
    return WORKSPACES_ROOT / ws_id / "uploads"
