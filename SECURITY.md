# Security Architecture & Risk Assessment
**Date**: 2026-02-20
**Status**: AUDITED (Morpheus Security Audit v1.0)

## 1. Executive Summary
The Morpheus AI (OpenClaw) environment is designed as a containerized agent with restricted access to local hardware and cloud services. Following the latest audit, several critical and high-risk items were rectified via environment isolation and permission hardening.

## 2. Risk Mitigation

### 🔑 Secret Management
*   **Environment Variables**: All sensitive API keys (`OPENROUTER_API_KEY`) and Bot Tokens (`TELEGRAM_BOT_TOKEN`) have been moved from plaintext configuration files (`openclaw.json`) into the protected `.env` file.
*   **Permissions**: The `.env` and `credentials.json` files are restricted to `600` (read/write by owner only).
*   **Redaction**: System instructions are configured to auto-redact tokens from any outbound messages.

### 🦾 Execution & Agency
*   **The `exec` Tool**: Morpheus uses the `exec` tool to run local scripts (`mail_bridge.py`, `scanner.py`). While this provides agency, all scripts are stored within the container-mounted volume and are restricted by filesystem permissions.
*   **Access Control**: Filesystem permissions for `memory/`, `tokens/`, and `library/` are set to `700` to prevent unauthorized cross-user access on the host system.

### 🧠 Memory & Context
*   **Memory Search**: The `memorySearch` feature is enabled in `openclaw.json`. This enables local vector search of the `KNOWLEDGE.md` and `MEMORY.md` files for semantic retrieval. It does NOT exfiltrate data to the cloud; embedding generation is performed locally via Ollama.

## 3. Residual Risks (Acceptable)
*   **OAuth Complexity**: Google OAuth is used for Gmail/Calendar access. While complex, it is the industry standard. Tokens are stored locally in `tokens/gmail/` and are encrypted/protected by Google's client infrastructure.
*   **Plaintext Internal Traffic**: Communication between the Docker container and the Ollama host (`host.docker.internal`) uses plaintext HTTP. This is acceptable as it remains within the local loopback/bridge network of the physical machine.

## 4. Maintenance Schedule
*   **Audit**: Run `/secure` (or `python3 skills/security/audit.py`) weekly.
*   **Pruning**: Old mission files and logs are pruned weekly to minimize the "data surface" for potential breaches.
