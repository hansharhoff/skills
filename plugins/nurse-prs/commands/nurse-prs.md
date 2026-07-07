---
description: Nurse a repo's open PRs toward completion (validate, resolve conflicts, flip drafts to ready, triage issues, keep a monitor up) — never approving or merging.
---

Invoke the **nurse-prs** skill for the current repository (or the repo named in
the arguments).

Run one full loop pass now:

1. Enumerate open PRs + related open issues (`gh`).
2. For each PR, assess CI / mergeability / reviews and act in priority order —
   fix red CI, resolve conflicts, address review comments, validate, flip
   validated drafts to ready.
3. Validate changes end-to-end and post the evidence as a PR comment.
4. Triage related issues (implement small unambiguous ones as draft PRs;
   verify "already fixed" ones with proof; ping for the ambiguous/architectural
   ones).
5. Arm `bin/pr-watch.sh <owner/repo>` as a persistent monitor if one isn't
   already running, so new activity is handled autonomously.

Never approve, merge, close others' issues, force-push, or push to
main/master. Close with **what changed · what's pending · what needs your
decision**, and surface any merge/approve/design calls as crisp questions.

Arguments (optional): `<owner/repo>` to target a specific repo, or `#N` to
focus a single PR.
