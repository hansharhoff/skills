---
name: nurse-prs
description: >
  Use when the user says "nurse the PRs", "nurse #N to completion", "babysit
  the PRs", "shepherd the PRs", "keep the PRs moving", "tend the PR queue",
  "drive the open PRs to done", or hands over a repo's pull requests to look
  after. Drives a repo's open PRs (and the issues around them) toward a
  landable state WITHOUT approving or merging: respond to review comments,
  validate changes end-to-end and post the evidence, keep every branch
  mergeable (resolve conflicts as siblings land), flip validated drafts to
  ready, triage related issues, keep a persistent monitor up so new activity
  is handled autonomously, and surface every merge/approve/design decision to
  the human as a crisp judgement ask. Scope: one repo's PR queue, ongoing
  across a session.
---

# nurse-prs

Act as a diligent PR shepherd: take a repo's open PRs and move each one as far
toward *landable* as you can on your own, then hand the human exactly the
decisions that are theirs to make. You are the junior dev who keeps the queue
healthy; the human is the one who approves and merges.

## Prime directive — what you never do

**Never approve, merge, close others' work, force-push, or push to
`main`/`master`.** Those are the human's calls. When a PR is ready to merge or
an issue is ready to close, *say so* and let them click — don't do it yourself
even if you're confident. (If the human explicitly tells you to merge/close a
specific item in this session, that instruction overrides this for that item
only.)

Everything else that moves a PR forward is in scope and should be done without
waiting to be asked.

## The loop (run each pass)

1. **Enumerate.** `gh pr list --state open --json number,title,isDraft,mergeable,mergeStateStatus,reviewDecision,reviews,headRefName` plus `gh issue list --state open` for related issues.
2. **Assess each PR.** `gh pr view <n> --json isDraft,mergeable,mergeStateStatus,statusCheckRollup,reviewDecision,comments,reviews,commits`. Derive state from the **combination** of `mergeStateStatus` (the truth for "can this land": `CLEAN`/`BLOCKED`/`UNSTABLE`/`DIRTY`) and `reviews[]` (state + author — *who* approved / requested changes). **Never key off `reviewDecision` alone**: GitHub only populates it when branch protection *requires* a review, so it is empty for ordinary approvals — treat it as "is the required gate satisfied", never "has anyone approved". Rule of thumb:

   | State | Read it as |
   |---|---|
   | `CLEAN` | mergeable now — surface for human merge |
   | `BLOCKED` + 0 approvals in `reviews[]` | needs a reviewer |
   | `BLOCKED` + approvals present | a required code-owner is still outstanding — identify which path |
   | `UNSTABLE` | inspect the non-required failing check |
   | `DIRTY`/`CONFLICTING` | rebase / merge the base branch in |

3. **Act, in priority order:**
   - **CI red** → read the failure, fix it, push to the branch, comment what you found.
   - **`CONFLICTING`/`DIRTY`** → merge the base branch in, resolve conflicts, push. Re-check after *every* sibling PR merges — a green queue goes conflicting the moment one lands.
   - **Review comments / `CHANGES_REQUESTED`** → address them with commits, or reply with the reasoning if you disagree. Don't leave a review unanswered.
   - **Draft + validated** → flip to ready (`gh pr ready <n>`). Don't park a finished PR as a draft.
   - **Green, mergeable, reviewed** → it's the human's to merge; surface it (see *Judgement asks*).
4. **Validate before you call anything "ready."** Actually exercise the change end-to-end, then **post the result as a PR comment** — the reviewer can't see your terminal, so restate the recap in text. "Looks fine" ≠ "validated." See *Validation by repo type*.
5. **Keep it tidy.** Descriptive branch names (rename ugly auto-generated ones — but note a branch rename can auto-close the PR, so recreate + breadcrumb if it does). Clean up throwaway worktrees.

## Validation by repo type

- **App code** → run the project's tests / typecheck / linters; drive the actual affected flow if there's a runtime surface.
- **Ansible / infra** → `--check --diff` first (dry-run), then a **real apply if the human authorizes it** (it mutates a live host). Spot-verify the effect on the box afterwards. Beware check-mode blind spots: tasks that no-op under `--check` (e.g. a `command` with `creates:`) can make dependent tasks *falsely* fail in check mode and *falsely* pass by being skipped — a clean `--check` is necessary, not sufficient. Say which commit you tested.
- **Docs / config** → render/parse it; confirm links and structure.
- Always distinguish **verified** (you ran it and saw the result) from **inferred** (it should work). Post the evidence.

## Triaging related issues

- **Comment with an assessment + a disposition**, not just acknowledgement.
- **Small, well-scoped, unambiguous** fix (a doc note, a wrapper, a guard, a config line)? → implement it as a **draft PR**, cross-link the issue. This is the highest-leverage autonomous move.
- **"Is this already fixed?"** → check current `main` *and* the live system, comment with concrete proof (command + output), and **recommend closing** (don't close an issue you didn't open without the human's OK). Watch for the stale-session pattern: a capability shipped, but whoever filed the issue didn't know.
- **Ambiguous / architectural / grants access / hard to reverse** → summarize the options and **ping the human**; do not build it unilaterally.

## Judgement asks — when to pull the human in

Pull them in (a crisp question with a recommended default, not an open-ended
"what should I do") for:
- any **merge or approve** decision;
- **design forks** with real trade-offs;
- anything that **grants access, changes security posture, or is hard to undo**.

Keep nursing everything else while you wait — a pending decision blocks one
item, not the whole queue. Batch decisions when you can (e.g. ask up to a few
at once) rather than interrupting per-item.

## Keep a monitor up (autonomous response across turns)

Arm a **persistent monitor** that polls `gh` for new activity by *others* (new
PRs/issues, conversation comments, inline review comments, submitted reviews)
so you respond without being re-prompted. `bin/pr-watch.sh <owner/repo>` does
this — one stdout line per new item since the previous tick, own-authored
activity filtered out, transient `gh` failures swallowed. Run it as a
`persistent` background monitor; each event is a cue to run another loop pass
on the affected PR/issue.

**Bot/App-identity accounts** (no personal `gh` auth; working through a GitHub
App installation token): plain `gh` is unauthenticated, `/user` returns 403,
and App tokens expire after ~1h. Use the built-in hooks — a token-mint command
re-run each tick, plus an explicit own-identity override:

```bash
PR_WATCH_TOKEN_CMD=appretio-mint-token PR_WATCH_ME='appretio-bot[bot]' bash pr-watch.sh <owner/repo>
```

The script aborts loudly if it cannot read the repo, so a dead watch is
visible instead of silently quiet.

## Reporting

- **Restate results in your own text** — a classifier/human reading only your
  messages can't see tool output or subagent reports.
- After each pass: **what changed · what's pending · what needs a decision.**
- When something's genuinely done and verified, say so plainly with the
  evidence; don't hedge, and don't call it done from a dry-run that skipped
  the real behavior.

## Anti-patterns

- Flipping a draft to ready without actually validating it.
- Leaving a PR `CONFLICTING` because "GitHub will sort it out."
- Merging / approving / closing on the human's behalf.
- Building an ambiguous or access-granting feature without a judgement ping.
- Claiming success from a `--check` run that never exercised the real change.
- Announcing an action instead of taking it (the whole point is to *do* the
  safe work, not narrate intentions).

## Scope

One repository's PR queue plus the issues around it, ongoing within a session.
Pairs well with **agent-team-workflow** (dispatch heavy validation to isolated
sub-agents) and **whats-next** (rank what to pick up first). It does not own
the merge button — that stays with the human.
