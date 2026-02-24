# Digital Nervous System: Full Architecture Review
**Date**: 2026-02-18
**Status**: ACTIVE
**Components**: 3 (Morpheus, Antigravity, memU)
**Hardware**: Local Laptop (RTX 4060, 16GB RAM)

---

## 1. The Core Components

### 🧠 Morpheus (The Nervous System)
- **Role**: The "Executive Router" (OpenClaw) running in Docker.
- **Interface**: Telegram Bot (`@nvllm_memu_bot`).
- **Intelligence**: Native **Ollama** (Llama 3.1 8B) with direct GPU access.
- **Capabilities**:
    - **Intent Routing**: Directs requests to sub-agents or local skills.
    - **Memory**: Persistent storage in `memory/*.md` and `KNOWLEDGE.md`.
    - **Agency**: Executes tools (Browser, Files, Bash) via OpenClaw's skill system.
    - **Daily Briefing**: Automates summaries of your Digital Life.

### 🦾 Antigravity (The Cloud Muscle)
- **Role**: The "Heavy Worker" who performs complex, internet-connected tasks on demand.
- **Interface**: Antigravity AI session (opened by Nev when needed).
- **Intelligence**: Cloud-hosted Gemini.
- **Capabilities**:
    - **Web Scouting**: Scans X (Twitter) and YouTube for "Alpha."
    - **Deep Research**: Summarizes articles and writes reports to `library/`.
    - **Code Audits**: Reads the local codebase for security vulnerabilities.
- **Limitation**: Only active when the Antigravity session is open. Morpheus queues missions in `missions/` for Antigravity to process.

---

### 📚 Knowledge Base (The Memory)
- **Architecture**: Ingest + Embed -> SQLite + Vectors (FAISS).
- **Social Connectors**: 
    - **YouTube**: Transcript extraction via `yt-dlp`.
    - **X / Twitter**: Hybrid scouting (Cloud scraping -> Local vectorization).
    - **PDF / Articles**: Deep parsing and semantic chunking.
- **Retrieval**: High-speed semantic search using `all-MiniLM-L6-v2`.
- **UX**: "Ask in Plain English" via Telegram topics.

## 2. Active Workflows (Loops)

### 📡 The "Scout" Loop (X Ingestion)
1.  **You (Telegram)**: `/scout Llama 4 News`
2.  **Morpheus**: Logs a mission file (`missions/mission_[timestamp]_scout_x.json`).
3.  **You (Here)**: Open chat and say "Sync."
4.  **Antigravity**: Reads mission -> Scans X -> Writes report to `library/X_Scout_Llama4.md`.
5.  **You (Telegram)**: `/research Llama 4` -> Morpheus reads the new file and summarizes it.

### 📚 The "Research" Loop (Library)
1.  **You (Telegram)**: `/research OpenClaw`
2.  **Morpheus**: Scans the local `library/` folder for keywords.
3.  **Action**: Returns a summary of matching Markdown files directly to your phone.

### 🏛️ The "Council" Loop (Decision Making)
1.  **You (Telegram)**: `/consult Should I upgrade RAM?`
2.  **Morpheus**: Reads 3 Persona Files (`COUNCILS/RISK_ADVISOR.md`, etc.).
3.  **Action**: Simulates a debate between the personas using local Ollama.
4.  **Result**: Returns a structured "Council Minutes" report.

### 🛡️ The "Security" Loop (Self-Audit)
1.  **You (Telegram)**: `/secure`
2.  **Morpheus**: Reads his own source code (`morpheus_bot.py`).
3.  **Action**: Sends the code to Ollama with the "Security Council" prompt.
4.  **Result**: Returns a vulnerability report (e.g., "Hardcoded path found").

---

## 3. The Portal Protocol (Permanent Security Model)
- **Constraint**: Morpheus remains in a permanent Docker sandbox (v2026.2.22). Direct host execution is VETOED.
- **Portals**: Controlled access to the host is limited to specific bind-mounted directories:
    - `/CRM_Workspace` -> Secure contact and interaction storage.
- **API First**: Communication with external services (Gmail, Calendar) is moved to OAuth-scoped API calls, reducing reliance on local system utilities.
- **Human-in-the-Loop (HITL)**: Any write-action outside the sandbox requires a "Nev Approved" confirmation.
- **Localhost Locking**: All web-facing services are strictly bound to `127.0.0.1`.

---

## 4. File Structure (Your Laptop)
`c:\Users\nvllm\.gemini\antigravity\scratch\morpheus_ai\`
├── `morpheus_bot.py` (The main brain script)
├── `mission_control.py` (The local background watcher)
├── `missions/` (The queue of JSON tasks waiting for Antigravity)
├── `library/` (The archive of research reports)
├── `COUNCILS/` (The personality files for advisors)
├── `SECURITY_COUNCIL/` (The personality files for auditors)
├── `CONTACTS.md` (The CRM database)
├── `KNOWLEDGE.md` (The permanent user fact database)
└── `.env` (The keys for Telegram and Ollama)
