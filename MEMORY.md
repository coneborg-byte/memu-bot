# MEMORY.md - Long-Term Memory

_This is your curated, distilled memory. Raw daily logs go in `memory/YYYY-MM-DD.md`. This file is the essence — what's worth keeping forever._

_Only load this in the MAIN SESSION (direct chat with Nev). Do NOT share in group chats._

---

## Key Facts

- Nev is building a local-first AI called **Morpheus** running on an RTX 4060 in Wales, UK.
- The system uses **OpenClaw** (Docker) as the gateway and **Native Ollama** for GPU-accelerated inference.
- Primary interface is Telegram bot `@nvllm_memu_bot`.
- Nev values speed, privacy, and real agency. He dislikes slow responses and filler text.

## System History

- **2026-02-18**: Successfully migrated from Dockerized Ollama to Native Windows Ollama. Resolved 1008 auth errors and context window size conflicts. Bot is now live and responding on Telegram.

## Lessons Learned

- OpenClaw requires a minimum 16k context window declared in config, but actual `num_ctx` sent to Ollama can be lower (8k) to fit within 12.4GB available RAM.
- The `auth-profiles.json` file must exist in the agent directory for the ollama-local provider to authenticate.
- Workspace files are mounted at `/root/.openclaw/workspace/` inside the container.
