# AI Financial Data Assistant

Current state: **plan-only**.

The project is specified as a Text-to-Pandas financial QA system:

```text
OCR TXT
-> clean CSV tables
-> table metadata
-> table retrieval
-> evidence package
-> Pandas reasoning
-> verification
-> answer
```

No source code or output folders should be created until the implementation spec is approved.

Core documents:

```text
Docx/01_Project_Plan.md
Docx/02_System_Architecture.md
Docx/03_Technology_Stack.md
Docx/04_Phase1_Data_Preparation.md
Docx/05_Phase2_Data_Retrieval_Core.md
Docx/06_Phase3_MultiAgent_Integration.md
Docx/07_Phase4_Deployment_and_Optimization.md
Docx/08_Task_Breakdown_and_Status.md
```

Retrieval priority:

```text
BM25 baseline
Qwen3-Embedding-8B dense retrieval
Reranker
```

No database is used for cleaned financial tables.
