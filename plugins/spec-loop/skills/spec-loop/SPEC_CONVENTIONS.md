# Spec conventions

Reference for reading spec wording and drafting proposed spec edits in
close-outs. Loaded on demand by [`SKILL.md`](SKILL.md) — only needed when
generating spec text (Step 6 asks back to user, or when this skill is
invoked directly from the spec source for editing). The loop steps in
`SKILL.md` don't depend on this file.

Project-specific overlays — the deliverable's specific phase numbering,
active `Q@<OWNER>` tags, the actual file set, reference module for visual
review, opt-in generated-artifact specifics — live in the deliverable's
`CLAUDE.md` at `<spec-dir>/<deliverable>/implementation/CLAUDE.md`.

`<spec-dir>` defaults to `specs/` and can be overridden via `.spec-loop.toml`
at the repo root — see *Repo configuration* at the bottom of this file.

## Notation

- **Sections** are referenced as `§N` or `§N.M` (e.g. `§2.1.1`). Never
  `Section N` or `section N` in prose.
- **Open questions** are tagged `Q@<OWNER>` where the owner is a person *or*
  a team. Resolved questions are struck through with `~~Q@<OWNER>~~ ✅
  **resolved <date>**: …`. Partially-resolved use the same strike pattern
  but list `🔓 Still open:` sub-bullets.
- **Decisions** in `implementation/decisions.md` are letter-coded (A, B, C,
  …). Each entry: `<letter>. [<origin>, <date>] <decision>.` Origin
  captures who participated — a person, pair, or team. For ordinary
  decisions the entry is a one-liner. For heavyweight decisions the entry
  points to an external ADR: `<letter>. [<origin>, <date>] See ADR-NNNN:
  <slug>.` The deliverable's `INTRO.md` (or `implementation/CLAUDE.md`)
  carries the canonical pointer to where ADRs live in your repo. The skill
  doesn't load ADRs.
- Decisions define architectural intent. Don't sprinkle `(decision X)`
  cross-refs throughout the body — they read as ceremony. The decisions
  list is the source; cite it only when load-bearing.
- **Phases** are tagged `P0` / `P1` / `P2` / `…` (P0 = current design; P1 =
  first ship; P2+ = deferred). At the **first mention** in a doc, spell out:
  *"phase 1 (P1)"*. Subsequent mentions can drop the spell-out. Don't mix
  in `V1` / `Phase 2`. The specific phase mapping is per-deliverable; the
  tag style is shared.

## Deliverable shape

Every module deliverable folder (`<spec-dir>/domain/<module>/`) carries
exactly **two top-level markdown files** plus **one subfolder** for
everything else:

- **`INTRO.md`** — domain context; cross-refs to other modules,
  `<spec-dir>/architecture/`, `<spec-dir>/conventions/`, per-package
  guideline files. The on-ramp that orients a new reader or LLM session.
  Not a tier — `INTRO.md` doesn't make HARD claims about behaviour, it
  directs the reader to where those live.
- **`SPEC.md`** — business-binding requirements; stakeholder-readable.
  The reviewer (canonically named "the stakeholder" or your team's chosen
  reviewer name) signs off against this file. **All HARD requirements live
  here** — anything stakeholder-set or business-binding is in `SPEC.md` by
  virtue of being there. EARS acceptance criteria live as inline bullets
  within sections (not a flat list at the bottom).
- **`implementation/`** — everything else. The structurally-separate dev
  surface.

**Flat-mode opt-out.** For tiny deliverables where the F-shape is overkill,
a single file `<spec-dir>/<deliverable>.md` is acceptable. The skill detects
flat mode by file-vs-folder and adjusts: no `INTRO.md`/`SPEC.md` split, no
`implementation/` subfolder, the whole spec is one file, and the loop's
state dir moves to `<spec-dir>/.sdd/<deliverable>/`. Flat mode loses the
HARD/AGREED/INCIDENTAL tier model — everything's in one voice. Promote to
F-shape when the spec outgrows it (typically when you want to start
recording decisions separately).

