---
name: session-retro
description: >
  Reflect on the current (or a named) Claude Code session and produce an honest
  retrospective: what went well, what went poorly, techniques worth keeping, and
  concrete suggestions (new skills, CLAUDE.md/memory edits, how we work together).
  Also grades token hygiene — where `/clear` or `/compact` would have saved money,
  with tips — and cross-checks against the whats-next handoff/memory/tasks to catch
  anything discussed but never captured ("are we forgetting stuff?"). Ends with a
  one-pager Artifact for review. Triggers: "retro", "retrospective", "what did we
  learn", "session summary", "lessons learned", "how did that session go",
  "postmortem", or the /retro slash command.
---

# session-retro

Turn a working session into durable lessons. This is a reflection tool, not a
status tool — for "what should I do next?" use **whats-next** instead. The two
are complementary: whats-next looks *forward* at the queue; session-retro looks
*backward* at how the work went and *sideways* at whether anything fell through
the cracks.

Run it when a chunk of work wraps up, before a `/clear`, or whenever the user
asks for a retro.

---

## Step 0 — Get the transcript digest (do this first, always)

Never read the raw `.jsonl` — it can be tens of MB. Run the bundled analyzer,
which does the deterministic accounting and prints a compact JSON digest:

```
<skill-dir>/scripts/analyze.py            # current workspace's newest session
<skill-dir>/scripts/analyze.py <path|id>  # a specific transcript
```

`<skill-dir>` is this skill's folder (`scripts/` is next to this SKILL.md).
`scripts/get-session.sh` resolves the transcript path the same way if you want
it separately (`get-session.sh` prints the path; `--dump` cats it).

The digest gives you: message/tool/error counts, wall-clock duration, per-tool
tally, capped tool-error snippets, compaction events, the ordered list of
**human messages** each annotated with `context_tokens` (prompt size at that
turn) and `growth_since_prev`, plus `peak_context` and `final_context`. That is
enough to write the whole retro — only re-read specific slices of the raw
transcript if a detail is genuinely missing.

If the digest has an `error` field (transcript not found), tell the user and
ask for a session id or path.

---

## Step 1 — Reconstruct the story (checks the classic-retro boxes)

From the digest's `human_messages` (in order) and the tool/error data, work out:

- **What we set out to do** and how the goal shifted (the human messages *are*
  the plot beats — mid-turn corrections like "actually, switch to X" are gold).
- **Problems hit and how they were resolved** — pair `tool_errors` with the
  human messages around them.
