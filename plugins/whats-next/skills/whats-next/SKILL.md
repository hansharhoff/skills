---
name: whats-next
description: >
  PM-style triage and capture for the active workspace. Use this skill in READ
  mode when the user asks "what's next", "where were we", "what should I do",
  "what now", "status", or asks for a "triage" / "catch me up" — produces a
  ranked dashboard across open PRs, in-session tasks, scheduled memory notes,
  Atlassian items (when MCP is available), git state, and previously captured
  circle-back items. Use it in CAPTURE mode when the user says "remind me to
  …", "let's circle back to …", "we should X later", "for later", "don't
  forget to …", "note for next time", "TODO …", or "circle back on …" — the
  skill captures the new item as either an in-session task or a durable memory
  file and acknowledges with a stable reference.
---

# whats-next

PM-style "what should I work on right now?" for the current workspace, plus
lightweight capture of new TODOs from natural-language phrases.

The skill operates in two modes that share one body. **Detect the mode from
the user's phrasing first**:

| Mode | Trigger phrases (examples) |
|---|---|
| READ | "what's next", "where were we", "what should I do", "what now", "status", "triage", "catch me up", or the `/whats-next` slash command |
| CAPTURE | "remind me to …", "let's circle back to …", "we should X later", "for later", "don't forget to …", "note for next time", "TODO …", "circle back on …" |

