---
name: spec-loop
description: "Iterate code against a spec (+optionally design pair) using the in-repo / pinned-hash model — spec and code share one git history, alignment is a commit hash, drift is `git diff`. Use when the user asks to align code with the latest spec, align spec/design/code, surface inconsistencies across the three, or surface candidates for moving spec-dir content out to cross-cutting categories. Trigger phrases: 'iterate on our spec', 'pull the spec changes and align', 'run the spec loop', 'run the spec-driven workflow', 'update against the latest spec', 'check spec vs design vs code', 'generalise this spec', 'check what can promote'."
---

# Spec loop

**At a glance.** Six-step loop: pin alignment → drift check → plan → implement+verify → commit → close out. State lives at `<deliverable-dir>/implementation/.sdd/`. First-time on a deliverable: see [Bootstrap](#bootstrap-first-time-only-per-deliverable).

Iterate code against a **spec** (+ optionally **design** pair) serving as the source of truth. This skill is for the **in-repo / pinned-hash model**: the spec source and the code live in **one git repository** and share one history. The loop pins a **last-aligned commit hash** rather than copying files, and detects movement by diffing that hash against `HEAD`. Each iteration's plan is driven by:

1. The deliverable-folder diff since the last alignment (`git diff <last-aligned>..HEAD -- <deliverable-dir>`) — new design intent → code. Covers `INTRO.md`, `SPEC.md`, and `implementation/` in one diff.
2. Code drift since the last alignment (`git diff <last-aligned>..HEAD -- <code-dir>`) — code changes that don't yet have a spec/design home.
3. Conflicts among spec, (optionally) design, and code that need an explicit decision.

The detail levels (spec / design / code) **are not expected to be in lock-step** — minor discrepancies are normal. Each iteration either resolves them or parks them as open questions in the spec source.

> Projects where the spec lives in a **separate repository** from the code (older multi-repo shape, with code repos cloned as gitignored siblings) should use a different skill — historically named `spec-driven-workflow`. This loop's mechanics assume one shared git history.

## Context

The skill assumes one git repository holding both spec sources and code. Paths are configurable via `.spec-loop.toml` at the repo root — see [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Repo configuration* section for the file shape. Where this document writes `<spec-dir>`, `<code-dir>`, etc., substitute the values from that config (defaults below).

- **Deliverable folder** — a deliverable spec lives at `<spec-dir>/domain/<deliverable>/`. The default `<spec-dir>` is `specs/`; override with `spec_dir` in `.spec-loop.toml`. Every deliverable folder carries exactly two top-level files plus one subfolder:
  - `INTRO.md` — domain context, cross-refs to other deliverables / `<spec-dir>/architecture/` / `<spec-dir>/conventions/` / `<code-dir>/AGENTS.md`. The on-ramp for a new reader (or LLM session).
  - `SPEC.md` — business-binding requirements; stakeholder-readable. **All HARD requirements live here** by virtue of being there.
  - `implementation/` — everything else (decisions, conventions, investigations, open questions, changelog, design, `.sdd/`, deliverable `CLAUDE.md`, opt-in generated artifacts).
- **Cross-cutting concerns** — `<spec-dir>/architecture/<topic>.md` and `<spec-dir>/conventions/<topic>.md` are **flat peer topic files** at the group root (no `spec/` subfolder, no three-tier split). They are read-only context for deliverables; cross-domain references go to these files. The group names (`architecture`, `conventions`) are the defaults — override via `cross_cutting_dirs` in `.spec-loop.toml` if the project uses different names.
- **Per-code-area guidelines** — `<code-dir>/AGENTS.md` and `<code-dir>/README.md` house code-area-scoped conventions (e.g. one per package/service in a polyrepo-style monorepo, or a single file in a flat repo). Deliverables consult these and cross-ref them where they apply (see [Generalisation mode](#generalisation-mode)). The list of `<code-dir>`s is configurable via `code_dirs` in `.spec-loop.toml`.
- **Design input** — `<spec-dir>/domain/<deliverable>/implementation/design/` is a **live, optional folder**. May hold output from a design tool **or** simple reference screenshots highlighting style / components / layout. Optional and often absent; a deliverable's `CLAUDE.md` may *additionally* name a *reference deliverable* (an existing module whose look-and-feel the new work should match). Step 4's visual review uses whatever `design/` holds plus any named reference deliverable.
- **Iteration state** — `<spec-dir>/domain/<deliverable>/implementation/.sdd/`, **committed in full** so it travels with the deliverable folder and is shared across machines / teammates. Holds the long-lived ledger (config + last-aligned hash + blocked + divergences), the happy path, and the most-recent iteration's plan. There is **no `snapshot/` copy folder** — alignment is a commit hash in `LEDGER.md`, not a verbatim copy of the spec.
- **Code** — one or more `<code-dir>` roots in the same repo. One working branch for the active workstream; the loop records the `last-aligned` commit hash, not the branch name. One PR for the workstream.
- **Pitch / brief** (optional) — when the project carries a Shape Up pitch (or analogous high-level brief) outside the spec tree, it's **read once at bootstrap** for background. The loop never edits the pitch, and pushes spec→pitch information only when the user explicitly asks.
- **`<deliverable>`** — the spec being iterated against. All lowercase `snake_case`. See [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Deliverable specs vs cross-cutting specs*.
- **Workstream** — a branch of work in the repo. *Not* a spec. Workstreams iterate against existing deliverables; one that touches multiple deliverables invokes the skill once per deliverable.

**Workspace layout (defaults — override via `.spec-loop.toml`):**

```
<repo-root>/                                       ← invocation point
├── .spec-loop.toml                                ← optional; configures spec_dir, code_dirs, cross_cutting_dirs
├── <spec-dir>/                                    ← default: specs/
│   ├── architecture/                              ← cross-cutting group (flat peer topic files)
│   │   ├── <topic>.md
│   │   └── …
│   ├── conventions/                               ← cross-cutting group (flat peer topic files)
│   │   └── …
│   └── domain/
│       └── <deliverable>/                         ← deliverable folder
│           ├── INTRO.md                           ← context, cross-refs (on-ramp)
│           ├── SPEC.md                            ← business-binding (HARD requirements)
│           └── implementation/                    ← everything else
│               ├── decisions.md                   ← AGREED dev decisions
│               ├── conventions.md                 ← INCIDENTAL choices (optional)
│               ├── investigations.md              ← research scratch (optional)
│               ├── changelog.md                   ← history (optional)
│               ├── open_questions.md              ← parked questions (user-curated)
│               ├── CLAUDE.md                      ← deliverable overlay (phases, reference deliverable, files)
│               ├── design/                        ← design output or reference screenshots (optional)
│               ├── .sdd/                          ← committed iteration state
│               │   ├── LEDGER.md
│               │   ├── HAPPY_PATH.md
│               │   └── CURRENT_PLAN.md
│               └── <generated artifacts>          ← opt-in per deliverable
├── <code-dir>/  …                                 ← one or more; AGENTS.md / README.md per area
└── ...
```

**Path resolution.** `<deliverable>` is the deliverable name the user types. The skill resolves it to `<spec-dir>/domain/<deliverable>/`. If the deliverable hasn't been provisioned at that path yet, the skill drops into Bootstrap to set it up.

For brevity, `<deliverable-dir>` below means the resolved `<spec-dir>/domain/<deliverable>/` path; `<impl-dir>` means `<deliverable-dir>/implementation/`; `<state-dir>` means `<impl-dir>/.sdd/`.

**Flat-mode opt-out.** For very small deliverables, the F-shape (`INTRO.md` + `SPEC.md` + `implementation/`) is overkill. Flat mode collapses the deliverable to a single `<spec-dir>/<deliverable>.md` file, with state at `<spec-dir>/.sdd/<deliverable>/` — no tier model, no per-deliverable folder. Promote to the F-shape when the deliverable outgrows a single file (multiple sections, design pair appears, decisions log starts mattering). Full rules in [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Flat-mode opt-out* section.

## When to use

Any user prompt that semantically asks to align code with the latest spec/design or surface inconsistencies. Treat as equivalent:

- *"Let's iterate on our spec"* / *"Iterate on spec"*
- *"Pull the spec changes and align"*
- *"Run the spec loop"* / *"Run the spec-driven workflow"*
- *"Update against the latest spec"*
- *"Check spec vs design vs code"*

Two narrower triggers that only run a sub-check:

- *"Check cross-branch drift on `<deliverable>`"* — runs Step 2's Check E only (skips A/B/C/D and the rest of the loop). Useful mid-flight when you want to know what another branch has changed without running a full iteration.
- *"Check merge readiness on `<deliverable>`"* — runs a one-shot `git diff origin/main..HEAD -- <deliverable-dir>` filtered to the normative + generated files. Surfaces final cross-main deltas before the workstream branch merges back. No code changes, no commits.

One **separate mode** that runs without the loop:

- *"Generalise this spec"* / *"check what can promote on `<deliverable>`"* — runs the [Generalisation mode](#generalisation-mode), which scans the deliverable's `implementation/` for content that's actually cross-cutting and surfaces promotion candidates. Read-only; the user applies any moves.

## How to invoke

1. Be at the **repo root**.
2. Make sure the workstream branch is checked out. The skill operates on whatever branch is currently checked out — it doesn't validate the branch name.
3. Say a trigger phrase, naming the spec inline if needed: *"iterate on my-deliverable's spec"*, *"iterate on architecture"*. If `<state-dir>/LEDGER.md` already exists, the skill picks up the pinned config (path filter, verification commands) and goes straight to **Step 1**.
4. **First time on a new spec** (no `.sdd/` for the deliverable yet) → run **Bootstrap** below.

**Multiple specs in flight (single workstream touching several).** Each spec has its own co-located `.sdd/`. The workstream's branch stays put across invocations; only the spec being iterated changes. Run the skill once per spec, in whatever order makes sense for the workstream's plan.

## Bootstrap (first time only, per deliverable)

If no `.sdd/` exists for the deliverable, set it up:

1. **Check the repo config.** If `.spec-loop.toml` doesn't exist (or the defaults don't fit the repo), create / edit it now. See [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Repo configuration* section for the file shape. Defaults: `spec_dir = "specs"`, `code_dirs = ["src"]`, `cross_cutting_dirs = ["architecture", "conventions"]`.
2. **Read any pitch / brief once** (if one exists — external doc named in the deliverable `CLAUDE.md`). This is background only: it informs the first iteration's understanding of intent. The loop will not edit the pitch afterwards.
3. Confirm with the user:
   - **`<deliverable>`** — the spec this iteration is for. All lowercase `snake_case`. See [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Deliverable specs vs cross-cutting specs*.
   - **Where the deliverable lives** — confirm the path `<spec-dir>/domain/<deliverable>/`. If the deliverable hasn't been created at that path yet, create the folder + the two top-level files (`INTRO.md`, `SPEC.md`) + the `implementation/` subfolder before continuing.
   - **Workstream branch** — the branch the code changes land on. If it doesn't exist yet, create one (`git checkout -b <branch-name>`; any name — the skill records the `last-aligned` commit hash, not the branch name).
   - **Competing branches (optional)** — other branches currently editing the same deliverable. Set when you want the agent to surface cross-branch drift (Step 2 Check E). Format in `LEDGER.md`'s Config section: `competing_branches: feature/foo feature/bar`. Leave unset when only this branch touches the deliverable.
4. Create the state layout (see **Folder roles** below for what each file holds):
   ```
   <deliverable-dir>/implementation/.sdd/
   ├── LEDGER.md                ← config + last-aligned hash + blocked + divergences
   ├── HAPPY_PATH.md            ← agreed demo flow + per-component deterministic tests
   └── (CURRENT_PLAN.md appears after the first iteration's Step 3)
   ```
   There is **no `snapshot/` folder** — the last-aligned commit hash in `LEDGER.md` is the alignment marker. `CURRENT_PLAN.md` appears in `.sdd/` after the first iteration's Step 3 and is overwritten at the start of each subsequent iteration's Step 3 (its previous content is preserved in git history).
5. **Install repo scripts** (once per repo, skip if already done). See [`REPO_SCRIPTS.md`](REPO_SCRIPTS.md) for the runner (`<spec-dir>/scripts/spec-loop.sh`) and the allowlist rule. This collapses the loop's recurring git calls behind one named command so a single permission rule covers them all.
6. Run **first-time happy-path setup** with the user (see "Happy path discipline" below).
7. Run the first iteration of the loop normally (Step 1 onwards).

## Folder roles

All paths are scoped to a single deliverable. Multiple deliverables = multiple deliverable folders, each independent.

| Folder / file | Role | Lifetime |
|---|---|---|
| `<deliverable-dir>/` | Deliverable folder (`<spec-dir>/domain/<deliverable>/`). Holds two top-level files + `implementation/`. | Long-lived |
| `<deliverable-dir>/INTRO.md` | Domain context; cross-refs to other deliverables, `<spec-dir>/architecture/`, `<spec-dir>/conventions/`, `<code-dir>/AGENTS.md`. The on-ramp for a new reader (or LLM session). | Long-lived |
| `<deliverable-dir>/SPEC.md` | Business-binding requirements; stakeholder-readable. The stakeholder signs off against this file. **All HARD requirements live here** by virtue of being there. May split into `SPEC/<NN>-<slug>.md` when large — see [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Splitting large specs*. | Long-lived |
| `<deliverable-dir>/implementation/` | Everything that isn't business-binding — decisions, conventions, research, design, state, opt-in artifacts. Shrinks over time as cross-cutting content moves to its existing home (see [Generalisation mode](#generalisation-mode)). | Long-lived |
| `<impl-dir>/decisions.md` | Letter-coded internal dev decisions with `[origin, date]` tags. AGREED tier. | Long-lived |
| `<impl-dir>/conventions.md` | Bullet-style incidental choices. Optional — create when needed. `(stable)` flag where change-resistance matters. | Long-lived; optional |
| `<impl-dir>/investigations.md`, `<impl-dir>/changelog.md`, … | Research notes, history, etc. Support files; not normative. The deliverable's `CLAUDE.md` lists which files exist. | Long-lived; optional |
| `<impl-dir>/open_questions.md` | Parked questions awaiting stakeholder input. **Skill never edits directly** — proposes wording in close-out. | Long-lived; user-curated |
| `<impl-dir>/CLAUDE.md` | Per-deliverable overlay: active phase numbering, `Q@<OWNER>` tags, actual file set, reference deliverable for visual review, opt-in generated-artifact specifics. | Long-lived |
| `<impl-dir>/design/` | **Optional, live design input** — design-tool output OR reference screenshots of style / components / layout. Used by Step 4 visual review alongside any reference deliverable named in the deliverable `CLAUDE.md`. | Long-lived; optional |
| `<impl-dir>/<artifact>.md` (e.g. an OpenAPI summary) | **Opt-in generated artifacts** — declared in the deliverable's `CLAUDE.md`. Derived from `SPEC.md` + `decisions.md`; regenerated in the same commit chain when those change. Most deliverables have none. | Long-lived; generated; opt-in |
| `<state-dir>/LEDGER.md` | Config (path filter, verification commands, optional `competing_branches`) + **last-aligned commit hash** + Blocked rows + Divergences rows | Long-lived |
| `<state-dir>/HAPPY_PATH.md` | Agreed demo flow + deterministic per-component tests + last-verified record | Long-lived; updated each iteration |
| `<state-dir>/CURRENT_PLAN.md` | Most-recent iteration's plan + per-item progress checkboxes. Doubles as session-resume marker (network outage, context clear, hand-off). | Overwritten at each Step 3; final state lives in git history |

(`<deliverable-dir>` = `<spec-dir>/domain/<deliverable>/`; `<impl-dir>` = `<deliverable-dir>/implementation/`; `<state-dir>` = `<impl-dir>/.sdd/`.)

**Cross-domain dependencies are links, never duplicated content.** When a deliverable's `SPEC.md` depends on another deliverable's requirements, link to that deliverable's `SPEC.md` (or to an external page). When it depends on a cross-cutting rule, link to `<spec-dir>/architecture/<topic>.md` / `<spec-dir>/conventions/<topic>.md` / `<code-dir>/AGENTS.md`. The link *is* the contract — see [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Cross-spec references*.

**The whole `.sdd/` is committed.** `LEDGER.md`, `HAPPY_PATH.md`, and `CURRENT_PLAN.md` all live in git — nothing under `.sdd/` is gitignored. The per-iteration churn on `CURRENT_PLAN.md` is accepted in exchange for full cross-machine / teammate continuity (one simple rule, all state shared).

**No snapshot folder.** Earlier multi-repo versions of this workflow kept verbatim copies of the spec under `snapshot/`. In the in-repo / pinned-hash model the spec and code share one history, so alignment is pinned as a commit hash in `LEDGER.md` and drift is read with `git diff`. There is nothing to hand-copy and nothing to hand-edit.

**Open questions.** Live in `<impl-dir>/open_questions.md`. Human-curated; the agent only proposes wording in close-out for the user to paste.

## Spec conventions

When proposing spec/design wording in Step 6 close-out, or when this skill is invoked directly from the spec source for editing, **read [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)** for notation, philosophy, EARS-style acceptance criteria, change-log rules, and anti-patterns. The loop steps below don't depend on that file — load it only when generating spec text.

Project-specific overlays (active phase numbering, `Q@<OWNER>` tags, the deliverable's actual file set, reference deliverable for visual review, opt-in generated-artifact specifics) live in `<impl-dir>/CLAUDE.md`. (`Q@<OWNER>` is the spec's open-question tag naming a person or team awaiting input — e.g. `Q@PLATFORM`. Full notation in [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md).)

> Verbose happy-path discipline (per-component deterministic tests, last-verified bookkeeping, etc.) is in the optional [`HAPPY_PATH_DISCIPLINE.md`](HAPPY_PATH_DISCIPLINE.md) sidecar — link it from your deliverable's `CLAUDE.md` to opt in.

## Pre-loop alignment vs Step 4 autonomy

The skill uses different interaction patterns at different stages — important for runs that span hours (e.g. overnight).

- **Pre-loop (Steps 1–3) — interactive.** The agent surfaces drift, conflicts, ambiguities, and plan items; the user resolves each. The Step 3 approval gate (full flow) waits on `ok` / `reject` / `modify` (opt-out: *"skip plan approval"*).
- **Step 4 — Implement and verify — unattended by design.** The agent runs without blocking on user input. Decision points (wiggum exhaustion, amendment escalation, visual review parks, logged assumptions) trigger **conservative auto-defaults** — typically *revert + log* — and the agent appends a structured A-ask to `CURRENT_PLAN.md`'s In-flight asks section, then continues with the next plan item. The user reviews everything in close-out.
- **Step 6 — Close out — interactive again.** The agent presents the structured close-out; the user replies to asks at their pace; next iteration's Step 1 picks up the resolutions.

"Auto mode" in Claude Code's tool-permission sense is orthogonal: it skips per-tool-call approval prompts but doesn't change the loop's interaction shape.

## Prerequisites

Before starting any iteration, verify:

- **Authentication / SSO is fresh.** If the project depends on a credential that expires (cloud SSO, identity provider tokens, etc.), check it's valid. If signs of expiry surface (auth-bound endpoints time out, token-retrieval errors, etc.), **ask the user to refresh before Step 4**.
- **Dev servers are running** (if the project's verification step uses them).
- **`<state-dir>/HAPPY_PATH.md` exists.** If not, run the happy-path bootstrap.

## Two flow modes

The loop runs in **full flow** by default. For trivial iterations the agent may opt into **quick flow**, which trims the planning and close-out ceremony while preserving every sync point.

### Quick-flow eligibility

The agent declares quick-flow at the end of Step 2 if **all** of these hold:

- The Step 1 deliverable-folder diff (`<last-aligned>..HEAD -- <deliverable-dir>`) is empty or trivially small (typo, vocabulary harmonisation, decision-log addition, change-log entry only — no new decisions, fields, flows, screens, or removed concepts).
- Step 2 surfaced no drift candidates and no conflicts.
- The user's request describes an alignment / pull / refresh — not a new feature, design change, or substantive code update.
- No multi-stage coordination beyond pulling and re-running the happy path.

If any criterion fails → run **full flow**.

### What quick-flow trims

| Step | Full flow | Quick flow |
|---|---|---|
| 1. Pin alignment | yes | yes |
| 2. Drift & conflict | yes | yes (one-line *"no drift"* output is fine) |
| 3. Plan | `CURRENT_PLAN.md` written + user approval gate | inline one-sentence plan in chat; no file written |
| 4. Implement + verify | yes (wiggum loop, self-verification) | yes (sync mechanics never skipped) |
| 5. Commit + alignment bump | yes | yes |
| 6. Close-out | structured 2a/2b summary | three lines: last-aligned hash + one-line summary + asks (if any) |

**The agent announces quick-flow before Step 3** (e.g. *"Running quick-flow because the spec diff is a one-section vocabulary harmonisation; full flow available on request."*). The user can veto.

### Escape valve back to full flow

During Step 4, if **any** of these happen:

- A test fails after the wiggum loop's retry budget is exhausted.
- The Step 4 spec-amendment escalation rule fires.
- The code surface widens beyond the one-sentence estimate.

→ stop, write `CURRENT_PLAN.md` with the discovered scope, surface the issue using the structured conflict template, resume from Step 3 in full flow. Quick-flow has no lock-in.

## The loop

Throughout the steps below, `<deliverable>` is a placeholder — substitute the active deliverable's name in actual commands and paths. `<last-aligned>` is the commit hash in `LEDGER.md`'s Alignment section.

### Step 1 — Pin alignment

Read the last-aligned commit hash from `<state-dir>/LEDGER.md`'s Alignment section. This is the baseline the iteration diffs against. There is nothing to copy.

```bash
# Run from the repo root — prints the last-aligned hash and current HEAD
<spec-dir>/scripts/spec-loop.sh status <deliverable>
```

The wrapper (see [`REPO_SCRIPTS.md`](REPO_SCRIPTS.md)) resolves the spec path, reads `last-aligned` from `LEDGER.md`, and prints both it and `HEAD` so you can see the span the iteration covers. Record `HEAD` — it becomes the new `last-aligned` in Step 5 once the iteration ships.

**Don't touch** `LEDGER.md`, `HAPPY_PATH.md`, or `CURRENT_PLAN.md` here. The previous iteration's alignment hash stays until Step 5 bumps it.

### Step 2 — Drift & conflict check

Before reading the spec → code direction, check the **other directions**. Pairwise checks:

**A. Code → spec drift.** Code may have changed since the last alignment in ways the spec doesn't reflect — manual fixes, hot patches, demo polish, or implementation-discovered design that never round-tripped back.

**B. Code → design drift.** Same idea, against the design surface (if the deliverable has one). Often correlated with A but not always.

For both A and B, diff the code paths since the last-aligned hash:

```bash
# Run from the repo root. <last-aligned> comes from LEDGER.md's Alignment section.
# <code-dir> here is each entry from `code_dirs` in .spec-loop.toml — loop over them.
git log  --oneline <last-aligned>..HEAD -- <code-dir>
git diff <last-aligned>..HEAD --stat   -- <code-dir>
```

Default: no path filter beyond the configured `<code-dir>` list — read the diff stat and ignore noise (lockfiles, generated files, docs that don't reflect spec changes) by judgment from the file paths. If a project benefits from strict scoping, set an optional `Path filter` line in `LEDGER.md`'s Config section (e.g. `*.py *.ts *.tsx`) and append it to the commands above.

Categorise each change:

- **Bug fixes / mechanical refactors / styling polish** — typically no spec or design implication; ignore.
- **New behaviour, new fields, new flow steps** that the spec doesn't describe — surface as a candidate for spec amendment, design amendment, or both.
- **Removed behaviour** that the spec still describes — surface as a candidate for spec/design amendment.

**Read `LEDGER.md`'s Divergences section first.** Anything listed there is a known intentional divergence — don't re-flag it. Only surface candidates that aren't already accounted for.

**C. Spec ↔ design consistency.** When the deliverable has a design pair, skim the spec diff (`git diff <last-aligned>..HEAD -- <deliverable-dir>`) and the design for places where one source describes a decision the other doesn't, or describes it differently. Skip if the deliverable has no `design/` folder.

**D. Ambiguity sweep.** Distinct from drift: scan the spec sections this iteration's plan items will touch (whether they changed in the spec diff or not) for cases where the spec is silent on a behaviour the implementation will have to decide. Typical shapes: undefined behaviour when two conditions co-occur, missing edge cases, unspecified ordering, vague quantifiers. Surface each one upfront with three options:

```
Ambiguity #N: <one-line title>
- Section: §X.Y
- Question: <what the spec doesn't say>
- Implementation will need to: <decide between A / B / ...>

Options:
  1. Clarify now — user picks; agent proposes spec wording for the user to apply.
  2. Pick interpretation X and log — agent proceeds with X; assumption goes in close-out as an `A` ask (see Step 4 "Assumptions log").
  3. Park — defer; skill proposes wording for <impl-dir>/open_questions.md.
```

The point is to make assumptions explicit *before* implementation, not bury them in code and surface at close-out. If the user says "you decide" repeatedly, that's fine — each silent decision gets logged per Step 4's assumptions-log rule.

**E. Cross-branch drift.** Skip if no `competing_branches` field in `LEDGER.md`'s Config section. Use case: multiple sub-deliveries are working against the same deliverable's spec in parallel branches, and you want to know what the other branches have changed before your iteration's plan goes stale.

For each branch listed, diff the deliverable folder between the current branch and that branch:

```bash
git fetch origin <competing-branch>
git diff origin/<competing-branch>..HEAD -- <deliverable-dir>
```

Categorise hunks:

- **Same section, different wording** → potential conflict. Surface using the cross-branch template below.
- **Different sections / additive only** → no immediate conflict; note in `CURRENT_PLAN.md`'s *Cross-branch awareness* section so merge-time isn't a surprise.
- **Identical wording on both sides** (rare race) → no action.

Surfacing format:

```
Cross-branch conflict #N: <one-line title>
- §<section> on this branch:        <quote>
- §<section> on <competing-branch>: <quote>

Options:
  1. Take this branch  — no change here; revisit when merging.
  2. Take other branch — propose adopting their wording (skill produces the spec edit).
  3. Merge             — propose unified wording for cross-branch sync; both implementers apply on their respective branches.
  4. Raise issue       — skill drafts a GitHub issue body describing the conflict and inviting discussion. User pastes into GitHub.
  5. Defer             — note in CURRENT_PLAN.md's Cross-branch awareness section; revisit before merge.
```

**Default lean is *defer*** unless the conflict directly affects this iteration's plan items — most cross-branch drift can wait until the user is ready to coordinate with the other implementer. Use *raise issue* when a discussion will unblock multiple branches; use *merge* when you and the other implementer are clearly converging on the same answer and just need to agree on wording.

**The "Raise issue" output** is a markdown body suitable for `gh issue create --body`:

```markdown
## Cross-branch spec drift: <one-line title>

`<deliverable>` §<section> has diverged between branches.

**This branch (`<this-branch>`)**:
> <quote>

**`<competing-branch>`**:
> <quote>

Both branches are actively iterating against this section. Suggested resolution: <merge proposal, or "discuss in this issue">.

cc <implementer-A> <implementer-B>
```

**Code in competing branches is ignored.** The agent does *not* read or diff code in `<competing-branch>` — only the deliverable folder. The whole point of the cross-branch model is that each implementer works against their own code locally; coordination happens at the spec level.

**Three-way conflict surfacing.** When a candidate touches more than one artifact (e.g. spec says X, design implies Y, code does Z), present it as a structured question:

```
Conflict #N: <one-line title>
- Spec says: <quote or reference>
- Design says: <quote or reference>
- Code does: <observed behaviour, file:line>

Options:
  1. Take spec   — update design + code to match.
  2. Take design — update spec + code to match (skill proposes spec wording for the user to apply).
  3. Take code   — update spec + design to match (skill proposes wording).
  4. Merge       — propose a hybrid; show the merged statement; user accepts/rejects.
  5. Park        — defer to a later phase. Skill proposes wording for
                   <impl-dir>/open_questions.md.
```

**Guidance for picking** (offer when the user looks unsure):

- **Take spec** when the spec is the most considered statement of intent — usually after a recent decision-log entry. Code/design likely got ahead by accident.
- **Take design** when the design exposes a constraint the spec didn't anticipate (UX detail, layout, interaction). Spec needs to absorb the design's judgement.
- **Take code** when the implementation discovered a constraint that retroactively invalidates the spec/design (data shape, performance, library limit). Almost always pair with a spec/design update.
- **Merge** when each side carries part of the answer — common for naming, sequencing, or vocabulary harmonisation.
- **Park** when the conflict is real but resolving it now isn't worth the iteration cost — a later deliverable will clarify, or it depends on a decision the user isn't ready to make. Parked questions live in `<impl-dir>/open_questions.md`.

**Captured preferences inform the recommendation.** Before offering an option, check `CURRENT_PLAN.md`'s *Session preferences and new criteria* section. If a preference (P1, P2, …) bears on this conflict, lead with the matching option and reference the preference inline. The user can still pick any of the five — the preference just shifts the salience.

**Per-file defaults.** The deliverable's normative files carry different binding strengths — see [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Normative files* section. The agent shifts its default suggestion based on which file the spec side of the conflict lives in:

| File the conflict touches | Default lean | A-ask shape |
|---|---|---|
| `SPEC.md` (HARD requirement) | **Take spec.** Code drift here is loud. | Prefix the question with `[HARD]`. "Take code" is presented but discouraged — almost always means we misread the spec, not the spec is wrong. |
| `implementation/decisions.md` (AGREED) | Standard five-option flow. | As today — no prefix, no bias. |
| `implementation/conventions.md` (INCIDENTAL, no flag) | **Take code, sync the convention.** | Lower-noise; default offered is *"update the convention to match"*. |
| `implementation/conventions.md` entry with `(stable)` flag | Standard five-option flow. | Treat as `decisions.md` — the flag exists to upgrade an incidental entry to "don't drift without thinking." |
| `INTRO.md` (context, cross-refs) | Standard five-option flow. | Drift here usually means a cross-ref pointing at the wrong section/file. "Take code" is rare — INTRO doesn't make claims about behaviour. |
| Opt-in generated artifact (when declared by the deliverable's `CLAUDE.md`) | Regenerate from the normative files; never hand-edit to match code. | If code forces the artifact to diverge → Step 4 amendment escalation against the *normative* file it derives from. |

The default is a *lean*, not a lock — the user can pick any option regardless. The lean exists so the question is faster to answer when the obvious resolution holds.

Each parked or "amend the spec/design" outcome is a **proposal** — the skill writes the suggested wording into the close-out summary; the user applies the edit to the spec/design source on the next pass. The skill never edits the spec or design source itself.

Step 3 only proceeds after the user resolves each surfaced item (or the user says *"rest of these later, plan around them"*).

**Quick-flow check.** At the end of Step 2, evaluate quick-flow eligibility (see "Two flow modes"). If eligible, announce the choice and proceed in quick-flow shape. Otherwise full flow.

### Step 3 — Diff + plan

```bash
<spec-dir>/scripts/spec-loop.sh diff <deliverable>     # git diff <last-aligned>..HEAD -- <deliverable-dir>
```

Read every change. Group:

- **Substantive design changes (spec or design source)** — new decisions, new endpoints, new schema columns, new flows, new screens, removed concepts. New HARD requirements (`SPEC.md` body changes) belong here too.
- **Cosmetic / vocabulary** — naming harmonisations, anti-pattern cleanups.
- **Decisions / conventions log additions** — new entries in `implementation/decisions.md` or `implementation/conventions.md`.
- **Changelog entries** — log-only, usually a no-op for code. Cross-file tier moves (e.g. promotion to `SPEC.md`) get a changelog entry — see [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Cross-file moves* section.
- **Cross-ref updates in `INTRO.md`** — pointers added or rerouted. Usually no code impact, but check whether the referenced source actually says what `INTRO.md` claims.

For each substantive change:

- Identify the code surface it touches (which `<code-dir>`).
- Note whether it's blocked on an external dependency. If yes → goes into `LEDGER.md`'s Blocked section, not the plan.
- **Check whether it affects a generated artifact.** Generated artifacts are opt-in per deliverable (declared in `<impl-dir>/CLAUDE.md`); skip this check if the deliverable doesn't use any. If one is in play, the iteration's commit chain regenerates it.

Persist the plan as `<state-dir>/CURRENT_PLAN.md`, **fully overwriting any previous iteration's content** (the previous iteration's final state is in git history):

```markdown
# Iteration plan — <date>

Last-aligned: <hash>          ← commit at the start of this iteration (from LEDGER.md)
HEAD at start: <hash>

Status legend: `[ ]` todo · `[x]` done · `[~]` partial · `[!]` failed

## Substantive changes
| # | Status | Change | Source (spec/design) | Code surface (dir:path) | Blocked? |
|---|---|---|---|---|---|
| 1 | [ ] | ... | spec | <code-dir>/.../route.py | no |
| 2 | [ ] | ... | design | <code-dir>/.../Planner.tsx | yes — Q@<OWNER> |

## Conflicts to resolve this iteration
| # | Conflict | Resolution chosen | Action |
|---|---|---|---|
| C1 | spec says X, design says Y | take design | update spec source proposed in close-out; code aligns to Y |

## Parked (proposed for implementation/open_questions.md)
- Q1. <question wording the skill proposes the user copy into open_questions.md>

## Cosmetic
- ...

## Verification
- Re-run `<state-dir>/HAPPY_PATH.md` after Step 4.
- New unit tests for items 1, 3.
- New integration / e2e assertion for item 1.

## In-flight asks (accumulating during Step 4)

A-asks the agent writes here in real-time when it hits a decision point during Step 4 (wiggum exhaustion, amendment escalation, visual-review parks, etc.). Step 6's close-out 2a reads this section. The agent does not block waiting for user input on these — it picks a conservative default, logs the ask, and continues.

Each ask names its **file-of-origin** in parentheses so close-out preserves the tier signal (HARD asks are loud; conventions asks are cheap). Use the file the amendment would touch on the spec side; omit if the ask has no spec-side anchor (e.g. a pure verification gap).

- A1. (file: SPEC.md) <ask wording, two-sentence floor>
- A2. (file: implementation/decisions.md) <ask wording>
- A3. (file: implementation/conventions.md, `(stable)`) <ask wording>

## Cross-branch awareness

Only populated when `competing_branches` is set in `LEDGER.md`. Step 2's Check E records cross-branch hunks here when the user picks *defer* (option 5). Pre-merge sanity check (*"check merge readiness on <deliverable>"*) re-reads this section to remind the user what's still open.

- X1. §<section>: this branch has <wording>; `<competing-branch>` has <wording>. Deferred from iteration <date>. Revisit before merge.

## Session preferences and new criteria

Captured throughout the iteration when the user expresses an opinion, preference, or new criterion that should influence resolution decisions in this iteration **and** potentially feed back to the spec/design/conventions. The agent appends here in real-time during Steps 2 / 3 / 4. Step 6 close-out re-emits these as proposed spec / design / conventions edits.

**When to capture:**

- User states a preference: *"I prefer X"*, *"always X in this case"*, *"stop doing Y"*.
- User adds a new criterion: *"must also support mobile"*, *"should respond under 200 ms"*.
- User validates a non-obvious choice: *"yes, that was the right call"* (preserves the validated approach so the agent doesn't drift away on the next iteration).
- User redirects mid-flight: *"no, do Z instead"*.

**Format**: one bullet per preference. Lead with the wording, then a `(where it was raised)` parenthetical so close-out can route it to the right tier file.

- P1. Prefer idempotent saves for all writeback endpoints. *(raised during Step 2, conflict C1 — proposed for implementation/decisions.md)*
- P2. Mobile support is a new acceptance criterion for the planner. *(raised during Step 3 planning — proposed for SPEC.md §3)*
- P3. Don't auto-merge conflicts with three or more sources. *(redirect during Step 4 — proposed for implementation/conventions.md, `(stable)`)*

**The 5-option flow reads from this section.** When the agent surfaces a conflict in Step 2, it checks Session preferences first: if a preference bears on the conflict, the agent leads with the matching option and references the preference inline (e.g. *"Preference P1 suggests Take spec — the spec wording is already idempotent"*). The user can still pick any of the five options.
```

`CURRENT_PLAN.md` doubles as the agent's **session-resume marker** — checkboxes flip during Step 4 so a fresh agent (network outage, context clear, hand-off) can read this file and resume from where the previous agent stopped.

**Then: present the plan to the user and wait for `ok` / `reject` / `modify` before proceeding to Step 4.** This gate is respected in both interactive and auto mode — auto mode skips per-tool-call approval prompts, not workflow gates. The user can opt out explicitly by saying *"skip plan approval"* (or similar) upfront; otherwise, present the plan and wait.

(Quick flow: skip the file; show a one-sentence inline plan in chat. The escape valve in "Two flow modes" describes when to fall back to writing `CURRENT_PLAN.md` mid-iteration.)

### Step 4 — Implement and verify

For each approved plan item:

1. Make the code edit (in the relevant `<code-dir>`).
2. Run the relevant tests (unit / type-check / lint).
3. **Add a unit test that exercises the new behaviour** — small, deterministic, runs alongside the existing suite. Where the spec uses EARS-style acceptance criteria (see [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)), one EARS line ≈ one test name.
4. **Re-run the happy path** in `<state-dir>/HAPPY_PATH.md` to confirm no regression. The happy path may exercise multiple code areas — make sure all relevant dev servers are up.
5. **Regenerate any opt-in spec-derived artifacts** this item touches (declared in `<impl-dir>/CLAUDE.md`; e.g. an OpenAPI summary, schema dump, JSON sketch). The artifact's "Last regenerated" stamp should match the closing commit. See [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s Generated artifacts section. Most deliverables have none — skip.
6. Flip the item's checkbox in `CURRENT_PLAN.md` — but **only after self-verification** (see below).

#### Wiggum loop — when verification fails

If any of step 2–4 above surfaces a failure (test fails, type check breaks, happy path regresses):

- **Retry budget**: up to **5 attempts** on the same item. Default; user can override (e.g. *"budget 2"*, *"escalate immediately on failure"*).
- Per attempt: read the failure carefully, attempt a targeted fix. If the failure suggests a spec misinterpretation, re-read the relevant spec section before the next attempt. If it suggests a missing test fixture or environmental gap, fix that and retry.
- **Don't keep trying past the budget.** Spinning is worse than logging. After exhaustion: **revert the item's edits**, mark the item `[!]` failed in `CURRENT_PLAN.md`, and **append a structured A-ask to `CURRENT_PLAN.md`'s In-flight asks section** (3–4 lines: what was tried, what the failure looked like, possible next directions, *"need user steer"*). Continue with the next plan item. **Do not block waiting for user input** — the user reviews the ask in close-out.

#### Self-verification — concrete evidence before flipping a checkbox

Before marking any plan item `[x]`, the agent must produce concrete evidence:

- The new test exists in source (`grep` finds the test name) and is picked up by the project's test runner — whatever it is (pytest's collection output, `jest --listTests`, `go test -list`, etc.).
- Tests pass (exit code 0; quote the relevant tail lines).
- The happy path ran end-to-end without regression for this item. (`HAPPY_PATH.md`'s "Last verified" date isn't bumped per-item — that's a per-iteration update gated by the Visual review sub-section.)
- (If the deliverable uses opt-in generated artifacts) any artifact this item touches has been regenerated and its "Last regenerated" stamp updated.

**Don't flip on the agent's own claim** ("I added the test") — flip only after the evidence check passes. For partial completions (`[~]`), say in one line *what's missing* alongside the row. For failures (`[!]`), one line on *why* and link to the escalation note.

#### Assumptions log — surface silent interpretations

If implementation requires picking among interpretations of an ambiguous spec section (no conflict, no escalation — the spec is just silent), the agent must **record the assumption** as an `A` ask in close-out rather than burying the decision in code. This catches the cases that didn't reach Step 2's ambiguity sweep — e.g. ambiguity discovered mid-implementation when reading a section in detail.

Format:

```
A2. Assumption — §4.5 ambiguity on (X, Y) co-occurrence

    Spec doesn't specify. I picked: when both occur, X wins.
    Manifested in: <code-dir>/.../resolver.py:42, test_resolver_xy.py.
    To remove the ambiguity, propose appending to §4.5:

      WHEN both X and Y occur in the same save THE SYSTEM SHALL prefer X.

    To pick the other interpretation, swap "prefer X" → "prefer Y" and
    flip the assertion in test_resolver_xy.py.
```

Three required parts: (a) the ambiguity, (b) the chosen interpretation, (c) where it manifests in code/tests. Plus proposed spec wording the user can paste to remove the ambiguity in either direction. Don't merge multiple assumptions into one ask — one row per assumption so the user can accept/flip them independently.

#### Spec/design-amendment escalation rule

If implementation discovers a constraint that forces an opt-in generated artifact or the design itself to deviate from what the spec says: **revert the offending change** (preserves spec / code consistency — this is the most conservative default), mark the item `[!]` failed, and **append a structured A-ask to `CURRENT_PLAN.md`'s In-flight asks section** describing the constraint, the proposed amendment wording, and the three possible decisions for the user to pick in the morning:

1. **Accept the amendment** — the user updates the spec or design source on the next edit; the next iteration's Step 1 picks up the new wording and the code change re-lands cleanly.
2. **Confirm revert** — the constraint is wrong or the workaround isn't yet warranted; the auto-revert stands.
3. **Diverge** — the user accepts that the code lives differently from the spec/design, on purpose. The user adds a row to `LEDGER.md`'s Divergences section (review trigger + reasoning); the code change re-lands in a follow-up iteration. Use sparingly — divergences are debt.

**Per-file framing of the A-ask.** The auto-revert is always the conservative default, but the ask's wording shifts based on which spec file the amendment would touch (see [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Normative files* section):

- **`SPEC.md` (HARD)** — A-ask prefixed `[HARD]`. Wording leads with *"This is a HARD requirement; an amendment here probably means stakeholder re-alignment, not a dev-side fix."* Outcome 3 (diverge) is explicitly flagged as load-bearing tech debt.
- **`implementation/decisions.md` (AGREED)** — standard three-outcome framing as above. No prefix.
- **`implementation/conventions.md` (INCIDENTAL, no flag)** — strong bias toward outcome 1 (accept the amendment). Wording leads with *"Convention entry was incidental; the code's choice is likely fine to sync to."* Outcome 2 (confirm revert) gets a brief note when the user might still want to keep the original wording.
- **`implementation/conventions.md` with `(stable)` flag** — treat as `decisions.md` for framing. The flag exists to upgrade an incidental entry to "don't drift without thinking."

**Do not block waiting for user input.** Continue with the next plan item; the user picks the outcome from close-out. Don't silently let the code outpace the spec or design — the auto-revert is what prevents that.

#### Visual review — when the iteration touched UI

A per-iteration check (run once after all plan items are complete, before Step 5). **Skip** if:

- The iteration shipped no user-visible UI changes (backend-only, infra-only, doc-only).
- The deliverable has neither a `design/` reference nor a named reference deliverable to compare against.

**Reference source — `design/` and/or a reference deliverable.** The `design/` folder is a live optional input that may hold **design-tool output or reference screenshots** of style / components / layout. A deliverable's `CLAUDE.md` may *additionally* name a **reference deliverable** — an existing one whose look-and-feel the new work should match. Use whichever is available; both are first-class comparison surfaces:

1. **Capture current state.** Screenshot each page this iteration touched (Playwright or equivalent). For multi-step flows, screenshot each step.
2. **Capture references.** The relevant `design/` files (design-tool output or reference screenshots, if present), and/or the named reference deliverable's equivalent screens (open the running reference deliverable and screenshot the analogous surfaces). If the deliverable `CLAUDE.md` names both a reference deliverable and a convention page, capture both.
3. **Compare against a structured checklist:**
   - **Layout** — placement of regions, overall composition, hierarchy.
   - **Controls** — the right inputs / buttons present in the right places.
   - **Missing elements** — anything in the reference absent from the rendered page.
   - **Theme / shading / typography** — colors, fonts, consistency with the reference and with the broader app.
   - **Sizing / density** — proportions, spacing.
4. **Iterate** until the checklist is clean or each remaining gap is parked. Per gap, pick from:
   - **Take reference** — adjust the code to match the design / reference deliverable.
   - **Take code** — propose a design or spec edit (close-out ask).
   - **Park** — add to `open_questions.md` proposal.
   - **Close-enough** — the gap is real but small enough not to chase given the deliverable's stance threshold (close-out note, no park entry needed).

   **Iteration model.** Visual refinement is genuinely iterative — closing a layout / theming gap often takes many small attempts. Step 4 runs unattended; the agent doesn't block waiting for user input on visual gaps:
   - **Per-gap soft cap of ~5 attempts.** After 5 attempts that haven't closed a gap, **auto-park** with a structured A-ask appended to `CURRENT_PLAN.md`'s In-flight asks section (what was tried, what still differs, the gap entry). Continue with the next gap.
   - **"Close-enough" as agent judgment.** A small gap that the deliverable's stance threshold marks as below-the-line can be flagged close-enough rather than parked — still surfaced in close-out, just without a park entry. Use sparingly; default to park if uncertain.
   - **Narrate progress within a batch.** Short status notes ("attempt 3: column width still ~10px off") leave a readable trail, and let a user who happens to be in the chat interrupt at any point.
   - **Amendment escalation** if a gap reveals a constraint forcing a spec / design amendment — Step 4's amendment rule applies (auto-revert + log, same pattern).
5. **Only then** update `HAPPY_PATH.md`'s "Last verified" row.

**Screenshot vs. DOM probe.** Step 1's screenshot tells you what the page looks like; it does not tell you whether the rendered geometry agrees with a measurable claim ("edge-to-edge", "sticky bottom", "no scrollbar", "centered", "X pixels of gap"). Pair every measurable assertion with a `getBoundingClientRect()` + scroll-dimension probe in the **same browser-tool batch as the screenshot**:

```js
const el = document.querySelector(<selector>).getBoundingClientRect();
({
  hScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  vScroll: document.documentElement.scrollHeight - document.documentElement.clientHeight,
  viewport: window.innerWidth + "x" + window.innerHeight,
  rect: { left: el.left, right: el.right, bottom: el.bottom, width: el.width, height: el.height },
  dpr: window.devicePixelRatio
})
```

Reject the work if any value disagrees with the expectation (`hScroll > 0` when no scroll is expected, `rect.right < viewport.width` for an element claimed edge-to-edge, etc.) — iterate before declaring done. Screenshots alone mislead in two specific ways: browser-tool overlays (extension indicators, devtools chrome) can obscure the exact region being verified, and a fix that looks right at the agent's local viewport / DPR can fail at the user's viewport / DPR. Numeric assertions are independent of both.

**Threshold modulation.** The deliverable's `CLAUDE.md` "Implementation stance" sets how strict the checklist is. A *new module composed from existing primitives* should be strict on layout / controls / missing elements but lenient on pixel-level theming (existing primitives bring their own). A *new shared component* would invert this — pixel match is the contract. Same checklist categories, different thresholds.

### Step 5 — Commit + push

In the in-repo model, spec + state + code all live in one history. A single iteration is typically a small chain of commits on the workstream branch. Default to **opening + code + closing** commits in one branch:

**1. Opening commit.** Stages:

- The freshly-overwritten `<state-dir>/CURRENT_PLAN.md` (with checkboxes initially `[ ]`).

Message body cites the iteration date + the `last-aligned` baseline. Shows "where we're going" before any code lands. (Optional — for a tiny iteration the plan can land in the closing commit instead.)

**2. Code commits.** Code changes in `<code-dir>`, scoped per concern. Each message references which plan item it ships. Pick the order based on dependencies (typically backend before frontend if the frontend consumes a contract this iteration introduces). If the deliverable opted into a generated artifact, regenerated copies land in the same commit as the change that drove them.

`CURRENT_PLAN.md` checkbox updates from Step 4 happen on disk as items complete; they land in the closing commit. (For long iterations, an intermediate `CURRENT_PLAN.md` checkpoint commit is fine as a recovery point, but not required.)

**3. Closing commit.** Stages:

- `<state-dir>/LEDGER.md`'s **Alignment** section updated: date + the new `last-aligned` hash = the iteration's `HEAD` *before* this closing commit (i.e. the last code/spec commit). **Blocked** / **Divergences** sections updated if rows changed this iteration.
- The final state of `<state-dir>/CURRENT_PLAN.md` (all checkboxes flipped to their final values: `[x]` / `[~]` / `[!]`). The file is **not deleted** — it stays as the most-recent plan and is overwritten by the next iteration's Step 3. The trail of completed iterations lives in git history (`git log -p <state-dir>/CURRENT_PLAN.md`).

`HAPPY_PATH.md` updates, if any, land in a follow-up commit per Step 6.

**Push.** Push the workstream branch.

#### Abandoned iteration

If Step 4 ends with **no plan items shipped** — e.g. the user picked *"reject + revert"* on the only load-bearing item, wiggum budgets exhausted across the board, or the user said *"abandon, this isn't right"*:

1. **No commits.** No opening, code, or closing commits. The alignment bump signals *"we aligned to this version"*; without shipping, no alignment occurred, so the bookkeeping shouldn't claim otherwise.
2. **Restore the working tree.** Discard the uncommitted `CURRENT_PLAN.md` and revert any uncommitted code edits. **Confirm with the user before running destructive ops** — list what will be discarded, wait for explicit approval (this is the standard rule for any irreversible action, not just abandon).
3. **Close-out is one paragraph**: *"Iteration abandoned because <reason>. No alignment was bumped. Working tree is back to its pre-iteration state."* Plus any asks back to the user (e.g. proposed spec edits the iteration surfaced even though it didn't ship).
4. **Next iteration starts fresh** — Step 1 re-reads the (unchanged) `last-aligned` hash and diffs against the now-likely-changed `HEAD`.

Partial-success (some items `[x]`, others `[~]` / `[!]`) is **not** abandonment — close out normally; the 2a sub-buckets cover it. Abandonment is the all-or-nothing case where committing would be a lie.

### Step 6 — Close out

After Step 5's push, **the implementer produces a closing summary** so the user can pick up cleanly without scrolling back through the iteration's activity.

(Quick flow: the close-out is three lines — last-aligned hash, one-sentence summary, any asks. Skip the structure below.)

#### 1. What shipped

A short bullet list of the code changes, grouped by code area. Reference the new `last-aligned` hash (the alignment point) and the final commit hashes. Keep it tight — one line per change.

#### 2a. What's still open / blocked / needs the user

Use **2a** when the iteration left work behind — anything in `LEDGER.md`'s Blocked section, anything `[~]` partial or `[!]` failed in `CURRENT_PLAN.md`, or any asks back to the user. Use **2b** instead when the deliverable is fully aligned. Never both.

Sub-buckets under 2a — list whichever apply, omit empty ones:

- **Blocked items** (B1, B2, ...): every row from `LEDGER.md`'s Blocked section, numbered and given **at least two sentences of context**. The first sentence names the blocker; the second explains why the dep matters and what's parked behind it. Example:

  ```
  B1. Event log schema (Q@PLATFORM). The planner needs a per-entity event
      timestamp to dedup virtual records across cycles; currently using a
      simple set-difference stand-in. The platform team owns the schema and
      the lifecycle-owner UI; we wait on their schema flavour pick before
      wiring writes.
  ```

- **Partial / failed items** (P1, P2, ...): anything in `CURRENT_PLAN.md` flagged `[~]` or `[!]`. Same two-sentence floor — what shipped, what's missing or failed, what completes it.
- **Asks back to the user** (A1, A2, ...): two-sentence floor each. **Primary source: read `CURRENT_PLAN.md`'s In-flight asks section** — those are the structured asks the agent accumulated during Step 4 (wiggum exhaustion, amendment escalation auto-reverts, visual review parks, logged assumptions). Re-emit them here in close-out order; don't drop any. Plus any asks generated *during* close-out itself (proposed `open_questions.md` additions, proposed spec/design edits surfaced post-iteration). Cover:
  - **In-flight asks from Step 4** (wiggum exhaustions, amendment auto-reverts, visual review parks, assumptions). Each was logged as the agent hit it; close-out re-emits with full context.
  - Decisions raised during Step 2 (drift / conflict / ambiguity sweep) that the user resolved interactively or said *"plan around them"* on.
  - Verification gaps — things the implementer couldn't test (missing access, missing data, environment problem).
  - **Proposed spec / design edits** — wording the implementer thinks should land in the spec or design source on the next edit. Include the proposed text verbatim so the user can paste.
  - **Proposed `open_questions.md` additions** — for each parked discrepancy from Step 2, give the wording to append. Example:

    ```
    A3. Append to <impl-dir>/open_questions.md:

        ### Uniqueness key for virtual records
        The spec defines uniqueness on (entity, owner, cycle). The current
        implementation uses (entity, owner). Resolving requires the event
        log schema (B1). Defer until B1 lands.
    ```

End each ask with a clear prompt: *"Want me to ... ? [yes / no / something else]"*.

**Divergences**: do not list `LEDGER.md`'s Divergences rows in the close-out by default — they're long-lived intentional state, not iteration output. Only surface them if the user asks (*"any divergences?"*) or if this iteration **added or cleared** a row, in which case mention only the delta in one line.

#### 2b. Conversation starters (only when fully complete on the current alignment)

When `CURRENT_PLAN.md` is all `[x]`, `LEDGER.md`'s Blocked section is empty, and there are no asks back to the user, replace 2a with a short **conversation-starter** block. Forward-looking suggestions to keep the deliverable moving.

**Format**: numbered/lettered **one-liners** the user can pick by reference (e.g. *"tell me more about S2"*). Each line names the concern in <12 words; the implementer holds the detail until asked. Don't expand any line until the user picks it.

Three buckets — pick a few from each:

- **Spec / design improvements** (S1, S2, ...): gaps noticed while implementing — anti-patterns, missing decision-log entries, sections reading confusingly, cross-references that drifted, design + spec out of sync. **Also**: run `<spec-dir>/scripts/spec-loop.sh check-size <deliverable>`; if any normative file is over 500 lines, propose a split per [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)'s *Splitting large specs* section.
- **Code quality improvements** (C1, C2, ...): brittle code, thin tests, off abstractions, dead code, refactors that would pay back soon.
- **Workflow / best-practice improvements** (W1, W2, ...): friction the implementer hit running the loop.

Example shape:

```
S1. Q@PLATFORM has been open 2 iterations — escalate or design unilateral fallback.
S2. implementation/conventions.md carries 3 entries also in <code-dir>/AGENTS.md — propose generalisation pass.
S3. SPEC.md is carrying dev-facing detail a stakeholder wouldn't sign off on — propose moving §4–§5 into implementation/decisions.md.
C1. service.py is 1100+ lines — split by concern.
C2. No integration test for the cascade against the warehouse.
W1. Step 4 verification has no scripted dev-server orchestration — manual every time.
```

User picks; the implementer expands the picked item with full context + a *"want me to ... ?"* prompt; next iteration starts from there.

#### 3. (Conditional) Propose updates to `HAPPY_PATH.md`

If the iteration shipped behaviour-affecting changes — new flow steps, new components, new fields the user sees, new cascade rules — propose a one-line update to `<state-dir>/HAPPY_PATH.md`:

- A new demo step exercising freshly-shipped behaviour.
- A new sub-test locking in something the diff introduced.
- A revision to a step whose wording drifted from current spec wording.

User accepts / rejects; updates land in a follow-up commit if accepted.

**If the iteration shipped no behaviour changes** (a no-op iteration, or only mechanical / cosmetic edits), **stay silent on `HAPPY_PATH.md`** — don't propose anything. The "Last verified" row gets bumped only when the happy path was re-run and confirmed *and* the visual review passed (when applicable per Step 4's sub-section).

#### 4. Mini-retrospective — improve the loop itself

After the structured close-out, produce 0–N retrospective entries for this iteration's friction. Focused on three buckets — **don't go broader**:

1. **Workflow improvements** — what slowed this iteration? Where did the loop have unnecessary friction? Concrete change to `SKILL.md` or `SPEC_CONVENTIONS.md`.
2. **User-prompting guidance** — what could the user say earlier or more explicitly next time to skip a round-trip? Concrete trigger phrase, bootstrap assertion, or invocation hint.
3. **Anti-repetition** — what fact had to be repeated this iteration that should be persisted (in `LEDGER.md` config, the deliverable's `CLAUDE.md`, or user memory)?

Each entry is a JSONL line matching the user's `/retro` skill schema. Append to the user's retro log (default `.claude/retro/improvements.jsonl`; override via deliverable `CLAUDE.md` if the project uses a different path). Each entry is `applied: false` — the user reviews via `/improve-skills`.

```json
{"timestamp":"<ISO 8601 UTC>","session_summary":"<one sentence>","category":"<skill-update | claude-md | memory | settings>","target":"<file path or skill name>","trigger":"<observed pattern this iteration>","proposal":"<concrete change>","evidence":"<quote or paraphrase>","priority":"<high | medium | low>","applied":false}
```

**Source signals** (look for these in the iteration's chat history):

- Corrections the user made to your approach ("no, do Z") → workflow or anti-repetition.
- Facts the user had to volunteer that weren't in `LEDGER.md` / `CLAUDE.md` ("by the way, this needs SSO refresh") → anti-repetition.
- Repeated clarifications on the same topic ("again, /save not /drafts") → user-prompting guidance.
- Validated non-obvious choices ("yes that was right") → preserve as a workflow note so you don't drift away next time.
- Turns wasted on path resolution, file discovery, or environment setup → workflow.

**Empty retros are fine.** If nothing notable happened this iteration, write nothing and say so. Don't invent generic improvements ("could add more tests", "consider refactoring").

**Out of scope for this retro:** spec/design quality, code architecture, business logic. Those belong in Step 6 section 1c (Spec / design improvements). This sub-step is about the **loop itself** — workflow, prompting, anti-repetition.

## Happy path discipline

`<state-dir>/HAPPY_PATH.md` is the agreed end-to-end demo flow + deterministic tests that exercise each component along the way.

**First-time setup** (run during Bootstrap, or before the first iteration if missing):

1. The implementer drafts a happy path that walks through the spec's primary user journey, cross-referenced to the design / reference deliverable where applicable.
2. The user reviews and edits.
3. For each component along the path, the implementer adds (or links to) a small **deterministic unit test** — fast, no external deps, runs alongside the regular suite. List the tests in `HAPPY_PATH.md` so the next iteration can re-run them as a checkpoint.
4. The file also tracks the last-verified date, the last-aligned commit, and the outcome — appended per iteration.

**Per-iteration**: Step 4 covers per-item happy-path re-runs + the iteration's new unit test, and Step 4's Visual review sub-section gates the "Last verified" bump. Step 6 section 3 handles proposing structural updates. See those.

For the verbose discipline — per-component deterministic tests, last-verified bookkeeping, regression replay rules — see the optional sidecar [`HAPPY_PATH_DISCIPLINE.md`](HAPPY_PATH_DISCIPLINE.md). Link it from your deliverable's `CLAUDE.md` to opt in.

## LEDGER.md — long-lived state

The single long-lived state file per deliverable. Holds project config + alignment bookkeeping + Blocked + Divergences in one place.

```markdown
# LEDGER — <deliverable>

## Config

- Deliverable path: <spec-dir>/domain/<deliverable>
- Code dirs: <code-dir>, …          (from .spec-loop.toml's code_dirs)
- Verification: <project-specific notes — test runners, dev-server URLs, happy-path runner>
- (Optional) Path filter for Step 2 drift check: e.g. `*.py *.ts *.tsx`. Default: unset.
- (Optional) competing_branches: feature/foo feature/bar

## Alignment

- Last bumped: <YYYY-MM-DD>
- Last-aligned commit: <hash>

(Single history — one hash.)

## Blocked

| # | Change | Source | Blocked on | What unblocks it | Notes |
|---|---|---|---|---|---|
| 1 | ... | spec | Q@<OWNER> | ... | ... |

Clearing protocol:
1. When the dep lands, move the row from Blocked into the next iteration's `CURRENT_PLAN.md`.
2. Implement + verify per Step 4.
3. Delete the row from Blocked in Step 5.

If a row sits >2 iterations, escalate — chase the dep or amend the spec.

## Divergences

| # | Vs. | Spec / design section | What spec/design says | What code does | Why | Review trigger | Added |
|---|---|---|---|---|---|---|---|
| D1 | spec | §4.5 uniqueness | unique on (a, b, c) | unique on (a, b) | Dep not landed; can't dedup across cycles yet | When dep ships | <date> |
| D2 | design | screen-3 layout | tabbed view | accordion | Tabs don't fit the dense grid; revisit when grid trims | After grid cleanup | <date> |

Distinction from Blocked:

- **Blocked** = waiting on **someone else** (external dep). Resolves automatically when the dep lands.
- **Divergences** = **we** chose to do something different. Resolves only when **we** revisit and either update the spec/design or rework the code.

Resolution paths for any divergence row:

1. Spec / design catches up (the user updates the source to match the code) → delete the row.
2. Code catches up (a future iteration reworks the code to match) → delete the row.
3. Review trigger fires → revisit; either of the above happens.

**Close-out etiquette**: do not list divergences in close-out summaries by default. Only mention them if the user asks, or if the iteration added/cleared a row (one-line delta).
```

When updating `LEDGER.md`, edit the relevant section in place — the four sections (Config, Alignment, Blocked, Divergences) are independent and shouldn't be conflated.

## Open questions — routed back to the spec source

Parked discrepancies do not have a local file. They live in `<impl-dir>/open_questions.md`. The skill never edits that file directly — it always proposes the wording in the close-out's "Asks back to the user" section, and the user applies the edit on the next pass.

Format expected in `open_questions.md` (skill writes proposals matching this shape):

```markdown
### <one-line title>
**Surface(s).** spec / design / code (and which sections / files).
**Question.** What's unresolved?
**Why parked.** What blocks resolving it now? (Often a future deliverable, or a dep that's waiting.)
**Resolution trigger.** What event makes this resolvable?
```

When the spec source updates `open_questions.md`, the next Step 3 diff (`<last-aligned>..HEAD -- <deliverable-dir>`) picks up the new content — resolutions flow into the plan naturally.

## Generalisation mode

A **separate, on-demand mode** of this skill that surfaces candidates for moving content out of a deliverable's `implementation/` into the cross-cutting categories the repo already has. The aspiration: a deliverable's `implementation/decisions.md` / `conventions.md` accumulates content that *looks* domain-specific while it's being written but is in fact shared with another deliverable — the same picker UX in `foo-module` and `bar-module`; the same save discipline in two adjacent flows. Left alone, that content stays misfiled and the cross-cutting groups never get populated. This mode is how the move is actively driven, rather than left to reviewer discipline.

Generalisation mode is **independent of the iteration loop** — it doesn't pin alignment, doesn't bump the last-aligned hash, doesn't commit. It reads, it surfaces candidates, and the user applies any moves.

### Trigger phrases

- *"Generalise this spec"* / *"generalise `<deliverable>`"*
- *"Check what can promote on `<deliverable>`"*
- *"Look for promotion candidates in `<deliverable>`"*

### Cadence

**On demand only.** Not part of close-out, not scheduled. The user runs this when they suspect duplication has accumulated or when a deliverable has shipped enough iterations that some content has clearly stabilised into a cross-cutting pattern.

### What the mode does

1. **Read the deliverable's content.** `<deliverable-dir>/INTRO.md`, `<deliverable-dir>/SPEC.md` (including its `SPEC/` split children if present), and `<deliverable-dir>/implementation/*.md`. Skip `.sdd/`, `design/`, and opt-in generated artifacts. (INTRO content can also be cross-cutting — e.g. a context blurb that repeats across deliverables; surface it like any other promotion candidate.)
2. **Compare against the existing cross-cutting categories.** The configured homes for cross-cutting content (read `.spec-loop.toml`'s `cross_cutting_dirs` and `code_dirs`):
   - **`<spec-dir>/architecture/*.md`** — system architecture (API patterns, CI/CD, local stack, etc.). Peer topic files (flat, no `spec/` wrapper).
   - **`<spec-dir>/conventions/*.md`** — coding and project conventions (pre-commit, naming, etc.). Peer topic files.
   - **`<code-dir>/AGENTS.md`** and **`<code-dir>/README.md`** — code-area-scoped guidelines. Frontend UX patterns, backend API conventions, query-builder rules, styling rules, etc. **Don't skip these** — duplicate UX rules across deliverables belong in a frontend `AGENTS.md`, not in any of the spec-dir groups.
   - **Other deliverables' folders** under `<spec-dir>/domain/` — to detect recurring patterns across deliverables.
3. **Surface candidates** in three flavours:

   - **Merge** — content overlaps with an existing cross-cutting doc. Propose deleting the local copy and replacing with a cross-reference.
     > *"§4 of `<spec-dir>/domain/foo-module/implementation/conventions.md` ('idempotent save discipline') is already in `<spec-dir>/conventions/save-discipline.md` §2 — propose replacing with a cross-ref."*
   - **Promote** — content is genuinely cross-cutting but no cross-cutting home exists yet. Propose creating one **in an existing category** (don't invent new top-level groups).
     > *"This picker UX entry appears in `<spec-dir>/domain/foo-module/implementation/conventions.md` AND `<spec-dir>/domain/bar-module/implementation/conventions.md`. Both are FE-specific. Propose creating a section in the frontend `AGENTS.md` (or a sibling doc referenced from it); replace both local copies with cross-refs."*
   - **Generalise to a guideline** — content is incidental enough that a short best-practice entry would suffice.
     > *"This 80-line investigations note boils down to 'use idempotent saves'. Propose one bullet in `<spec-dir>/conventions/save-discipline.md`; the rest of the note belongs in commit-message history, not in `implementation/`."*

4. **Produce the proposed move + cross-ref edit** as a close-out-style ask — the user applies. The skill never edits the deliverable folder or the cross-cutting source directly.

### Anti-patterns specific to this mode

- **Inventing new top-level groups.** If content doesn't fit `<spec-dir>/architecture/`, `<spec-dir>/conventions/`, or any `<code-dir>/AGENTS.md`, **don't** propose a new top-level group (`ui-patterns/`, `data-patterns/`, etc.) as a side-effect of one promotion. If a new category is genuinely needed, surface it as a *separate* discussion in close-out — not bundled into a promotion ask.
- **Promoting deliverable-specific rules.** Promotion is for content that turns out to be cross-cutting *despite* being written domain-local — not for everything in `implementation/`. Rules unique to one deliverable stay in that deliverable's `implementation/`.
- **Editing `<code-dir>/AGENTS.md` or `<spec-dir>/<group>/*.md` directly from this mode.** The mode proposes; the user applies. Same invariant as the iteration loop.

## Anti-patterns

- **Editing the spec or design source from within the loop.** The skill *proposes* wording in close-out asks; the user applies edits.
- **Hand-editing `LEDGER.md`'s Alignment hash to skip a real iteration.** The hash bumps in Step 5 *because* an alignment happened — don't fast-forward it to silence a diff.
- **Re-introducing a `snapshot/` copy folder.** In the in-repo model, alignment is a commit hash and drift is `git diff`. Verbatim copies are a legacy mechanism — don't bring them back.
- **Skipping the Step 3 approval gate** (in full flow) without explicit user instruction. Auto mode is about tool permissions, not workflow shortcuts.
- **Letting opt-in generated artifacts outpace the spec or design.** When a deliverable declares one, Step 4's escalation rule exists to prevent it.
- **Adding generated artifacts the deliverable hasn't opted into.** Generated artifacts are opt-in per deliverable (declared in `<impl-dir>/CLAUDE.md`). Don't add one as a side-effect of an iteration — it's a separate decision with regen / drift cost.
- **Inventing new top-level groups during generalisation.** Use the existing categories — `<spec-dir>/architecture/`, `<spec-dir>/conventions/`, `<code-dir>/AGENTS.md`. See [Generalisation mode](#generalisation-mode) anti-patterns.
- **Bundle commits without an opening signal.** The opening commit (or the plan landing in the closing commit) signals "we're aligning to this version".
- **Appending to `CURRENT_PLAN.md` across iterations.** Each Step 3 fully overwrites the file. The previous iteration's content is preserved in git history, not on disk.
- **Flipping a checkbox without self-verification.** Concrete evidence (test exists, exit code 0, happy path ran) before `[x]`. Don't trust the agent's own claim.
- **Declaring a measurable UI claim done from a screenshot alone.** "Edge-to-edge", "sticky bottom", "no scrollbar", "centered" need a DOM probe (`getBoundingClientRect` + `scrollWidth`/`scrollHeight` vs `clientWidth`/`clientHeight`) paired with the screenshot. See Step 4's *Screenshot vs. DOM probe* sub-section.
- **Picking an interpretation under spec ambiguity without logging the assumption.** Silent decisions become buried tech debt. Use Step 2's ambiguity sweep upfront, or Step 4's assumptions-log rule mid-flight.
- **Looping past the wiggum budget.** Five attempts; if it's still failing, escalate. Spinning is worse than asking.
- **Editing the pitch / brief from the loop.** Any external brief is read once at bootstrap for background. Spec→pitch sync happens only on explicit user request — never as a side effect of an iteration.
- **Local open-questions files.** Open questions belong in `<impl-dir>/open_questions.md`, not in `.sdd/`.
- **Auto-listing divergences in every close-out.** Surface them only on demand or as a delta.
- **Letting `Divergences` rows sit without a review trigger.** Every row needs a concrete "when to revisit".
- **Sliding into quick-flow when criteria don't all hold.** Eligibility is all-or-nothing; partial matches → full flow.

## Bootstrap LEDGER.md template

When `LEDGER.md` is created during Bootstrap, populate `## Config` with the project's pinned values:

- **Deliverable path** — the resolved `<deliverable-dir>` (e.g. `<spec-dir>/domain/my-deliverable`).
- **Code dirs** — the `<code-dir>` entries from `.spec-loop.toml` the workstream touches.
- **Verification commands** — test runners, dev-server checks, happy-path runner.
- *(Optional)* **Path filter for Step 2's drift check** — leave unset by default; the agent reasons about noise from file paths.
- *(Optional)* **competing_branches** — set only when coordinating across parallel branches.

The Alignment section starts with the bootstrap `HEAD` as the first `last-aligned` hash. Blocked and Divergences start empty (just the header rows). They fill in over iterations.

For the on-disk shape of `HAPPY_PATH.md` and `CURRENT_PLAN.md`, see the example layouts in their respective sections above — adapt the columns and fields to the deliverable.
