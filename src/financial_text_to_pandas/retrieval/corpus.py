"""
corpus.py — Build retrieval corpus from Phase 1 artifacts.

Reads table_metadata.csv and individual table CSVs to build a unified
table_corpus.csv containing search_text for retrieval.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
import sys
import argparse

def build_table_corpus(table_metadata_path: Path, output_path: Path, include_review: bool = False) -> pd.DataFrame:
    """Build the search corpus from table_metadata.csv.
    
    Args:
        table_metadata_path: Path to table_metadata.csv from Phase 1.
        output_path: Where to save the resulting table_corpus.csv.
        include_review: If False, skip tables with needs_review=True.
        
    Returns:
        The built corpus DataFrame.
    """
    if not table_metadata_path.exists():
        raise FileNotFoundError(f"table_metadata.csv not found at {table_metadata_path}")
        
    metadata_df = pd.read_csv(table_metadata_path, encoding="utf-8-sig")
    
    if not include_review:
        metadata_df = metadata_df[~metadata_df["needs_review"]]
        
    corpus_rows = []
    
    # We need to read each CSV to get headers and row labels
    output_root = table_metadata_path.parent
    
    for _, row in metadata_df.iterrows():
        table_id = str(row["table_id"])
        csv_path_rel = str(row["csv_path"])
        abs_csv_path = output_root / csv_path_rel
        
        headers_text = ""
        row_labels_text = ""
        
        if abs_csv_path.exists():
            try:
                df = pd.read_csv(abs_csv_path, encoding="utf-8-sig")
                # Extract headers
                # Skip numeric__ columns and row_label cols for header search text
                data_cols = [c for c in df.columns if not c.startswith("numeric__") and not c.startswith("row_label_")]
                headers_text = " ".join(data_cols)
                
                # Extract row labels
                if "row_label_full" in df.columns:
                    row_labels_text = " | ".join(df["row_label_full"].dropna().astype(str).unique())
                elif "row_label_raw" in df.columns:
                    row_labels_text = " | ".join(df["row_label_raw"].dropna().astype(str).unique())
            except Exception as e:
                print(f"[WARN] Could not read CSV for {table_id}: {e}", file=sys.stderr)
        
        nearby_before = str(row.get("nearby_text_before", ""))
        nearby_after = str(row.get("nearby_text_after", ""))
        nearby_text = f"{nearby_before} {nearby_after}".replace("nan", "").strip()
        
        title = str(row.get("title", "")).replace("nan", "")
        unit = str(row.get("unit", "")).replace("nan", "")
        statement_type = str(row.get("statement_type", "")).replace("nan", "")
        ticker = str(row.get("ticker", "")).replace("nan", "")
        company_name = str(row.get("company_name", "")).replace("nan", "")
        year = str(row.get("year", "")).replace("nan", "")
        report_type = str(row.get("report_type", "")).replace("nan", "")
        
        # Build search_text
        search_parts = [
            title,
            headers_text,
            row_labels_text,
            nearby_text,
            unit,
            statement_type,
            ticker,
            company_name,
            year,
            report_type
        ]
        search_text = "\n".join([p.strip() for p in search_parts if p and str(p).strip() != ""])
        
        corpus_rows.append({
            "table_id": table_id,
            "csv_path": csv_path_rel,
            "ticker": ticker,
            "company_name": company_name,
            "year": row.get("year", 0),
            "report_type": report_type,
            "statement_type": statement_type,
            "unit": unit,
            "title": title,
            "headers_text": headers_text,
            "row_labels_text": row_labels_text,
            "nearby_text": nearby_text,
            "search_text": search_text,
            "quality_score": row.get("quality_score", 0.0),
            "needs_review": row.get("needs_review", False)
        })
        
    corpus_df = pd.DataFrame(corpus_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    return corpus_df


def main():
    parser = argparse.ArgumentParser(description="Build retrieval corpus from table_metadata.csv")
    parser.add_argument("--table-metadata", type=Path, required=True, help="Path to table_metadata.csv")
    parser.add_argument("--output", type=Path, required=True, help="Path to output table_corpus.csv")
    parser.add_argument("--include-review", action="store_true", help="Include tables marked needs_review")
    
    args = parser.parse_args()
    
    print(f"Building corpus from {args.table_metadata}")
    corpus = build_table_corpus(args.table_metadata, args.output, args.include_review)
    print(f"Built corpus with {len(corpus)} tables at {args.output}")

if __name__ == "__main__":
    main()
