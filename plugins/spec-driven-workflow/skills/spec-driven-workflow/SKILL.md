---
name: spec-driven-workflow
description: "Iterate code against a spec living in a separate location (e.g. a pitches/design repo). Use this skill whenever the user asks to align code with the latest spec — common phrasings: 'let's iterate on our spec', 'pull the spec changes and align', 'run the spec-driven workflow', 'iterate', 'update against the latest spec'. The skill runs a five-step loop (refresh snapshot → code-drift check → diff + plan → implement + verify → commit + close-out summary) with bookkeeping in spec/snapshot/ and spec/working/. The closing summary lists what shipped, what's open / blocked / asks back to the user, and — when the iteration is fully complete — proposes forward-looking conversation starters."
---

# Spec-driven workflow

Iterate code against a spec maintained outside the code repo. The spec is the source of truth; the code repo holds a **snapshot** of the spec the code was last verified against, plus **working bookkeeping** (plan / status / blocked items / happy path). The diff between snapshot and live spec drives each iteration's work plan.

## When to use

Any user prompt that semantically asks to align the code with the latest spec. Examples (treat as equivalent):

- *"Let's iterate on our spec"* / *"Iterate on spec"* / *"Iterate"*
- *"Pull the spec changes and align"*
- *"Run the spec-driven workflow"*
- *"Update against the latest spec"*

If the user says any of these and `spec/workflow.md` exists in the active code repo, jump to **Step 0** below. If `spec/workflow.md` doesn't exist, run **Bootstrap** first.

## Bootstrap (first time only)

If the active repo has no `spec/` folder, set it up:

1. Confirm with the user **what the spec source is** — e.g. `pitches/shaping/<feature>/spec/` in a sibling repo, a Confluence URL, a Notion doc. The skill assumes the source is **a folder of markdown files** in another git repo. If it's something else, propose adapting the source-fetch step accordingly.
2. Create the folder layout:
   ```
   spec/
   ├── workflow.md              ← copy from this skill (or the v2 template below)
   ├── SNAPSHOT.md              ← bookkeeping (date + source commit + code commit)
   ├── snapshot/                ← verbatim copies from the spec source
   └── working/
       ├── HAPPY_PATH.md        ← agreed demo flow + per-component tests
       ├── STATUS.md            ← compliance status across the spec surface
       └── BLOCKED.md           ← items waiting on external dependencies
   ```
3. Run **first-time happy-path setup** with the user (see "Happy path discipline" below).
4. Run the first iteration of the loop normally (Step 0 onwards).

## Folder roles

