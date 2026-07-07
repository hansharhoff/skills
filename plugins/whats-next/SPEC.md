# `whats-next` — design spec

**Date:** 2026-06-04
**Status:** approved design · not yet implemented
**Home:** `hansharhoff/skills` marketplace (generic skill)
**Author:** Hans, with Claude

## Problem

Hans frequently context-switches between projects, sessions, and time-zones. When picking a session back up he needs a fast triage of "what's the highest-leverage thing to do RIGHT NOW", drawing from in-session tasks, open PRs, scheduled memory notes, Atlassian items, git state, and the small "let's circle back" / "remind me to" hints that accumulate in conversation.

Today he asks variants of "what's next?" by hand each time, and the answer relies on whichever signals happen to be top-of-context. Forgotten items stay forgotten; capture of new TODOs is ad-hoc.

## Goal

A single skill that:

1. **Reads** the current workspace's state across PRs, in-session tasks, scheduled memory notes, Atlassian (when MCP available), git, and circle-back items, and renders a ranked dashboard ≤ 80 % of one screen.
2. **Captures** new TODOs from natural-language phrases ("remind me to …", "let's circle back to …", "for later") into either an in-session task or a durable memory file, depending on dating.
3. **Closes** every render with a concrete one-line question targeting the top item, so Hans can act with a one-word reply.
4. Acts, over time, like a lightweight project manager Hans hands open loops to.

## Non-goals