If the user's message contains a CAPTURE trigger, run **CAPTURE mode** below
and then return to whatever the conversation was about — **do not** render the
full dashboard. If the user explicitly asks both (e.g. "remind me X and show
me what's next"), run capture first, then READ.

---

## READ mode

### 1. Run `bin/gather.py`

Invoke the helper script with the active workspace. The script is bundled
with this plugin under `bin/gather.py` (relative to the plugin root). Typical
invocation pattern:

```
<plugin>/bin/gather.py --workspace "$CLAUDE_PROJECT_DIR"
```

The script emits a single JSON object with `items[]` (already ranked,
filtered to `score >= 1.0`, sorted high→low) and `errors[]`. **Always exits
0** — surface `errors[]` only as a one-line footer.

### 2. Layer in session-only sources

After parsing the JSON, add these collectors. Each is best-effort — skip
silently if the tool is unavailable.

**In-session tasks** — read the current TaskList via the TaskList tool. For
each task:
- `kind: "task"`, `ref: "T<n>"` (ordinal in TaskList order).
- Urgency: `in_progress` → 7, `pending` and unblocked → 4, `pending` and
  blocked → 0 (drop). Completed tasks are dropped from the dashboard.
- Recency multiplier: based on the task's last update if available, else 1.0.

**Atlassian** — if any `mcp__claude_ai_Atlassian__*` tool is callable in the
session, run two searches and merge results:
- `searchJiraIssuesUsingJql` with JQL `assignee = currentUser() AND statusCategory != Done`
  → `kind: "jira"`, `ref` = issue key (e.g. `DAS-6267`). Urgency from priority
  (Highest 7 / High 6 / Medium 4 / Low 2), `+1` if due-date is this week.
- `searchConfluenceUsingCql` with CQL `task.assignee = currentUser() AND task.status = "incomplete"`
  → `kind: "confluence"`, `ref: "C<n>"`. Urgency 5.
- Both searches: comment / mention searches (`comment ~ currentUser() AND updated >= -14d`
  and `mention = currentUser() AND lastModified >= -7d`) → urgency 2.

If the Atlassian MCP isn't connected, add a one-line footer:
`(Atlassian MCP not connected — Jira/Confluence skipped.)`

**Open questions / circle-back** — read durable memory files matching
`circle_back_*.md` in `$HOME/.claude/projects/<workspace-slug>/memory/` (the
slug is the absolute workspace path with `/` → `-` and a leading dash).
- `kind: "open_question"`, `ref: "Q<n>"`.
- Urgency: 3 if captured ≤ 7 days ago, 5 if older (forgotten penalty).
- Title: the first non-empty line of the file.

**Previous-session handoff** — read
`$HOME/.claude/projects/<workspace-slug>/whats-next-handoff.md` if it exists.
This is the file written by **step 8** of a previous READ-mode run; it
carries forward the *latent* context (small asides, decisions, in-flight
work) that hadn't graduated to PRs / tasks / Jira / memory before that
prior session ended.
- For each bullet under `## Latent asides` / `## In-flight (not yet tracked)`
  / `## Open / awaited (who/what)`:
  - `kind: "handoff"`, `ref: "H<n>"` (numbered in document order).
  - Urgency: 4 if the handoff was written ≤ 24h ago, **6 if older** (older
    handoff = more risk of being forgotten — bump it up).
  - Title: the bullet's text, trimmed to a sensible one-liner.
- Don't include items under `## Decisions made` as dashboard items — they're
  reference info, not action. Surface them only if the user explicitly asks
  "what did I decide?" via the closing-question prompt.
- Add a one-line footer: `(carried from handoff written <relative time ago>)`.

(Scanning the last ~20 turns of conversation for ungestured trigger phrases
is a stretch goal — punt if it adds noise. Step 8's handoff-write covers
most of what that scan would catch anyway.)

### 3. Re-sort and apply the budget

Sort the merged item list by score (descending), with ties broken by higher
urgency, then more recent `touched_at`, then alphabetical title.

Drop items with `score < 1.0`.

Apply the 80%-of-screen budget:
- ≤ 4 items per section.
- Sections render in this order: Pull Requests, Tasks, Scheduled, Atlassian,
  Local, Open questions, Carried over.
- Empty sections are dropped silently.
- If total items > what fits, append a trailing line:
  `(showing N of M items · /whats-next --all for full)`

### 4. Render the dashboard

Use this exact shape (emojis intentional — they're the user-facing visual
anchors). One trailing blank line between sections.

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

🎫 Atlassian (N items)
  DAS-6267  Pareto sweep …                          assignee=you · Medium · 3d
  C1        Confluence: standup notes               inline task · 7d

🌿 Local (N items)
  G1  uncommitted on feat/pareto-viewer-tab        3 files · likely WIP

❓ Open questions / circle-back (N captured)
  Q1  "revisit the copy-skip design"                18h ago · no date
  Q2  "check the bestseller frontier"               4h ago · TODAY

📋 Carried over (N items from previous handoff · written 14h ago)
  H1  "double-check the CA cert path on macOS"      latent aside
  H2  "Dennis pending: Members:Read org perm"       open / awaited

➤ Take action on #106? (admin-merge / wait for review / ping reviewer / drop)
```

Pick the closing-question verb from the top item's state:

| Top item state | Verb | Alternatives |
|---|---|---|
| PR green, unreviewed | admin-merge | wait for review / ping reviewer / drop |
| PR red, code suspect | investigate failures | rerun CI / drop |
| PR draft, green | flip to ready | drop |
| Task in_progress | continue | pause / drop |
| Memory due-today | act now | reschedule / drop |
| Jira High/Highest | look at the ticket | reassign / comment / drop |
| Confluence inline task | open the page | drop |
| Circle-back captured | revisit | reschedule / convert to task / drop |
| Carried-over handoff item | pick up | promote to task / drop |
| Git uncommitted | commit or stash | drop |

### 5. Empty-state outputs

- No items at all → render `Nothing pressing. You're caught up.` and stop.
- Single item → render only the top-line + closing question (no section
  headers).

### 6. Handling the reply

If the user picks the suggested verb, perform it where automatable (e.g. PR
admin-merge, `git stash`). Otherwise, after performing the action, offer the
next-highest item. If the user says `defer Q2` / `do #106` / `drop M1`,
resolve the reference against the most-recent rendered dashboard.

### 7. `--all` flag

If the slash command is invoked as `/whats-next --all`, bypass the per-section
4-item cap and render everything. Drop threshold (`score < 1.0`) still
applies.

### 8. Write a handoff for the next session

**Always overwrite** `$HOME/.claude/projects/<workspace-slug>/whats-next-handoff.md`
after rendering the dashboard. The latest invocation is canonical; previous
handoffs don't matter once a fresh one is written.

The point is to capture *latent* state from THIS session's conversation —
the stuff that wouldn't otherwise survive into the next session. Things
already tracked elsewhere (PRs in `gh`, issues in Jira, items in TaskList,
files under `memory/`) are re-discoverable next session via gather.py — no
need to duplicate them in the handoff.

**What to capture** (scan the current session's conversation for):

- **Latent asides** — small things mentioned in passing that didn't get
  promoted to a PR, task, memory file, or Jira item. Hans's specific concern:
  "the small tasks mentioned in passing". Example: *"and we should double-
  check the CA cert path on macOS later"*.
- **Decisions made** — substantive choices the user committed to this session
  that future-you should treat as settled (so we don't re-litigate them next
  time). Example: *"agreed: skel pattern uses /etc/appretio-skel/ with first-
  run-only semantics"*.
- **In-flight (not yet tracked)** — work that's started but isn't in a
  tracked system yet. Example: *"started drafting a script to verify the GH
  App token can read org members; abandoned mid-debug"*.
- **Open / awaited (who/what)** — things blocked on someone else's response,
  with the named person and what we're waiting on. Example: *"Dennis: add
  Members:Read org permission to the appretio-bot App"*.

**Format**:

```
---
written_at: <ISO 8601 UTC>
session_duration_approx: <best estimate, e.g. "4h">
top_focus: <one-line summary of what this session was mostly about>
---

# Carried forward

## Latent asides
- <bullet, one line each>

## Decisions made
- <bullet>

## In-flight (not yet tracked)
- <bullet>

## Open / awaited (who/what)
- <person>: <what we're waiting on>
```

**Rules**:

- **Empty sections are omitted** — don't render headers with no content.
- **If there's nothing worth carrying**, write just the frontmatter + one
  line `(nothing carried over — fresh slate)`.
- **Don't duplicate** items that gather.py would re-discover (open PRs, git
  state, Jira tickets, scheduled memory files). The handoff is for things
  those sources *won't* surface.
- **Keep each bullet to one line** — if it needs a paragraph, it probably
  belongs as a circle-back memory file (CAPTURE mode) or a task instead.
- **Bullets that the user has acted on this session** (the asides they
  resolved before the dashboard ran) should not appear — only carry forward
  what's *still* open.

After writing the file, end the response. Do **not** announce the handoff
file path in the dashboard — it's an invisible carry-forward mechanism, not
a user-facing artifact. If the user asks where it lives, tell them. Otherwise
stay quiet.

---

## CAPTURE mode

1. **Echo back** as: `Captured: "<paraphrase>"` — paraphrase the user's intent
   in 8-15 words, not a verbatim quote.
2. **Dating heuristic**:
   - Phrase contains `today`, `tomorrow`, `by <day>`, an ISO `YYYY-MM-DD`
     date, or a relative duration ("next week", "Friday") → **durable
     memory file**. Write it to
     `$HOME/.claude/projects/<workspace-slug>/memory/circle_back_<slug>.md`
     where `<slug>` is a short kebab-case keyword extraction. Include a
     YAML frontmatter block:

     ```
     ---
     captured_at: 2026-06-04T12:34:56Z
     target_date: 2026-06-11
     ---

     # <one-line title>

     <paraphrase>

     <any context Hans gave>
     ```

   - No date → use the **TaskCreate** tool to add an in-session task with
     the paraphrase as the title.
3. **Acknowledge**: `Captured as <ref>` where `<ref>` is `T<n>` (new task) or
   `Q<n>` (new memory file). For memory files, also paste the file path so
   Hans can `cmd+click` it.
4. **Do not** render the full dashboard. Return to whatever conversation was
   happening.

---

## Reference resolution

Refs are stable **within a single rendered dashboard**, not globally. When
the user types `do #106` / `drop M1` / `defer Q2`:

1. Resolve against the most-recent dashboard you rendered in this session.
2. PRs (`#<n>`) are also valid globally — `#106` always means GitHub PR 106.
3. If no recent dashboard exists, render one first.

## Footer

After every READ-mode render, if `errors[]` from gather.py is non-empty, add
a one-line footer:

```
(gather errors: prs=not authenticated · memory_scheduled=…)
```

Keep it under 100 chars; truncate per-collector messages if needed.