- **Key decisions** the user committed to (these are settled; don't re-litigate).
- **Techniques discovered** — the clever/reusable bits worth remembering.

Write in a plain, honest, conversational voice. Name specific commands, paths,
error strings, and numbers — vague retros are useless. **Be honest about
failures and dead ends**, including your own wasted iterations; that's where the
lessons live.

## Step 2 — What went well / what went poorly

Two crisp lists. "Well" = things to keep doing. "Poorly" = each item paired with
a concrete **lesson** ("next time, check the config section before editing" ),
not just a complaint. Include process friction, not only bugs — wrong turns,
things that took too many iterations, missed context.

## Step 3 — Token hygiene: where `/clear` and `/compact` would have helped 💸

Use the token trajectory in the digest. Guidance:

- **`peak_context` above ~120–150k, or context climbing across many turns on the
  *same* topic** → a `/compact` would have summarized the history and cut the
  per-turn cost (every turn re-bills the whole context, mostly as cache reads).
- **A human message that starts a genuinely *new, unrelated* task while
  `context_tokens` is already large** (big `growth_since_prev` behind it, then a
  topic switch) → a `/clear` there would have dropped the now-irrelevant history
  entirely. Point at the specific message number and its context size.
- **Long tool-heavy stretches** (`tool_calls_before` high) that ballooned context
  with output that was only needed momentarily → candidates for compacting after.

**Always give a few concrete, general tips** alongside the session-specific
findings, e.g.:
- `/clear` when you switch to an unrelated task — a fresh context is far cheaper
  than dragging the old one along.
- `/compact` when you're deep in one long task and the history is mostly settled
  — you keep the thread but shed the token weight.
- Front-load big pastes/logs into a file and reference it, rather than keeping
  them live in context.
- Prefer targeted reads over dumping whole large files.

Quantify when you can ("context peaked at 481k tokens around msg #17 — a
`/compact` there would've cut every later turn's cost").

## Step 4 — Are we forgetting anything? 🧵 (whats-next cross-check)

The retro's job here is to catch **latent** items — things said in passing,
promised, or half-finished that never got captured anywhere. Reuse whats-next's
four buckets:

- **Latent asides** — "we should double-check X later" that never became a task.
- **Decisions made** — settled choices future-you shouldn't re-litigate.
- **In-flight (not tracked)** — work started then abandoned mid-thread.
- **Open / awaited (who/what)** — blocked on someone; name them.

Cross-reference the session against what's already captured, so you only flag
*genuinely uncaptured* items:

1. Read the whats-next handoff if present:
   `$HOME/.claude/projects/<workspace-slug>/whats-next-handoff.md`
   (slug = workspace path with `/`→`-`).
2. Read durable memory: `$HOME/.claude/projects/<workspace-slug>/memory/`
   (both `MEMORY.md` and any `circle_back_*.md`).
3. Read the in-session TaskList (TaskList tool) if available.

Anything discussed in the session but absent from all three is a "forgetting"
risk — list it under the right bucket. Then **offer to capture it**: if the
whats-next skill is installed, recommend the exact CAPTURE phrasing (e.g.
`remind me to …`) or a `/whats-next` run; otherwise offer to write the memory
file or task yourself. Don't capture silently — surface and let the user choose.

## Step 5 — Suggestions 🚀

Forward-looking, specific, low-fluff:

- **New skills** — did a repeated manual dance this session deserve to be a
  skill? Name it and say what it'd automate.
- **CLAUDE.md / memory edits** — a preference or gotcha that recurred and should
  be written down so it's not re-derived next time. Propose the exact line.
- **How we work together** — collaboration friction worth changing: when to ask
  vs. proceed, how much to confirm before acting, output-format preferences,
  where approval gates belong. Frame as suggestions, not decrees.

Keep each suggestion to one or two lines with a clear "so that …".

---

## Step 6 — Publish the one-pager Artifact

Deliver the retro as a single reviewable page (that's the deliverable Hans
wants — "a one pager in claude for me to review").

1. **Load the `artifact-design` skill first** (required before building any
   Artifact) to calibrate the design.
2. Write the page to a file in the scratchpad dir, then publish with the
   **Artifact** tool. Favicon: `🪞`. Title like
   `Session Retro — <short topic> (<date>)`.
3. Use this section order (drop a section only if genuinely empty):

   1. **Header** — topic, date, and headline metrics from the digest (duration,
      human turns, tool calls, errors fixed, peak context).
   2. **TL;DR** — 2–3 sentences.
   3. **The journey** — the narrative from Step 1.
   4. **✅ What went well**
   5. **⚠️ What went poorly + lessons**
   6. **🧠 Techniques worth keeping**
   7. **💸 Token hygiene** — clear/compact findings + the general tips.
   8. **🧵 Are we forgetting anything?** — the whats-next cross-check buckets.
   9. **🚀 Suggestions** — new skills / CLAUDE.md / how-we-work.
   10. **Key takeaways** — 3–5 bullets.

Keep it scannable: metrics as a small stat strip, generous headings, short
bullets. It should read top-to-bottom in a minute or two.

After publishing, give the user the Artifact link and a 2–3 line spoken summary
(top win, top lesson, top token tip). Then ask whether to action any of the
"forgetting" items or suggestions — don't do it unprompted.

---

## Notes

- **Read-only by default.** This skill reflects and recommends. It does not
  write memory files, edit CLAUDE.md, or create tasks unless the user says yes.
- **Don't dump the raw transcript** into context or the Artifact. Work from the
  digest; quote only short, specific snippets.
- Scope is one session. For "what should I do next", defer to **whats-next**.
