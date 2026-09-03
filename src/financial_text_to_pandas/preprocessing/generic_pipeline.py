import os
import sys
from pathlib import Path
import pandas as pd
import uuid

# Đảm bảo đường dẫn import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from financial_text_to_pandas.workspace import get_workspace_artifacts_path, get_workspace_uploads_path
from financial_text_to_pandas.retrieval.corpus import build_table_corpus
from financial_text_to_pandas.retrieval.bm25 import build_bm25_index
from financial_text_to_pandas.retrieval.embeddings import embed_tables

def process_generic_workspace(ws_id: str):
    print(f"Processing workspace {ws_id}...")
    uploads_dir = get_workspace_uploads_path(ws_id)
    artifacts_dir = get_workspace_artifacts_path(ws_id)
    tables_dir = artifacts_dir / "tables_csv"
    indexes_dir = artifacts_dir / "indexes"
    
    indexes_dir.mkdir(parents=True, exist_ok=True)
    
    metadata_rows = []
    
    for file_path in uploads_dir.glob("*"):
        if not file_path.is_file(): continue
        
        try:
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8')
            elif file_path.suffix.lower() in ['.xls', '.xlsx']:
                df = pd.read_excel(file_path)
            else:
                print(f"Skipping unsupported file: {file_path.name}")
                continue
                
            # Tạo table_id ngẫu nhiên
            table_id = f"table_{uuid.uuid4().hex[:8]}"
            csv_name = f"{table_id}.csv"
            out_csv = tables_dir / csv_name
            
            # Lưu file CSV chuẩn
            df.to_csv(out_csv, index=False, encoding="utf-8-sig")
            
            # Đăng ký metadata
            metadata_rows.append({
                "table_id": table_id,
                "csv_path": f"tables_csv/{csv_name}",
                "title": file_path.name,
                "needs_review": False,
                "year": 2024,
                "company_name": "Generic Upload",
                "ticker": "UPLOAD",
                "statement_type": "Generic",
                "report_type": "User Upload"
            })
            print(f"Ingested {file_path.name} -> {table_id}")
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
            
    if not metadata_rows:
        print("No valid CSV/Excel files found in uploads.")
        return False
        
    meta_df = pd.DataFrame(metadata_rows)
    meta_path = artifacts_dir / "table_metadata.csv"
    meta_df.to_csv(meta_path, index=False, encoding="utf-8-sig")
    
    print("Building corpus...")
    corpus_path = indexes_dir / "table_corpus.csv"
    corpus_df = build_table_corpus(meta_path, corpus_path, include_review=True)
    
    print("Building BM25 index...")
    build_bm25_index(corpus_df, indexes_dir)
    
    print("Building Dense Embeddings...")
    embed_tables(corpus_df, indexes_dir)
    
    print("Processing complete!")
    return True

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        process_generic_workspace(sys.argv[1])
