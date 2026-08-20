# agent-team-workflow

A Claude Code skill for running sub-agents alongside a warm main agent — keeping the human's questions answerable while a sub-agent does isolated work, and catching the silent-failure modes of worktree isolation.

## Why

When the assistant dispatches a sub-`Agent` (especially with `isolation: "worktree"`), there's a recurring set of footguns that silently bite later:

- The sub-agent inherits uncommitted state from the main worktree and merges it back unintentionally.
- The agent's `isolation` flag is ignored and the work lands on the main worktree's checkout — but the report still claims it happened in an isolated worktree.
- The agent reports `commit_sha: abc1234` but `git log <branch>` doesn't contain it (pre-commit hook silently failed; agent confused staged-but-uncommitted for committed).
- The agent returns "completed" for long-running CLI work while the CLI it backgrounded is still running.
- Worktrees accumulate locked at `.claude/worktrees/agent-*` until manual cleanup.
- The main agent merges without restarting the live process, so the human is staring at a UI that doesn't reflect the change.

This skill turns the pattern into a procedure: pre-dispatch checks, an explicit return contract, verification steps after the agent returns, and a recovery section for when isolation drifts.

## What it covers

- **Decision: sub-agent vs main** — a small table that prevents 30-second dispatches for 10-second work.
- **Pre-dispatch checklist** — target-repo check (session cwd must BE the target repo for worktree isolation), `git status` resolution, branch naming, integration-branch declaration, return-contract demand, budget.
- **Dispatching** — `Agent` tool with `isolation: "worktree"` when the session cwd is the target repo; cross-repo dispatches go without isolation plus prompt boilerplate that cuts a worktree off the named target checkout; parallel via single-message multi-call.
- **Post-return verification** — required-fields check, `git log` commit-SHA cross-check, isolation-drift detection, current-branch verification, merge with `--no-ff`, restart live process, `TaskCreate` follow-ups, cleanup.
- **Long-running CLI variant** — the "STARTED + initial-state-OK" idiom + a `Monitor` filter that catches both success AND failure signatures.
- **Recovery from isolation drift** — when the `isolation: "worktree"` flag is ignored and the work lands on the main checkout.

## Install

```
/plugin install agent-team-workflow@hansharhoff/skills
/reload-plugins
```

## Triggers

- The assistant is about to call the `Agent` tool (especially with `isolation: "worktree"`).
- The user says: "dispatch", "spawn an agent", "do this in parallel", "in a sub-agent", "fan this out", "hand this off".

## What it looks like in practice

Before the skill — typical sub-agent dispatch:

```
[user] dispatch a sub-agent to add the Pareto-tab tests
[assistant] [calls Agent tool] ...
[Agent returns: "done, see branch X"]
[assistant] Great, merging now... [merges]
[later] ??? where did these extra files come from
```

After the skill — same trigger phrase:

```
[user] dispatch a sub-agent to add the Pareto-tab tests
[assistant]
  Pre-flight:
  - git status: clean
  - Branch: test/pareto-tab-coverage off feat/pareto-viewer-tab
  - Return contract: files + test counts + commit SHA
  - Budget: 15 min
  [dispatches Agent with explicit prompt]

[Agent returns: branch test/pareto-tab-coverage, commit abc1234, 3 files, 8 tests added]
[assistant]
  Post-flight:
  - git log --oneline -1 test/pareto-tab-coverage: abc1234 ✓
  - git worktree list: agent worktree present ✓
  - git branch --show-current: feat/pareto-viewer-tab ✓
  Merging ... done. Worktree removed. git status clean.
```

The footguns become checks; the silent failures get caught.

## Scope

This skill is the **in-session** layer. Inter-session orchestration (a long-running coordinator on a dedicated host, e.g. the "Mayor + workers" pattern) is a separate, larger architecture. This skill still applies inside any individual worker session in such a setup — it composes downward.
