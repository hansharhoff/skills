---
description: Retrospective on the current (or named) session — what went well/poorly, token-hygiene grade, a "did we forget anything?" cross-check, and suggestions, delivered as a one-pager Artifact.
---

Invoke the **session-retro** skill.

Reflect on the current Claude Code session (or the one named in the arguments)
and produce an honest retrospective one-pager:

1. Run the bundled analyzer to get the transcript digest (never read the raw
   `.jsonl`).
2. Reconstruct the story: goals, problems + fixes, key decisions, techniques.
3. Two lists — what went well, and what went poorly (each with a lesson).
4. **Token hygiene** — where `/clear` or `/compact` would have saved tokens,
   with a few general tips.
5. **Are we forgetting anything?** — cross-check the session against the
   whats-next handoff, durable memory, and the TaskList; flag uncaptured latent
   items and offer to capture them.
6. **Suggestions** — new skills, CLAUDE.md/memory edits, how we work together.
7. Publish it all as a one-pager **Artifact** and give the link.

Read-only: don't write memory, edit CLAUDE.md, or create tasks unless the user
approves.

Arguments (optional): a session id or transcript path to retro a different
session than the current one.
