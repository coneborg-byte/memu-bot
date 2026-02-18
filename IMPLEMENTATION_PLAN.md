# Hybrid Container Model Implementation Plan
**Goal:** Run "kinetic" tools (file/command) in Docker while keeping Antigravity on the host for safety and resource management (16GB RAM limit, RTX 4060).

**Status:** PENDING

---

## Phase 1: Establish the Jailed Sandbox (Docker)
- [ ] **Install/Prepare Docker Desktop**:
    - [ ] Enable WSL2 backend.
    - [ ] Enable NVIDIA GPU support (Settings > Resources > WSL Integration).
    - [ ] *Action Required: User must install Docker Desktop.*
- [ ] **Create Private Network**:
    - [ ] Run: `docker network create agent-net`
- [x] **Launch Ollama (GPU Access)**:
    - [x] Pull model: `llama3.1:8b` (Q4_K_M quantization).
    - [x] Run: `docker run -d --gpus all -v ollama_data:/root/.ollama -p 11434:11434 --name ollama --network agent-net ollama/ollama`
- [x] **Build OpenClaw from Source (Jailed)**:
    - [x] Created `Dockerfile.openclaw` using Node 22 base.
    - [x] Build: `docker build -t openclaw-custom -f Dockerfile.openclaw .`
- [x] **Launch OpenClaw Gateway**:
    - [x] Mount project folder: `c:\Users\nvllm\.gemini\antigravity\scratch\morpheus_ai`
    - [x] Run: `docker run -d -p 127.0.0.1:18789:18789 -e OPENCLAW_GATEWAY_TOKEN=morpheus123 --name openclaw --network agent-net openclaw-custom`

## Phase 2: Configure the "Remote Brain" (Telegram)
- [ ] **Create Telegram Bot**:
    - [ ] Talk to `@BotFather` to get API Token.
- [ ] **Configure Dashboard (OpenClaw)**:
    - [ ] Access: `http://localhost:18789`
    - [ ] Channel: Enter Telegram Bot Token.
    - [ ] Provider: Set URL to `http://ollama:11434/v1`.
    - [ ] Security: Set `gateway.bind: "loopback"` in `openclaw.json`.
- [ ] **Skip MemU**: As requested, MemU integration is omitted.

## Phase 3: Connect the Host IDE (Google Antigravity)
- [ ] **Install Open Code Extension**: (In Antigravity IDE).
- [ ] **Auth Login**: `opencode auth login`.
- [ ] **Initialize Specialist Squad**:
    - [ ] Run: `npx antigravity-ide init` (Antigravity Kit 2.0).
- [ ] **Terminal Policy**:
    - [ ] Set to "Auto" (User Setting).

## Phase 4: Hardening and Autonomy Activation
- [ ] **Command Deny-List**:
    - [ ] Add: `rm -rf`, `sudo`, `format`.
- [ ] **Create GEMINI.md Rule**:
    - [ ] Add: `"Every terminal command must end with a newline character (\n)"`.
- [ ] **GPU Resource Management**:
    - [ ] Close heavy apps during "Planning" phase.
    - [ ] Use `Gemini 3 Flash` as primary model for low latency.

---

## Next Steps
This plan requires **Docker Desktop** to be installed and running. Please confirm installation before proceeding with Phase 1.
