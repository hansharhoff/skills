# spec-driven-workflow

A Claude Code skill that iterates code against a spec maintained in a separate location (e.g. a design / pitches repo, a Confluence doc folder, a shared markdown set).

## What it does

The spec is the source of truth. The code repo holds a **snapshot** of the spec the code was last verified against, plus **working bookkeeping**. The diff between the snapshot and the live spec drives each iteration. The loop:

1. **Step 0 — Refresh the snapshot.** Replace `spec/snapshot/` with the latest from the spec source.
2. **Step 0.5 — Code-drift check.** Look for non-spec-driven code changes since the last snapshot bump and surface them to the user (amend the spec, revert the code, or park it in `BLOCKED.md`).
3. **Step 1 — Diff + plan.** `git diff HEAD -- spec/snapshot/` produces the input. Group changes (substantive / cosmetic / decisions / changelog), persist as `spec/working/CURRENT_PLAN.md`, present to the user, wait for `ok / reject / modify` (auto mode is about tool permissions, not gate-skipping).
4. **Step 2 — Implement and verify.** One change at a time; tests pass; happy path in `spec/working/HAPPY_PATH.md` re-runs; `STATUS.md` gets updated. Spec-amendment escalation rule: if implementation forces a generated artifact to deviate from the snapshot, stop and ask.
5. **Step 3 — Commit + push.** Snapshot bump on the **first** commit so direction-of-travel is visible; final commit deletes `CURRENT_PLAN.md` and updates `SNAPSHOT.md`.
6. **Step 4 — Close out.** Closing summary: what shipped, what's open / blocked / asks back to the user, conversation starters when fully complete on the current spec, plus an offer to update `HAPPY_PATH.md`.

## Triggers

Any user prompt that semantically asks to align code with the latest spec:

- *"Let's iterate on our spec"* / *"Iterate"*
- *"Pull the spec changes and align"*
- *"Run the spec-driven workflow"*
- *"Update against the latest spec"*

## Folder layout (in the code repo)

```
spec/
├── workflow.md              ← project-tailored copy of the skill body
├── SNAPSHOT.md              ← bookkeeping (date + source commit + code commit)
├── snapshot/                ← verbatim copies from the spec source — don't hand-edit
└── working/
    ├── HAPPY_PATH.md        ← agreed demo flow + per-component deterministic tests
    ├── STATUS.md            ← compliance status across the spec surface
    ├── BLOCKED.md           ← items waiting on external dependencies
    └── CURRENT_PLAN.md      ← present only during an in-flight iteration
```

## When to use

Use this skill on projects where the design lives outside the code repo (a separate pitches repo, a design doc, a Confluence space) and the code is meant to track that design over time. The skill formalises:

- **What the code is built against** (snapshot + bookkeeping).
- **How the code stays in sync** (the loop).
- **What round-trips back to the spec** (the spec-amendment escalation rule).
- **How blocked work doesn't get lost** (`BLOCKED.md` carries forward).
- **How the closing summary lets the user pick up cleanly** (Step 4).

## When NOT to use

- The spec lives in the same repo as the code (no need for snapshot bookkeeping).
- The project has no spec — design lives in tickets / issues / chat (use a different workflow).
- The team has its own established design-to-code process that conflicts with this loop.
