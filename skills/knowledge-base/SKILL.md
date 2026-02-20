---
name: knowledge-base
description: >
  Morpheus Knowledge Base System. Use when: user wants to "remember" an article, YouTube video, 
  or PDF, or when they ask a question that requires searching your private brain. 
  Follows the "Ingest + Embed -> SQLite + Vectors" architecture.
---

# Knowledge Base System 🧠

## What This Does
Implements a permanent, searchable memory for Morpheus.
1. **Ingest**: Pulls data from Articles, YouTube (transcripts), X/Twitter (via Missions), and PDFs.
2. **Embed**: Converts text into vector embeddings using `all-MiniLM-L6-v2`.
3. **Storage**: Saves raw text and metadata in **SQLite** and vector indexes in **FAISS**.
4. **Query**: Allows "Ask in Plain English" retrieval.

## How to Ingest
To add something to the brain:
```bash
python skills/knowledge-base/ingest.py --url "https://youtube.com/..." --title "Video Title"
python skills/knowledge-base/ingest.py --file "report.pdf"
```

## How to Query
To search the brain:
```bash
python skills/knowledge-base/search.py "What did Berman say about vector databases?"
```

## Architecture
- **Raw Data**: `library/knowledge/kb.db` (SQLite)
- **Vector Index**: `library/knowledge/vector.index` (FAISS)
- **Status**: Active (RAG-enabled)

## Rules
- Always summarize the the ingestion result to the user.
- If a YouTube video has no transcript, fall back to the description.
- Tag every entry with its source type (youtube, web, pdf, x).
- Verification: Perform a search after ingestion to ensure it's "remembered".
