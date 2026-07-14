# session-retro

A Claude Code skill that runs a retrospective on a working session and hands you
a reviewable one-pager. Where [`whats-next`](../whats-next) looks *forward* at
the queue, `session-retro` looks *backward* at how the work actually went — and
*sideways* at whether anything discussed quietly fell through the cracks.

It produces:

- **The journey** — goals, the corrections that reshaped them, problems hit and
  how they were fixed, and the key decisions you committed to.
- **What went well / what went poorly** — the second list pairs each item with a
  concrete lesson, not just a gripe.
- **🧠 Techniques worth keeping** — the reusable bits.
- **💸 Token hygiene** — points at the specific moments where a `/clear` or
  `/compact` would have saved tokens (using the per-turn context-size timeline),
  plus a few general tips every time.
- **🧵 Are we forgetting anything?** — cross-checks the session against the
  `whats-next` handoff, your durable memory, and the in-session TaskList, then
  flags latent asides / decisions / in-flight work / open-awaited items that
  never got captured, and offers to capture them.
- **🚀 Suggestions** — new skills worth building, CLAUDE.md/memory edits, and
  collaboration tweaks for how you and Claude work together.

Everything lands as a one-pager **Artifact** you can read in a minute.

## How it works

A deterministic analyzer (`scripts/analyze.py`) parses the session transcript
JSONL into a compact JSON digest — message/tool/error counts, wall-clock
duration, per-tool tally, tool-error snippets, compaction events, and the
ordered list of human messages annotated with the prompt (context) size at each
turn. The model reads that digest, **never the raw transcript** (which can be
tens of MB), then writes the retro. `scripts/get-session.sh` resolves the
transcript path for the current workspace (or a given session id / path).

## Installation

```bash
claude plugin install session-retro@hansharhoff/skills
```

## Usage

Slash command:

```
/retro
/retro <session-id-or-path>    # retro a different session than the current one
```

Or natural language: "let's do a retro", "what did we learn this session",
"how did that go", "session postmortem".

## Companion

Pairs with `whats-next`: run `session-retro` to reflect and catch dropped
threads, then `whats-next` to decide what to pick up next.

## Notes

- **Read-only by default** — it reflects and recommends; it won't write memory,
  edit CLAUDE.md, or create tasks unless you say yes.
- Scope is a single session.
