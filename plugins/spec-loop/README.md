# spec-loop

A Claude Code skill that iterates code against a spec living in the **same
repository** as the code, using a **pinned-commit-hash alignment** instead
of file copies / snapshots. Each iteration is driven by `git diff
<last-aligned>..HEAD` over the deliverable folder and over the code paths.

> *Previously this plugin was `spec-driven-workflow` and assumed the spec
> lived elsewhere (separate repo / Confluence). That model has been
> retired here — see commit history if you need the old shape.*

## What it does

The spec and the code share one git history. The skill pins a
`last-aligned commit hash` per deliverable; each iteration's plan comes
from three diffs against that hash:

1. The deliverable-folder diff — new design intent → code.
2. The code-paths diff — code changes that may need a spec home.
3. Cross-branch drift (optional) — if a sibling branch has edited the
   same deliverable.

Six-step loop: pin alignment → drift check → plan → implement+verify →
commit → close out. State (the ledger, the happy path, the current plan)
lives at `<deliverable-dir>/implementation/.sdd/`, committed in full.

## Triggers

Any user prompt that semantically asks to align code with the latest
spec:

- *"Let's iterate on our spec"* / *"Iterate"*
- *"Pull the spec changes and align"*
- *"Run the spec loop"* / *"Run the spec-driven workflow"*
- *"Update against the latest spec"*
- *"Check spec vs design vs code"*

Two narrower sub-triggers (don't run the full loop):

- *"Check cross-branch drift on `<deliverable>`"*
- *"Check merge readiness on `<deliverable>`"*

One separate mode (no loop, read-only):

- *"Generalise this spec"* / *"Check what can promote"* — scans the
  deliverable's `implementation/` for content that's actually
  cross-cutting and surfaces promotion candidates.

## Folder layout (in the repo)

Defaults — override `spec_dir` and friends via `.spec-loop.toml` at the
repo root if your project's tree looks different:

```
<repo-root>/
├── .spec-loop.toml             ← optional config (defaults to specs/)
├── <spec-dir>/                 ← defaults to specs/
│   ├── architecture/           ← cross-cutting topics (flat peer files)
│   ├── conventions/            ← cross-cutting topics (flat peer files)
│   └── domain/
│       └── <deliverable>/
│           ├── INTRO.md        ← context, cross-refs (on-ramp)
│           ├── SPEC.md         ← business-binding (HARD requirements)
│           └── implementation/ ← everything else
│               ├── decisions.md
│               ├── conventions.md
│               ├── investigations.md   (optional)
│               ├── changelog.md        (optional)
│               ├── open_questions.md   (optional)
│               ├── CLAUDE.md           ← deliverable overlay
│               └── .sdd/               ← iteration state
│                   ├── LEDGER.md
│                   ├── HAPPY_PATH.md
│                   └── CURRENT_PLAN.md
└── <code-dir>/                 ← whatever the project's code root(s) are
```

For tiny specs the **flat-mode opt-out** is a single file
`<spec-dir>/<deliverable>.md` with state at `<spec-dir>/.sdd/<deliverable>/`.
Promote to F-shape when it outgrows. See
[`SPEC_CONVENTIONS.md`](skills/spec-loop/SPEC_CONVENTIONS.md) for details.

## Companion files

The plugin's skill directory carries three companion docs alongside
`SKILL.md`:

| File | Purpose |
|---|---|
| `SKILL.md` | The loop itself — what each step does, when to escalate, how close-outs work. |
| `SPEC_CONVENTIONS.md` | How to read and write spec content — tier model, EARS notation, cross-refs, change-log conventions, the `.spec-loop.toml` config reference. |
| `REPO_SCRIPTS.md` | The optional wrapper script (`<spec-dir>/scripts/spec-loop.sh`) that lets you allowlist read-only git operations with one permission rule instead of a per-hash prompt every iteration. |
| `HAPPY_PATH_DISCIPLINE.md` | Optional sidecar — full discipline for per-component deterministic tests + a verification log. Link from your deliverable's `CLAUDE.md` to opt in. |

`SKILL.md` is loaded automatically on trigger; the rest load on demand
when the skill needs them.

## When to use

- The spec and the code share a repo (monorepo or otherwise).
- You want to track *what changed in the spec, since when, and what the
  code did about it* without copying spec files around.
- You want repeated friction-free iterations: pin a hash, work, push,
  pin again.

## When NOT to use

- The spec lives in a separate repo / Confluence / Notion — the
  snapshot-based model fits better (no skill for that ships here; the
  old `spec-driven-workflow` plugin is in this marketplace's git history
  if you need to reconstruct it).
- The project has no written spec — design lives in tickets / issues /
  chat. The loop's diff-driven shape doesn't apply.
- The team has its own established design-to-code process that conflicts
  with this skill's opinions (F-shape deliverable, tier model, EARS).
  Those opinions are load-bearing for the loop's defaults; if you fork
  them, you're effectively writing your own skill.

## Config — `.spec-loop.toml`

Optional, at the repo root. All keys have defaults:

```toml
spec_dir = "specs"               # spec root
code_dirs = []                   # default code pathspec for `code-diff` (empty = everything)
cross_cutting_dirs = ["architecture", "conventions"]   # peer-file categories under <spec-dir>/
```

See [`SPEC_CONVENTIONS.md`](skills/spec-loop/SPEC_CONVENTIONS.md)
*Repo configuration* for the full set.
