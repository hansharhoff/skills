# Happy-path discipline (optional sidecar)

This file is **opt-in**. The main [`SKILL.md`](SKILL.md) mentions happy-paths
in passing — that's enough for most deliverables. If you want the fuller
discipline (deterministic per-component tests, last-verified bookkeeping,
proposed per-iteration updates), link this file from your deliverable's
`implementation/CLAUDE.md`:

```markdown
## Happy-path discipline

Follow the discipline in `<plugin>/HAPPY_PATH_DISCIPLINE.md`.
```

Once linked, the skill treats it as load-bearing during Bootstrap and at
the end of each iteration.

## What `HAPPY_PATH.md` is

`<deliverable-dir>/implementation/.sdd/HAPPY_PATH.md` is **the agreed
end-to-end demo flow + the deterministic tests that exercise each
component along the way**. It's the single thing you can re-run between
iterations to confirm the deliverable still does what the spec says it
does.

Two distinct uses:

1. **Live verification** — run after Step 4 of each iteration. A
   Playwright script, an integration suite, or a manual click-through if
   nothing else exists. The point is to confirm the *whole spec story*
   still works, not just the new bits.
2. **Test inventory** — each EARS line in `SPEC.md` should map to one
   deterministic test, and `HAPPY_PATH.md` lists which test name covers
   which line. New iterations are responsible for adding tests for new
   EARS lines.

## First-time setup (during Bootstrap)

If the deliverable opts into this discipline, Bootstrap adds these steps
after the initial `.sdd/` scaffolding:

1. **Draft the happy path.** The implementing agent reads `SPEC.md` and
   drafts a step-by-step demo walking through the deliverable's primary
   user journey, end to end. Each step names the component it exercises
   and the observable outcome.
2. **User reviews and edits.** The draft is rarely right on the first
   try; the user trims, reorders, and clarifies.
3. **Per-component deterministic tests.** For each component along the
   path, the implementing agent adds (or links to) a small unit / integration
   test:
   - Fast (sub-second ideally).
   - No external dependencies that aren't mocked.
   - Runs alongside the regular suite — same test runner, same
     `pytest`/`vitest`/`go test` invocation. If your project has both a
     fast unit suite and a slower integration suite, prefer the fast one
     for the per-component test.
   - The test name *is* the EARS line where possible.
4. **Bookkeeping rows.** The file tracks the last-verified date, the
   source-spec commit, and the verification outcome — appended to per
   iteration.

Example structure:

```markdown
# Happy path — my-deliverable

## Demo flow

1. User opens the planner at `/foo` — the previous period's plan loads
   in read-mode.
2. User toggles edit-mode — table cells become editable.
3. User marks 3 rows as carry-over and clicks Save — the rows persist
   into the next period with idempotent semantics.
4. User reloads — the changes survive.

## Per-component tests

| Step | Component | Test | EARS line |
|---|---|---|---|
| 1 | planner.list-view | `test_list_loads_previous_period` | §3.1 ubiquitous |
| 1→2 | planner.edit-mode | `test_toggle_to_edit` | §3.1 WHEN-toggle |
| 3 | planner.save | `test_save_marked_rows_idempotent` | §3.2 IF-already-exists |
| 4 | planner.reload | `test_reload_persists` | §3.2 WHEN-save |

## Verification log

| Date | Source commit | Outcome |
|---|---|---|
| 2026-05-12 | abc1234 | ✅ all green |
| 2026-05-19 | def5678 | ⚠️ test_save flaky once on CI, passed locally |
| 2026-05-26 | 0123abc | ✅ all green |
```

## Per-iteration

- **After Step 4** of each iteration: re-run the documented happy path.
  If anything in the demo flow now fails or behaves differently, that's
  a regression — fix it before moving on, even if the iteration's own
  plan items pass.
- **Add a new test** covering the spec changes the iteration shipped.
  Update the per-component table.
- **Append a verification-log row** with date, source-spec commit hash,
  and outcome.
- **After Step 6** (close-out): propose `HAPPY_PATH.md` updates as part
  of section 4 if the iteration shipped behaviour-affecting changes —
  new flow steps, new components, new fields the planner sees. The user
  accepts / rejects; updates land in a follow-up commit if accepted.

## When the happy path falls behind

Real life: sometimes the happy path is allowed to fall a half-step behind
the spec, because the test infrastructure isn't ready or the bookkeeping
is too painful to maintain. That's tolerable for an iteration or two but
calcifies into permanent debt if left. Two signals to escalate:

- The verification log has more than ~3 ⚠️ rows in a row without a green.
- The happy path's flow no longer matches the spec's primary user
  journey (sections have moved, components renamed).

In either case, propose a happy-path overhaul in close-out section 1c
(conversation starters). Don't silently let it rot.

## Anti-patterns

- **Treating `HAPPY_PATH.md` as a TODO list.** It's the agreed *current*
  flow + tests. New ideas go in `implementation/open_questions.md` or as
  EARS lines in `SPEC.md`, not here.
- **Per-component tests that aren't deterministic.** The whole point is
  that the suite can be re-run cheaply between iterations. If a test
  needs a real network call, mock it.
- **Letting the verification log lapse.** A missing row in the log means
  no one knows whether the happy path still passes. Treat the row as part
  of the close-out, not optional ceremony.
- **Letting the per-component table drift from the EARS lines.** When you
  add an EARS line in `SPEC.md`, add a row. When you delete one, delete
  the row. The mapping is the discipline.
