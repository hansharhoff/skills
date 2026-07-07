# nurse-prs

A Claude Code skill for **shepherding a repo's open PRs to a landable state** —
doing all the safe work that moves a pull request forward, while leaving the
approve/merge button firmly with the human.

## Why

Handing an agent "keep my PRs moving" usually degrades into either too little
(it waits to be told every step) or too much (it merges something half-baked).
The healthy middle is a diligent junior dev: keep the queue green, validate
before declaring anything ready, chase down conflicts and review comments, and
surface exactly the decisions that are the maintainer's to make.

The recurring failure modes this skill guards against:

- A PR marked "ready" that was never actually run — "looks fine" ≠ validated.
- A PR left `CONFLICTING` after a sibling merged, silently stalling the queue.
- An agent merging/approving/closing on the human's behalf.
- Validation from a dry-run (`ansible --check`, a skipped test) mistaken for the real thing.
- New review comments / issues going unnoticed because nothing was watching.

## What it covers

- **The loop** — enumerate open PRs + related issues, assess CI / mergeability / reviews, and act in priority order: fix red CI, resolve merge conflicts as siblings land, address review comments, validate end-to-end **and post the evidence**, flip validated drafts to ready.
- **Validation by repo type** — tests/typecheck for app code; `--check` then an authorized real apply for infra (with the check-mode blind-spot caveat); render/parse for docs. Always distinguishes *verified* from *inferred*.
- **Issue triage** — implement small, unambiguous fixes as draft PRs; verify "already fixed?" issues with concrete proof; ping the human for ambiguous / architectural / access-granting ones.
- **Judgement asks** — a crisp question with a recommended default for every merge/approve decision, design fork, or hard-to-reverse change; keep nursing the rest meanwhile.
- **Autonomous watch** — `bin/pr-watch.sh <owner/repo>` polls for new PRs/issues/comments/reviews by others (your own writes filtered) so a persistent Monitor can cue the next loop pass without re-prompting.

## Prime directive

**Never approve, merge, close others' work, force-push, or push to
`main`/`master`.** Those are the human's calls. Everything else that moves a PR
forward is done without waiting to be asked. (An explicit "merge #N" from the
human overrides this for that item.)

## Install

```
/plugin install nurse-prs@hansharhoff/skills
```

Then say "nurse the PRs", "nurse #N to completion", "keep the PR queue moving",
or run `/nurse-prs [owner/repo | #N]`.

Pairs with **agent-team-workflow** (dispatch heavy validation to isolated
sub-agents) and **whats-next** (rank what to pick up first).