| Folder / file | Role | Lifetime |
|---|---|---|
| `spec/workflow.md` | The loop definition (this skill's content, project-tailored) | Long-lived |
| `spec/SNAPSHOT.md` | Bookkeeping — which spec version the code is aligned with | Long-lived |
| `spec/snapshot/` | Verbatim copies from the spec source. **Don't hand-edit.** | Replaced each iteration |
| `spec/working/HAPPY_PATH.md` | Agreed demo flow + deterministic per-component tests | Long-lived; updated each iteration |
| `spec/working/STATUS.md` | Compliance status (per-section pass/fail/partial) | Long-lived; updated each iteration |
| `spec/working/BLOCKED.md` | Items waiting on external deps; rolls forward | Long-lived; cleared as deps land |
| `spec/working/CURRENT_PLAN.md` | The active iteration's plan | Created Step 1, deleted Step 3 |

## Auto mode vs interactive mode

Auto mode is about **tool permissions**, not workflow shortcuts:
- **Interactive mode (default)**: present the plan after Step 1 and **wait for `ok` / `reject` / `modify`** before Step 2. Substantive design questions encountered mid-implementation pause for confirmation.
- **Auto mode**: same flow, but tool calls execute without per-action approval prompts. **The Step 1 → Step 2 gate is still respected.**

If the user wants to skip the Step 1 approval gate explicitly, they say *"skip plan approval"* (or similar). Otherwise, present the plan and wait — auto mode does not imply silent execution of substantive changes.

## Prerequisites

Before starting any iteration, verify:
- **Authentication / SSO is fresh.** If the project depends on a credential that expires (AWS SSO, Auth0, etc.), check it's valid. If signs of expiry surface (auth-bound endpoints time out, `TokenRetrievalError`, etc.), **ask the user to refresh before Step 2**.
- **Dev servers are running** (if the project's verification step uses them).
- **`spec/working/HAPPY_PATH.md` exists.** If not, run the happy-path bootstrap.

## The loop

### Step 0 — Refresh the snapshot input

Replace the contents of `spec/snapshot/` with the current spec from the source.

```bash
# from the code-repo root, source is a sibling folder
rm -rf spec/snapshot/*
cp <spec-source>/*.md spec/snapshot/
```

**Don't touch** `spec/SNAPSHOT.md`, `spec/workflow.md`, or `spec/working/`. The previous spec content is recoverable via `git show HEAD:spec/snapshot/...` if needed.

Note the source commit hash; it'll go in the bookkeeping in Step 3.

### Step 0.5 — Code-drift check (the other direction)

Before reading the new spec → code direction, check the **code → spec** direction. Code may have changed since the last snapshot bump in ways the spec doesn't reflect — manual fixes, hot patches, demo polish, or implementation-discovered design that never round-tripped back.

```bash
# Find the last snapshot bump on this branch
LAST_BUMP=$(git log -1 --format=%H -- spec/SNAPSHOT.md)
# List code changes since then (adapt the path filter per project's languages)
git log --oneline "$LAST_BUMP..HEAD" -- '*.py' '*.ts' '*.tsx' | head -20
git diff "$LAST_BUMP..HEAD" --stat -- '*.py' '*.ts' '*.tsx' | tail -10
```

Read the changes through the lens: **does any of this represent design intent the spec doesn't capture?**

Categories:
- **Bug fixes / mechanical refactors** — typically no spec implication; ignore.
- **Demo polish (styling, copy, layout tweaks)** — usually no spec implication.
- **New behaviour / new fields / new flow steps** that the snapshot doesn't describe — **surface these to the user**. They are the candidates for spec amendment.
- **Removed behaviour** that the snapshot still describes — surface as a candidate for spec amendment.

If candidates exist, present them as a short list **before** producing the new-spec → code plan. The user decides per item:
- **"Amend the spec"** — note it for the next spec-source edit; flag the item as design-drift to fold back. The skill does **not** edit the spec source itself; it only documents the proposal in the iteration's notes.
- **"Revert the code"** — the change was unintended; back it out as part of this iteration.
- **"Park it"** — leave the code as-is for now and revisit; goes into `working/BLOCKED.md` with the rationale.

Only after the user resolves each drift candidate does Step 1 proceed.

### Step 1 — Diff + plan

```bash
git diff HEAD -- spec/snapshot/
```

Read every change. Group:
- **Substantive design changes** — new decisions, new endpoints, new schema columns, new flows, removed concepts.
- **Cosmetic / vocabulary** — naming harmonisations, anti-pattern cleanups.
- **Decisions log additions** — new entries in the decisions log.
- **Changelog entries** — log-only, usually a no-op for code.

For each substantive change:
- Identify the code surface it touches.
- Note whether it's blocked on an external dependency. If yes → goes into `working/BLOCKED.md`, not the plan.
- **Check whether it affects a generated artifact** (e.g. an `api.md` documenting the endpoint surface). If yes, the iteration's commit chain regenerates the artifact.

Persist the plan as `spec/working/CURRENT_PLAN.md`:

```markdown
# Iteration plan — <date>

Source: <repo>@<commit>
Code branch: <branch>

## Substantive changes
| # | Change | Code surface | Blocked? |
|---|---|---|---|
| 1 | ... | ... | no |
| 2 | ... | ... | yes — Q@<PERSON> |

## Cosmetic
- ...

## Verification
- Re-run `spec/working/HAPPY_PATH.md` after Step 2.
- New unit tests for items 1, 3.
- New integration / e2e assertion for item 1.
```

**Then: present the plan to the user.** In interactive mode, wait for `ok` / `reject` / `modify`. If the user said *"skip plan approval"* upfront, proceed directly.

### Step 2 — Implement and verify

For each approved plan item:
1. Make the code edit.
2. Run the relevant tests (unit / type-check / lint).
3. **Add a unit test that exercises the new behaviour** — small, deterministic, runs alongside the existing suite. The test makes the spec-vs-code alignment regression-safe.
4. **Re-run the happy path** in `spec/working/HAPPY_PATH.md` to confirm no regression.
5. Update `spec/working/STATUS.md` — mark each plan item completed / failed / partial.

**Spec-amendment escalation rule**: if implementation discovers a constraint that forces a generated artifact (e.g. `api.md`) or the design itself to deviate from what the snapshot says, **stop**. Write a short note describing the constraint and the proposed change, ask the user whether the spec should be amended. Don't silently let the code outpace the spec.

### Step 3 — Commit + push

Commit shape (one logical iteration per repo):
- **First commit**: snapshot bump + `CURRENT_PLAN.md` + `STATUS.md` updates. Message body cites the spec source's commit hash. Shows "where we're going" before any code lands.
- **Subsequent commits**: code changes, scoped per concern. Each message references which plan item it ships.
- **Final commit**: updates `SNAPSHOT.md` (date + source commit + final code commit), **deletes `working/CURRENT_PLAN.md`**, optionally updates `working/HAPPY_PATH.md` if the iteration suggests changes. `STATUS.md` and `BLOCKED.md` stay.

Push the branch.

When an iteration spans multiple code repos, each repo's first-commit message references the same source-spec commit hash for traceability.

### Step 4 — Close out

After Step 3's push, **the implementer produces a closing summary** so the user can pick up cleanly without scrolling back through the iteration's activity. The summary has three sections — the third is conditional on whether the iteration left anything open.

#### 1. What shipped

A short bullet list of the code changes, grouped by repo. Reference the snapshot bump (source-spec commit hash) and the final code commits per repo. Keep it tight — one line per change.

#### 2. What's still open / blocked / needs the user

This section has three sub-buckets — list whichever apply, omit empty buckets:

- **Blocked items**: every row from `working/BLOCKED.md`, **numbered** (B1, B2, ...) and given **at least two sentences of context**. The first sentence names the blocker; the second explains why the dep matters and what's parked behind it. The user should be able to skim the list and recall which thread is which without opening `BLOCKED.md`. Example:

  ```
  B1. Tradex lifecycle event log (Q@TRADEX). Range plan needs a per-(style, brand)
      event timestamp to dedup virtual carry-overs across years; currently using a
      simple set-difference stand-in. The Tradex team owns the schema and the
      lifecycle-owner UI; we wait on their schema flavour pick before wiring writes.
  ```

- **Partial items**: anything in `working/STATUS.md` flagged ⚠️ partial. Same numbering convention (P1, P2, ...) and same two-sentence floor — what shipped, what's missing, what completes it.
- **Asks back to the user** (A1, A2, ...): same numbering + two-sentence floor. Cover:
  - Decisions raised during Step 0.5 (code drift) or Step 2 (spec-amendment escalation) that the user paused on.
  - Verification gaps — things the implementer couldn't test (missing access, missing data, environment problem).
  - Proposed spec edits — anything the implementer thinks should land in the spec source on the next edit, with rationale.

End each ask with a clear prompt: *"Want me to ... ? [yes / no / something else]"*.

#### 3. Conversation starters (only when fully complete on the current spec)

If `working/STATUS.md` is all ✅ and `working/BLOCKED.md` is empty **and** there are no asks back to the user, replace section 2 with a short **conversation-starter** block. These are forward-looking suggestions to keep the project moving.

**Format**: numbered or lettered **one-liners** the user can pick by reference (e.g. "tell me more about 2"). Each line names the concern in <12 words; the implementer holds the detail until asked. Don't expand any line until the user picks it.

Three buckets — pick a few from each:

- **Spec improvements** (S1, S2, ...): gaps noticed while implementing — anti-patterns creeping in, missing decision-log entries, sections reading confusingly, cross-references that drifted.
- **Code quality improvements** (C1, C2, ...): brittle code, thin tests, off abstractions, dead code, refactors that would pay back soon.
- **Workflow / best-practice improvements** (W1, W2, ...): friction the implementer hit running the loop.

Example shape:

```
S1. Q@TRADEX has been open 2 iterations — escalate or design unilateral fallback.
S2. api.md regen could be a pitches-side pre-commit check.
C1. service.py is 1100+ lines — split by concern.
C2. No integration test for the GIS1 cascade against real Snowflake.
W1. Cross-repo iterations need a working/CROSS_REPO.md tracker.
```

User picks; the implementer expands the picked item with full context + a "want me to … ?" prompt; next iteration starts from there.

#### 4. (Conditional) Propose updates to `HAPPY_PATH.md`

If the iteration shipped behaviour-affecting changes — new flow steps, new components, new fields the planner sees, new cascade rules — propose a one-line update to `working/HAPPY_PATH.md`:
- A new demo step exercising freshly-shipped behaviour.
- A new sub-test locking in something the diff introduced.
- A revision to a step whose wording drifted from current spec wording.

User accepts / rejects; updates land in a follow-up commit if accepted.

**If the iteration shipped no behaviour changes** (a no-op iteration, or only mechanical / cosmetic edits), **stay silent on `HAPPY_PATH.md`** — don't propose anything. The "Last verified" row gets bumped only when the happy path was actually re-run and confirmed.

## Happy path discipline

`spec/working/HAPPY_PATH.md` is the agreed end-to-end demo flow + the deterministic tests that exercise each component along the way.

**First-time setup** (run during Bootstrap, or before the first iteration if missing):
1. The implementer drafts a happy path that walks through the spec's primary user journey.
2. The user reviews and edits.
3. For each component along the path, the implementer adds (or links to) a small **deterministic unit test** — fast, no external deps, runs alongside the regular suite. List the tests in `HAPPY_PATH.md` so the next iteration can re-run them as a checkpoint.
4. The file also tracks the last-verified date, source-spec commit, and outcome — appended to per iteration.

**Per-iteration**:
- Re-run the documented happy path after Step 2 (Playwright or equivalent live verification).
- Add a new unit test covering the spec changes the iteration shipped.
- After Step 3, propose `HAPPY_PATH.md` updates.

## STATUS.md — compliance tracking

Per-section / per-decision compliance rolling forward across iterations. Format:

```markdown
| Section | Status | Notes |
|---|---|---|
| §1 Purpose | ✅ | |
| §2 Data model | ⚠️ partial | <what's left> |
| §3.5 ... | ❌ | <why blocked, link to BLOCKED.md row> |
```

Maintained at the end of each Step 2.

## BLOCKED.md — external dependencies

Spec changes that can't be implemented now because they wait on something external. Each row carries forward across iterations until the dep lands. Format:

```markdown
| # | Spec change | Blocked on | What unblocks it | Notes |
|---|---|---|---|---|
| 1 | ... | Q@<PERSON> | ... | ... |
```

Clearing protocol:
1. When the dep lands, move the row from BLOCKED.md into the next iteration's `CURRENT_PLAN.md`.
2. Implement + verify per Step 2.
3. Delete the BLOCKED.md row in Step 3.

If a row sits >2 iterations, escalate — chase the dep or amend the spec.

## Anti-patterns

- **Touching `snapshot/` by hand.** Always go through Step 0. If something needs fixing, fix the live spec.
- **Skipping the Step 1 approval gate** without explicit user instruction. Auto mode is about tool permissions, not workflow shortcuts.
- **Letting generated artifacts outpace the spec.** Step 2's escalation rule exists to prevent this.
- **Bundle commits without a snapshot bump on the first commit.** The snapshot bump signals "we're aligning to this version".
- **Treating `CURRENT_PLAN.md` as long-lived documentation.** It's transient bookkeeping. Delete it on Step 3.

## Templates

If the project's `spec/workflow.md` doesn't exist yet, copy this skill's body into it and tailor the source path + verification commands.

For `SNAPSHOT.md`, `working/STATUS.md`, `working/BLOCKED.md`, `working/HAPPY_PATH.md`, see the example layout above — they're project-specific so adapt the columns and fields.
