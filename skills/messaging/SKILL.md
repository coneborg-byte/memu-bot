---
name: messaging
description: >
  Messaging rules and Telegram topic routing. Use when: deciding where to send a message,
  what format to use, or how many messages to send for a task. These rules apply to every
  outbound message on every channel.
---

# Messaging Skill

## Core Rules (Always Apply)

**Two messages max per task.**
- Message 1: Acknowledgment (only if the task takes more than 5 seconds)
- Message 2: The result
- Never send play-by-play narration ("Now I'm checking your email... OK found 3 emails... Now classifying...")

**Send files, not links.**
When delivering a file (report, backup manifest, export), send the actual file attachment. Not a Google Drive link, not a path. The file.

**Nothing gets cross-posted.**
Each topic receives only its designated content type. A security alert never goes to the daily brief topic. A morning briefing never goes to the email alerts topic.

**Silent on success for automated jobs.**
Cron jobs that complete successfully stay silent. Only speak up on failures, urgent findings, or things that need Nev's attention.

## Telegram Topic Routing

| Topic Name | What Goes There | What Doesn't |
|---|---|---|
| **Daily Brief** | Morning briefing (07:00 cron only) | Anything else |
| **Email Alerts** | Urgent email notifications | Routine emails, briefings |
| **Security** | Nightly audit reports, gateway checks, injection attempts | Everything else |
| **Cron Updates** | Job failures only | Success confirmations |
| **General** | Direct conversation, ad-hoc requests, everything else | Automated reports |

## Format Rules

- **Urgent alerts**: Lead with the emoji and severity. Get to the point in line 1.
- **Reports**: Use the structured format defined in each skill's SKILL.md.
- **Conversational replies**: Match Nev's energy. Short question = short answer.
- **No markdown overkill**: Use bold and bullets where they help. Not everywhere.

## What Not to Do

- Don't say "I'll now proceed to..." — just do it.
- Don't confirm receipt of every message — only if it'll take a while.
- Don't end every message with "Let me know if you need anything!" — Nev knows.
- Don't send the same information twice in one conversation.
