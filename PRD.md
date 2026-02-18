# PRD.md - Morpheus Digital Nervous System

## 🎯 Vision
To build a highly autonomous, local-first AI "Home Base" that manages personal relationships, financial analysis, and content pipelines with direct agency on the user's hardware.

## 🏗️ Architecture
- **Gateway**: OpenClaw (running in Docker as an "Executive Router").
- **Engine**: Ollama (native Windows for RTX 4060 GPU acceleration).
- **Communication**: Telegram (@nvllm_memu_bot) as the primary UI.
- **Persistence**: Hybrid Markdown-based memory (`memory/*.md`) and local SQLite databases (planned).

## 🦾 Core Components
- [x] **Local Model Pipeline**: Native Ollama + llama3.1:8b.
- [x] **Identity System**: `SOUL.md`, `IDENTITY.md`, `USER.md` defined.
- [x] **Memory System**: Daily logs + long-term `MEMORY.md` + `KNOWLEDGE.md`.
- [x] **Agent Councils**: Security, Finance, and Growth advisor templates ready.
- [ ] **Gmail Integration**: Read, summarize, and triage emails via Telegram.
- [ ] **Google Calendar**: Check upcoming events on demand and via heartbeat.
- [ ] **Cron/Heartbeat**: Scheduled proactive inbox + calendar checks.

## 📈 Roadmap
1.  **Phase 1: Stabilization (DONE)**: Stable Gateway + GPU connection established.
2.  **Phase 2: Email Integration**: Connect Gmail via `/link`, enable inbox summaries and triage.
3.  **Phase 3: Calendar**: Add proactive event reminders via heartbeat cron jobs.
4.  **Phase 4: Expansion**: Multi-modal capabilities and specialized sub-agents.

## 🛠️ Tech Stack
- **OS**: Windows (Native + Docker Desktop).
- **GPU**: NVIDIA GeForce RTX 4060 Laptop GPU (8GB VRAM).
- **RAM**: 16GB (Current limit).
- **Primary Model**: llama3.1:8b (running at 8k context).
