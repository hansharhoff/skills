---
description: Triage the current workspace — show what to work on next
---

Invoke the **whats-next** skill in READ mode.

Render the ranked dashboard for the current workspace (open PRs, in-session
tasks, scheduled memory notes, Atlassian items if MCP available, git state,
captured circle-back items) and close with the action question.

If the user passed `--all`, pass that through to the skill so it bypasses
the per-section 4-item cap.

Arguments: $ARGUMENTS