- Cross-workspace triage (scope: current workspace only — Hans confirmed 2026-06-04).
- Long-form retrospective / "dreaming" outputs (that's a separate skill in the pipeline).
- Auto-acting on items without confirmation (every action goes through the closing prompt).
- Replacing TaskList — it complements both TaskList (in-session) and memory files (durable).

## Architecture (Approach B — Skill + helper script)

```
~/workspaces/skills/plugins/whats-next/
├── plugin.json            # name, version, slash command, hooks declaration
├── README.md              # marketplace-facing description
├── SPEC.md                # this file
├── skills/whats-next/
│   └── SKILL.md           # description triggers; calls bin/gather.py;
│                          # adds session-only collectors; formats output
├── commands/whats-next.md # slash command body — delegates to the skill
├── bin/
│   └── gather.py          # CLI-collectable sources → structured JSON
├── hooks/
│   └── session_start.json # SessionStart hook — runs gather.py once,
│                          # injects result into the first user prompt
└── tests/
    └── test_gather.py     # unit tests on gather.py only
```

Two layers of logic:

- **`bin/gather.py`** — Python, side-effect-free, no MCP access. Reads CLI-available sources (gh, git, memory files). Emits JSON on stdout. Always exits 0 (errors go in-band in an `errors[]` array).
- **`skills/whats-next/SKILL.md`** — markdown procedure executed by the assistant. Calls gather.py, layers in session-only sources (TaskList, Atlassian MCP, recent conversation), merges all items, applies the ranking + 80 %-screen budget, renders the dashboard, asks the closing question.

## Activation

Three triggers, all routed to the same SKILL.md:

1. **Slash command:** `/whats-next` — always available, explicit.
2. **Skill description triggers (READ mode):** the SKILL.md's `description:` frontmatter includes phrases like *"what's next"*, *"where were we"*, *"triage"*, *"what should I do"*, *"status"*, *"what now"*.
3. **Skill description triggers (CAPTURE mode):** *"remind me to …"*, *"let's circle back to …"*, *"we should X later"*, *"for later"*, *"don't forget to …"*, *"note for next time"*.
4. **Session-start hook:** `hooks/session_start.json` runs `bin/gather.py --as-prompt-injection`, which wraps its JSON in a `<whats-next>…</whats-next>` block injected into the first user prompt. That triggers the SKILL.md via description match.

CAPTURE mode and READ mode share the same SKILL.md body; the procedure branches on the trigger phrase.

## `bin/gather.py` contract

### Invocation

```
bin/gather.py [--workspace PATH] [--as-prompt-injection]
```

- `--workspace` defaults to `$CLAUDE_PROJECT_DIR` (Claude Code) or `$PWD`.
- `--as-prompt-injection` wraps the JSON output in `<whats-next>…</whats-next>` for the session-start hook.

### Output (stdout)

A single JSON object:

```json
{
  "workspace": "/Users/hans/workspaces/bestseller/appretio-ml-recomeng",
  "generated_at": "2026-06-04T12:34:56Z",
  "items": [
    {
      "kind": "pr",
      "ref": "#106",
      "title": "ci: 1h timeout + seed main tables",
      "url": "https://github.com/.../pull/106",
      "score": 9.4,
      "urgency": 7,
      "recency_mult": 1.10,
      "dependency_mult": 1.3,
      "why": "green 18h · no review · blocks #98",
      "touched_at": "2026-06-03T20:00:00Z",
      "raw": { "ci": "7/7 pass", "reviews": 0, "comments": 0, "draft": false }
    }
  ],
  "errors": []
}
```

### Item kinds + ID scheme

| `kind` | `ref` format | Example |
|---|---|---|
| `pr` | GitHub PR number with `#` | `#106` |
| `task` | `T` + ordinal | `T1` |
| `memory_scheduled` | `M` + ordinal | `M1` |
| `jira` | issue key verbatim | `DAS-6267` |
| `confluence` | `C` + ordinal | `C1` |
| `git` | `G` + ordinal | `G1` |
| `open_question` | `Q` + ordinal | `Q1` |
| `handoff` | `H` + ordinal | `H1` |

IDs are **stable within a single render**, not globally. When Hans types `do #106` or `defer Q2`, the skill resolves against the most-recent rendered dashboard.

### Failure mode

- Per-collector errors push to `errors[]`. No exception escapes.
- Exit code is 0 unless gather itself crashes (unhandled Python exception).

## Data sources

### gather.py (CLI-collectable)

1. **PRs** — `gh pr list --author @me --state open` for the workspace's git remote. Yields one item per open PR.
2. **Memory-scheduled** — scans `~/.claude/projects/<workspace-slug>/memory/*.md`, but only genuine circle-back reminders count: a file qualifies iff it is named `circle_back_*.md` **or** carries an explicit `target_date:` frontmatter field. Standing auto-memory (feedback/project/reference facts, the `MEMORY.md` index) lives in the same directory and routinely contains prose dates and words like "revisit"/"TODO"/"due" — those are ignored. The due-date is read only from `target_date:` (or the `TOMORROW` keyword), never scraped from body prose (which is usually a reference/report date, not a deadline); a qualifying reminder with no such date is a dateless "keep on radar" note.
3. **Git state** — `git status --porcelain` for uncommitted files + `git log origin/<branch>..HEAD --oneline` for unpushed commits.

### SKILL.md (session-only, layered on top)

4. **In-session tasks** — read via the TaskList tool inside the skill body. Maps to `kind: "task"`, refs `T1`, `T2`, …
5. **Atlassian MCP** (when available) — the skill detects `mcp__claude_ai_Atlassian__*` tools and runs:
   - `searchJiraIssuesUsingJql` with `assignee = currentUser() AND statusCategory != Done` → `kind: "jira"`.
   - `searchJiraIssuesUsingJql` with `comment ~ currentUser() AND updated >= -14d` → mentions, lower score.
   - `searchConfluenceUsingCql` with `task.assignee = currentUser() AND task.status = "incomplete"` → inline tasks, `kind: "confluence"`.
   - `searchConfluenceUsingCql` with `mention = currentUser() AND lastModified >= -7d` → mentions, lower score.
6. **Open questions / circle-back** — read durable memory files named `circle_back_*.md` (written by CAPTURE mode); also scan the last ~20 turns of conversation for trigger phrases not yet captured. `kind: "open_question"`, refs `Q1`, `Q2`, …
7. **Previous-session handoff** — read `~/.claude/projects/<workspace-slug>/whats-next-handoff.md` (written by the previous run's step 8). Picks up *latent* state from prior sessions — small asides, decisions, in-flight work — that wasn't tracked elsewhere. `kind: "handoff"`, refs `H1`, `H2`, … Skipped if the file doesn't exist (e.g. first invocation in a workspace).

### Graceful degradation

- gh unauthenticated → PRs collector returns empty + adds an `errors[]` entry.
- MCP not connected → Atlassian collectors skipped silently (a single-line footer notes it).
- Memory dir missing → memory_scheduled returns empty.
- Handoff file missing → first-invocation case, skipped silently (no error).

## Handoff persistence (write side)

After every READ-mode render, the skill writes `~/.claude/projects/<workspace-slug>/whats-next-handoff.md` (always overwrites — the latest snapshot is canonical).

The handoff captures **only the latent state** from the current session that won't be re-discoverable next session via the existing collectors above:

- **Latent asides** — small things mentioned in passing that didn't become a PR / task / memory file / Jira ticket.
- **Decisions made** — settled choices the user committed to (reference info, not action — surfaced only when the user asks).
- **In-flight (not yet tracked)** — work that started but isn't in a tracked system.
- **Open / awaited (who/what)** — blocked on someone else's response, with named person + what we're waiting on.

The skill should **not** duplicate items already discoverable elsewhere (PRs, git, Jira, memory) — those are re-found via gather.py + the session-only sources on the next run.

Rationale: when Hans `/clear`s a long session and starts fresh, the new session loses the conversational context entirely. PRs and tracked items survive because they're in external systems; the *latent context* would otherwise vanish. This file is the bridge.

## Ranking algorithm

```
score = urgency × recency_multiplier × dependency_multiplier
        (clipped to [0, 10])
```

**Urgency `[0, 10]`** — primary axis, intrinsic to item type:

| Kind | Urgency rules |
|---|---|
| `pr` | 8 if green + unreviewed + blocks another open item; 7 if green + unreviewed; 6 if green + changes-requested (your action); 5 if green + draft (your flip); 4 if pending CI; 2 default open |
| `task` | 7 `in_progress`; 4 `pending` unblocked; 0 `pending` blocked |
| `memory_scheduled` | 9 overdue; 7 due today; 4 due this week; 2 future |
| `jira` | priority Highest 7 / High 6 / Medium 4 / Low 2; +1 if due-date this week |
| `confluence` | inline-task assigned 5; recent mention 2 |
| `git` | uncommitted on PR branch 4; uncommitted otherwise 2; unpushed commits 3 |
| `open_question` | captured ≤ 7 days ago: 3; older: 5 (forgotten penalty) |

**Recency multiplier `[1.0, 1.5]`** — small forgotten-item boost:

| Days since touched | Multiplier |
|---:|---:|
| 0 | 1.00 |
| 1–3 | 1.10 |
| 4–7 | 1.25 |
| 8–30 | 1.40 |
| 30+ | 1.50 |

**Dependency multiplier `[1.0, 1.3]`**:
- 1.3 if item blocks another open item (unblocker).
- 1.1 if item is the only unfinished one in its kind.
- 1.0 otherwise.

**Drop threshold:** `score < 1.0` → excluded from output.

**Tiebreak:** higher urgency wins; then more recent `touched_at`; then alphabetical title (stable).

## Output format

≤ 80 % of one screen (≈ 40 lines × 100 chars).

```
Next: <action verb> <ref> — <one-line why>
<one-line context — why this beats the others>

📌 Pull Requests (N open)
  #106  ci: 1h timeout + seed main tables          🟢 green · 18h · blocks #98
  #105  feat: pareto sweep CLI                     🟢 green · 24h unreviewed
  #98   feat: pareto viewer tab                    🟡 4 fails · clears w/ #106

✅ Tasks (N in-progress / M pending)
  T1  Merge & ship                                 in_progress · 9h
  T2  Bidirectional coupling                       completed · 4h

📅 Scheduled (N due / overdue)
  M1  Friction retro (today)                       project_friction_retro_2026_06_04
  M2  Revisit copy-skip question                   no date · keep on radar

🎫 Atlassian (N items)         ← only if MCP available
  DAS-6267  Pareto sweep …                          assignee=you · Medium · 3d
  C1        Confluence: standup notes               inline task · 7d

🌿 Local (N items)             ← only if non-empty
  G1  uncommitted on feat/pareto-viewer-tab        3 files · likely WIP

❓ Open questions / circle-back (N captured)
  Q1  "revisit the copy-skip design"                18h ago · no date
  Q2  "check the bestseller frontier"               4h ago · TODAY

(showing N of M items · `/whats-next --all` for full)

➤ Take action on #106? (admin-merge / wait for review / ping reviewer / drop)
```

**Budget enforcement (in SKILL.md):**
- Top-line + context: 2 lines.
- Per-section: 1 header + ≤ 4 items = 5 lines.
- 5–6 sections × 5 lines ≈ 30 lines + spacing ≈ 35 lines.
- Empty sections are dropped silently.
- `--all` bypasses the cap.

**Empty-state outputs:**
- No items at all → `Nothing pressing. You're caught up.`
- Single item → top-line only, no dashboard.

**Action-verb table** (drives the top-line + closing prompt):

| Top item state | Suggested verb | Alternatives in closing prompt |
|---|---|---|
| PR green unreviewed | admin-merge | wait for review / ping reviewer / drop |
| PR red, code suspect | investigate failures | rerun CI / drop |
| PR draft, green | flip to ready | drop |
| Task in_progress | continue | pause / drop |
| Memory due-today | act now | reschedule / drop |
| Jira high priority | look at the ticket | reassign / comment / drop |
| Confluence inline task | open the page | drop |
| Circle-back captured | revisit | reschedule / convert to task / drop |
| Git uncommitted | commit or stash | drop |

When Hans replies with one of the alternative verbs, the skill performs that action (where automatable) and offers the next-highest item.

## CAPTURE mode

Triggers: `remind me to …`, `let's circle back to …`, `we should X later`, `for later`, `don't forget to …`, `note for next time`, `TODO …`, `circle back on …`.

Behaviour:
1. Echo back: `Captured: "<paraphrase>"`
2. Dating heuristic:
   - Phrase contains `today`, `tomorrow`, `by <day>`, ISO date → **durable memory file** named `circle_back_<slug>.md` in the standard Claude Code memory directory (see "Durable memory" below), with the parsed date in frontmatter.
   - No date → **`TaskCreate`** in current session.
3. Acknowledgement: `Captured as <ref>` (where `<ref>` is the new `T<n>` or `Q<n>`).
4. Returns to whatever conversation was happening — does NOT show the full dashboard unless the user explicitly invokes it.

Durable memory files use the standard Claude Code per-user memory directory (`$HOME/.claude/projects/<workspace-slug>/memory/`) — same path Claude Code already uses for the auto-memory system. The path is per-user (resolves via `$HOME`), so installing this skill on another machine works without configuration.

## Tests

`tests/test_gather.py` covers:

- PR collector with mocked gh output (green/red/draft/blocked permutations).
- Memory-scheduled with sample memory files (overdue, today, this week, future).
- Git state with a tmp git repo (clean, dirty, unpushed).
- Ranking: known input → known order.
- JSON shape: schema validation (required keys, types).
- Failure: each collector raising → captured in `errors[]`, exit code 0.

No tests on SKILL.md (markdown-driven procedures are hard to unit-test); rely on hand-driving the skill in a Claude session after install.

## Plugin manifest

```json
{
  "name": "whats-next",
  "version": "0.1.0",
  "description": "PM-style triage + capture for the active workspace",
  "commands": [
    { "name": "whats-next", "command": "commands/whats-next.md" }
  ],
  "hooks": [
    {
      "event": "SessionStart",
      "spec": "hooks/session_start.json"
    }
  ]
}
```

(`plugin.json` exact schema follows the conventions already in `repo-cleanup` and `teach-tech` in this repo — check those before implementation.)

## Rollout

1. Implement `bin/gather.py` + `tests/test_gather.py` first (pure Python, easy to validate).
2. Implement `SKILL.md` (markdown procedure + frontmatter triggers).
3. Implement `commands/whats-next.md` slash command (3-line delegation).
4. Implement `hooks/session_start.json` last (depends on gather.py being stable).
5. Add to the marketplace's `README.md` and the repo's plugin index.
6. Hand-test in a fresh Claude Code session: invoke each trigger; capture a TODO; verify session-start auto-fire renders before the first user message lands.

## Open questions (for follow-up after first ship)

1. **Cross-workspace mode** — Hans confirmed current-workspace-only for v1, but multi-workspace scan could be valuable for the morning catch-up. Revisit after a week of v1 usage.
2. **"Open questions from conversation" collector** — punted in §3 of the design. Hard heuristic. Revisit if Hans finds himself manually adding `Q*` items often.
3. **Bias against draft PRs** — currently scored 2-5. May want to drop them entirely from the default view, with `--all` to surface.
4. **Action automation** — closing prompt currently lists verbs; the skill performs SOME (admin-merge) but not all (act-on-Jira). Define a clear automation surface in v2.