## Normative files (three tiers by voice)

The deliverable's normative files carry different voices and different
binding strengths. **The file an item lives in is its tier** — no inline
`[HARD]` tags needed.

- **`SPEC.md`** (HARD) — narrative prose. Stakeholder-readable. Tells the
  story of *what* the deliverable is required to do and *why*. **All HARD
  requirements live here.**
- **`implementation/decisions.md`** (AGREED) — letter-coded declarations.
  Internal dev decisions: the team picked among options and settled. Each
  entry: `<letter>. [<origin>, <date>] <decision>.`
- **`implementation/conventions.md`** (INCIDENTAL) — bullet-style.
  Incidental implementation choices the team picked without strong debate.
  Each entry may carry a `(stable)` flag if change-resistance is
  load-bearing for users — without the flag, the entry is free to update
  when code drifts away from it.

`implementation/conventions.md` is **optional**. Create it the first time an
incidental choice needs recording; if it stays empty across iterations,
propose deletion in close-out.

**The skill reads the deliverable's *actual* file set — don't assume
exactly three.** A deliverable may have only `SPEC.md` +
`implementation/decisions.md` (no conventions), and usually carries
**support files** alongside the normative ones, all inside `implementation/`:

- **Opt-in generated artifacts** — derived from the normative files, never
  hand-edited to match code (see *Generated artifacts*). Most deliverables
  have none.
- **History** (`changelog.md`) — append-only record; optional.
- **Investigation / validation notes** (`investigations.md`,
  `data_validation_plan.md`) — research and test-plan scratch space that
  informs the spec but isn't itself normative.
- **Open questions** (`open_questions.md`) — user-curated; the skill only
  proposes wording.

Support files are not part of the normative tier and don't carry binding
strength. The deliverable's `CLAUDE.md` lists which files exist and what
each is for; consult it rather than assuming.

**File-of-origin = binding strength.** The skill reads the file an item
lives in to set conflict-resolution and amendment-escalation defaults:
`SPEC.md` conflicts are loud and bias toward "take spec";
`implementation/conventions.md` conflicts bias toward "take code, sync the
convention". See [`SKILL.md`'s Step 2 and Step 4](SKILL.md) for the
workflow detail.

## Module specs vs cross-cutting specs

The `<spec-dir>/` tree has two shapes, used for different scopes:

- **Module specs** — a long-lived unit of code with a stable identity.
  Folder: lowercase `snake_case`, under `<spec-dir>/domain/`. Path:
  `<spec-dir>/domain/<module>/`. Uses the deliverable shape — `INTRO.md` +
  `SPEC.md` + `implementation/`.

- **Cross-cutting concerns** — architecture, conventions, etc. Live as
  **peer topic files** at the group root: `<spec-dir>/architecture/<topic>.md`
  and `<spec-dir>/conventions/<topic>.md`. No `spec/` subfolder, no
  per-deliverable `INTRO/SPEC/implementation/` split, no per-topic
  `CLAUDE.md`. The skill reads whatever `.md` files exist in the group.

  The default category names (`architecture/` + `conventions/`) are
  conventions, not load-bearing. Override the set via `.spec-loop.toml`'s
  `cross_cutting_dirs` if your project uses different names (e.g.
  `docs/concepts/`, `docs/practices/`).

The two shapes reflect their roles:

- Module specs are full deliverables with iteration state, decisions,
  multi-author edits, and (optionally) regen of artifacts. The
  `INTRO.md` + `SPEC.md` + `implementation/` shape carries that load.
- Cross-cutting topics are smaller, more stable rules referenced by many
  modules. A flat file is easier to read, reference, and grep across;
  per-deliverable scaffolding would add ceremony without value.

The assumption is **few cross-cutting concerns, many modules over time**.

**Workstreams** (e.g. `feature_x_revamp`) are *not* specs — they're
branches of work in the repo that iterate against existing deliverables.
The skill records commit hashes, not workstream branch names. A workstream
that touches multiple deliverables invokes the skill once per deliverable.

## Cross-spec references

Specs reference each other rather than duplicating content. The cross-ref
*is* the contract. When the referenced source changes, the referring spec
inherits the change automatically — no propagation work.

When a module spec relies on a cross-cutting concern, cross-ref the
relevant topic file:

> ## §3 Data layer
>
> Items follow the multi-tenant data model — see
> [`<spec-dir>/architecture/multi-tenant.md`](../../architecture/multi-tenant.md).
> This module adds two module-specific columns; the rest is shared.

When the dependency is a package-scoped guideline (FE/BE specifics that
live in the package, not in `<spec-dir>/`), cross-ref the package's
`AGENTS.md` or `README.md`:

> ## §5 Picker UX
>
> Follows the shared picker pattern — see
> [`<code-dir>/AGENTS.md#picker-ux`](../../../<code-dir>/AGENTS.md#picker-ux).

When the dependency is on another module's design (rare, prefer
architecture/), cross-ref the other module's `SPEC.md`:

> See [`<other-module>` SPEC §4 Foo](../<other-module>/SPEC.md#4-foo).

**Duplicating cross-cutting content into a module's `SPEC.md` or
`implementation/` is an anti-pattern** — the duplicate drifts. If the same
content appears in two modules, run [Generalisation mode](SKILL.md#generalisation-mode)
to surface it as a promotion candidate.

When Step 2 surfaces a conflict that touches a cross-referenced section,
the amendment ask routes to the *source* spec (the one being referenced),
not the referring module spec. The user re-invokes the skill against the
source spec to land the amendment.

## Splitting large specs

Spec files grow over time. When a normative file (`SPEC.md`,
`implementation/decisions.md`, or `implementation/conventions.md`) crosses
**~500 lines** OR more than 8 second-level headers (`##`) — whichever
fires first — propose a split in Step 6 close-out section 1c. Splits land
as a deliberate user-confirmed edit, not silently.

**Split pattern — index + sub-files.** The original file stays as a slim
index; sub-files hold the content:

```
<spec-dir>/domain/my-deliverable/
├── INTRO.md                 ← unchanged
├── SPEC.md                  ← stays: intro + section index linking sub-files
├── SPEC/                    ← split sub-files (created when SPEC.md crosses threshold)
│   ├── 01-overview.md
│   ├── 02-data-layer.md
│   └── 03-save-flow.md
└── implementation/
    ├── decisions.md         ← stays unless it crosses threshold
    └── conventions.md
```

- `SPEC.md` keeps the prose intro + a numbered section index linking to
  sub-files. Filename prefix matches section number: `§2` = `02-<slug>.md`.
- Sub-files use the same notation as the original (EARS, `Q@<OWNER>`, etc.).
  Treat them as if they were `## §N` sections inlined.
- `implementation/decisions.md` and `implementation/conventions.md` follow
  the same pattern when they cross the threshold —
  `implementation/decisions/` and `implementation/conventions/` subdirs
  respectively.
- The skill's diff (`<last-aligned>..HEAD -- <deliverable-dir>`) operates
  on the whole deliverable folder; sub-files are part of the spec.

**Lazy loading.** The Step 3 diff covers the whole deliverable folder, so
all changed sub-files surface. For Step 3 / Step 4 deep reads, the agent
loads only sub-files whose section IDs appear in the spec diff or in the
user's prompt. Other sub-files stay un-read until needed. This is what
makes splitting worthwhile — the agent's context isn't burned re-reading
sections that didn't change.

**Check the size.** Run `<spec-dir>/scripts/spec-loop.sh check-size
<deliverable>` (see [`REPO_SCRIPTS.md`](REPO_SCRIPTS.md)) to print line
counts per file. Step 6 section 1c reads this output and proposes splits.

**Anti-patterns:**

- **Splitting prematurely** (under threshold). `SPEC.md` should stay whole
  when it can — sub-files add navigation cost. Wait for the threshold.
- **Relative-path cross-refs** between sub-files
  (`./02-data-layer.md#xyz`) instead of `§N` notation. `§N` survives
  renumbering and moves; paths don't.
- **Index drift.** When a sub-file is added, renamed, or removed, update
  `SPEC.md`'s section index in the same commit. The index is the source of
  truth for what sub-files exist.
- **Mixing the index and content.** Once you split, `SPEC.md` is the index.
  Don't let prose bleed back into it — keep prose in `01-overview.md` (or
  equivalent).

## Spec philosophy

- **The spec describes WHAT to build, not HOW.** Architectural intent
  (what endpoints exist conceptually, the deferred-save model, the data
  model) belongs in `SPEC.md`. Implementation detail (specific verb
  justifications, class names, file paths, ORM specifics, test counts)
  belongs in `implementation/decisions.md` or
  `implementation/conventions.md` — or in code.
- **The spec is forward-looking design.** Avoid "currently shipped" /
  "tests pass" / "branches at" framings — they imply a status report,
  which the spec is not.
- **Be specific about constraints, sparing on prescriptions.** `SPEC.md`
  should pin decisions that limit the design space (e.g., "no
  `/items/promote` endpoint; promotion happens via `/save`'s diff")
  without dictating the exact endpoint shape.
- **`SPEC.md` is what the reviewer signs off on.** A stakeholder reading
  `SPEC.md` should be able to confirm the deliverable meets the business
  need without wading through implementation detail. Anything that fails
  the "would the stakeholder want to read this?" test belongs in
  `implementation/`.
- **Self-contained deliverable.** A reader (human or LLM) should be able
  to build the deliverable from the deliverable folder alone — `INTRO.md`
  (for context + cross-refs) + `SPEC.md` (for requirements) +
  `implementation/` (for dev material). External pitches / proposals are
  optional background; `implementation/changelog.md` is optional history.

## Acceptance criteria — EARS notation

For testable behaviour, prefer **EARS-style** acceptance criteria. Four
shapes cover most needs:

- `WHEN <trigger> THE SYSTEM SHALL <observable behaviour>` — event-driven.
- `WHILE <state> THE SYSTEM SHALL <behaviour>` — state-driven.
- `IF <condition> THEN THE SYSTEM SHALL <behaviour>` — conditional.
- `THE SYSTEM SHALL <behaviour>` — ubiquitous (no trigger).

Rules of thumb:

- **One EARS line ≈ one deterministic test** in `HAPPY_PATH.md` (or the
  regular suite). The line *is* the test name.
- **EARS for things you'd want a regression test for.** Free prose for
  context, motivation, and decisions that aren't directly testable.
- **Don't EARS-ify everything.** Over-formalising the spec becomes its own
  anti-pattern. The goal is *testable acceptance criteria are easy to spot
  and easy to convert to tests* — not to bury every paragraph in `THE
  SYSTEM SHALL`.

Example:

> ### §3.2 Draft save
>
> The user saves an in-progress draft and the marked rows persist into the
> next period.
>
> - WHEN the user saves a draft THE SYSTEM SHALL persist all marked rows
>   with the current `period+1` tag.
> - IF a marked row already exists in the next period THEN THE SYSTEM
>   SHALL skip it (idempotent save).
> - WHILE the save is in flight THE SYSTEM SHALL prevent further edits on
>   the affected rows.

The implementing agent's Step 4 uses these as the test inventory: each
EARS line should map to a named test before the plan item flips to `[x]`.

## Working principles for spec edits

- **Discuss before committing on substantive design questions.** When the
  user proposes a meaningful change ("what about X?"), default to grilling
  the idea (pros / cons / edge-cases) before writing edits. The user
  usually wants a real conversation, not a rubber-stamp.
- **Auto mode prefers progress over confirmation prompts for mechanical
  edits.** Typo fixes, cross-ref cleanup, vocabulary harmonisation — just
  do them. For substantive design choices, confirm first. (This is
  distinct from auto mode's effect on tool permissions during the loop's
  Step 4.)
- **Read `changelog.md` before discussing history.** Many decisions today
  were made earlier and recorded there. Don't re-litigate; consult the
  change log to ensure you're up-to-date with prior reasoning.
- **Multi-edit landings are normal.** A single user message often
  produces 5–15 edits across multiple sections. Batch them, then summarise
  at the end.
- **Cross-references must stay live.** When you renumber sections or
  items, sweep all cross-refs and update them. Search before committing.

## Change-log conventions

- The change log is a **historical record**. Entries describe events as
  they were thought / decided at the time.
- **Don't rewrite prior entries** when current understanding changes. Add
  a new entry that records the correction. The earlier entry stays as a
  record of the original misunderstanding.
- **Vocabulary harmonisation can be applied retroactively** across the
  change log (e.g. `V1` → `P1` rename). Document the retroactive change
  with a new entry. This is fidelity-preserving because the rename itself
  is recorded.
- **Date entries with absolute dates** (e.g. `2026-04-29`), never relative
  ("today" / "last week").
- A typical entry leads with a one-line summary, then a `(<actor>)`
  parenthetical, then the rationale, then a list of `Sites updated:`
  paragraphs.

### Cross-file moves between tiers

When an item graduates between tiers — e.g. the stakeholder re-confirms
an `implementation/decisions.md` item, so it gets promoted to `SPEC.md`;
or a stability concern surfaces and a convention entry gains a
`(stable)` flag — record the move as an `implementation/changelog.md`
entry with the rationale.

**Letter codes in `implementation/decisions.md` are stable across moves.
Don't renumber.** A promoted item leaves a strike-through placeholder so
cross-refs don't go dead:

```
~~B. [moved to SPEC §2.3 on 2026-05-12 — promoted to HARD after stakeholder confirmation]~~
```

Demotions (rare) work the same way in reverse — leave a pointer at the
source's last home noting where the item lives now.

## Generated artifacts

Some deliverables opt into a **generated artifact** alongside the
normative files — e.g. an OpenAPI summary, a schema dump, a JSON sketch —
derived from `SPEC.md` + `implementation/decisions.md` and used for
cross-repo coordination or stakeholder review. **Most deliverables have
none.** Generated artifacts are opt-in per deliverable, declared in
`<deliverable-dir>/implementation/CLAUDE.md`. They live in
`<deliverable-dir>/implementation/`.

When a deliverable does opt in:

- **Spec change → regenerate the artifact in the same commit chain.** When
  the normative files change in a way that affects the artifact, the
  artifact must be regenerated to match. The change-log entry should
  mention the regen so the trail is recoverable.
- **Implementation discovers a constraint** that forces the artifact to
  diverge from the spec → use the loop's Step 4 escalation rule (stop,
  write a constraint note, ask the user whether to amend the spec). Don't
  let the artifact silently outpace the spec.

The artifact's header should carry a "Last regenerated" stamp + a pointer
to which sections of the normative files it was generated from, so
reviewers can spot drift.

**Don't add a generated artifact mid-iteration.** Opting in is a separate
decision with regen / drift cost. If an iteration surfaces a need for one,
propose it in close-out section 1c (conversation starters); the user
decides whether to opt in.

## Spec-writing anti-patterns

- **Negative documentation** ("X is NOT here", "there is no `<some_field>`")
  only makes sense as a delta against a prior schema. In a settled spec it
  adds noise. Say what *is* there, not what isn't.
- **Inline `(decision X)` cross-refs** scattered through the body. Once
  `implementation/decisions.md` lists the decisions, citing them inline is
  ceremony. Cite only when the inline reference is load-bearing for the
  reader.
- **Prose narrative in `implementation/decisions.md`.** It belongs in
  `SPEC.md` (the requirement) or `INTRO.md` (the context). Decisions are
  declarative — one line each, with origin and date.
- **Tagging items in `SPEC.md` with `[HARD]` or similar.** Redundant —
  being in `SPEC.md` *is* the tag. The file is the tier signal.
- **Convention entries that need stability but lack the `(stable)` flag.**
  If you want this not to drift, mark it. Otherwise the skill will treat
  the entry as cheap to update from code.
- **Duplicating cross-cutting content into a deliverable's `SPEC.md` or
  `implementation/`.** The cross-ref is the contract — see *Cross-spec
  references*. Copy/pasted content drifts and rots; the [Generalisation
  mode](SKILL.md#generalisation-mode) exists to surface these.
- **Inventing new top-level groups for cross-cutting content.** Use the
  existing categories — `<spec-dir>/architecture/`, `<spec-dir>/conventions/`,
  package-scoped guideline files. See *Cross-spec references* and
  [SKILL.md's Generalisation mode](SKILL.md#generalisation-mode).
- **`INTRO.md` carrying behavioural requirements.** INTRO is context +
  cross-refs only. If you find yourself stating a HARD requirement in
  `INTRO.md`, it belongs in `SPEC.md`.
- **`SPEC.md` carrying dev-only detail.** Class names, ORM specifics, test
  counts, file paths belong in `implementation/decisions.md` or
  `implementation/conventions.md` — or in code. SPEC is what the
  stakeholder signs off on.
- **Code-existence claims** in the body ("currently shipped",
  "test_routes_e2e.py walks the planner happy path"). The spec is design,
  not status. The change log is allowed to record what was *thought* at
  the time of the entry; the body should not.
- **Implementation-specific paths and identifiers** in `SPEC.md` (file
  paths, branch names, PR numbers). These belong in commit messages or
  `implementation/changelog.md` entries, not the business-binding spec.
- **Pre-emptive over-specification.** Don't pin verb justifications,
  request-body shapes, file paths, or ORM details — the implementing LLM
  picks those.
- **Aspirational task lists** disguised as design ("we will / we need to /
  TODO"). The spec describes the resolved design or names what's open via
  `Q@<OWNER>`. Anything between is noise.
- **Resolved `Q@<OWNER>` entries piling up.** When a question resolves,
  fold the resolution into the spec body (the design now reflects the
  answer) and **delete the question entry in the same edit**. The body of
  the spec carries the answer; the change log records the chronology.
  Mixed entries (resolved sub-question + open sub-question) stay until all
  sub-questions resolve.
- **Over-formalising acceptance criteria.** Not every line should be EARS.
  Use it where regression-test value is high; free prose for context and
  motivation.

## Repo configuration — `.spec-loop.toml`

Optional file at the repo root that overrides spec-loop's defaults. Used
both by the skill (when resolving deliverable paths) and by the wrapper
script in [`REPO_SCRIPTS.md`](REPO_SCRIPTS.md).

```toml
# Optional. All keys have defaults.

# Where the spec tree lives. Default: "specs".
spec_dir = "specs"

# Default code pathspec for the wrapper's `code-diff` verb. Empty = diff
# everything in the repo. Examples for different project layouts:
#   single-package repo:     code_dirs = ["src"]
#   monorepo with packages:  code_dirs = ["packages/api", "packages/frontend"]
code_dirs = []

# Cross-cutting category subfolders inside <spec-dir>/. Defaults match the
# F-shape's "architecture + conventions" pair. If your project uses
# different names (e.g. docs/spec/concepts/, docs/spec/practices/), list
# them here and the skill's Generalisation mode will look there.
cross_cutting_dirs = ["architecture", "conventions"]
```

A repo without `.spec-loop.toml` works fine with all defaults — pick up
the config only when you need to override one of them.
