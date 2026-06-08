# agent-team-workflow

A skill for Claude Code that codifies how to run sub-agents alongside a warm main agent — so the human's questions aren't blocked by implementation work, and the silent-failure modes of worktree isolation (locked worktrees, uncommitted carry-over, premature "completed" reports) don't bite.

## Why

When the assistant dispatches a sub-`Agent` (especially with `isolation: "worktree"`), there's a recurring set of footguns:

- The sub-agent inherits uncommitted state from the main worktree and merges it back unintentionally.
- The agent picks a branch name out of nowhere and the main agent has to find it after the fact.
- The agent returns "completed" while the background CLI it kicked off is still running.
- Worktrees accumulate at `.claude/worktrees/agent-*`, locked, until manual cleanup.
- The main agent merges without restarting the live process, so the human is staring at a viewer that doesn't reflect the change.

This skill bakes the pre-dispatch checks, the explicit branch convention, the return contract, and the post-merge cleanup into one procedure that fires automatically when the assistant is about to dispatch.

## What it covers

- **When to use a sub-agent vs do work in main** — a small decision table that prevents 30-second dispatches for 10-second work.
- **Pre-dispatch steps** — `git status` check, branch naming, integration-branch declaration, return-contract demand, budget.
- **Dispatching** — `Agent` tool with `isolation: "worktree"`, parallel via single-message multi-call.
- **Post-return** — merge with `--no-ff`, live-process restart, worktree + branch cleanup, final `git status` to catch carry-over.
- **Long-running CLI variant** — the "STARTED + initial-state-OK" idiom + a `Monitor` on the log.

## Scope

This skill is the **in-session** layer. Inter-session orchestration (multiple Claude processes coordinated by a long-running Mayor on a dedicated host) is a separate, larger architecture. See `ai/docs/agentic-levelup-proposal.md` path 4 if you're in the Bestseller ai workspace.

## Install

```
/plugin install agent-team-workflow@hansharhoff/skills
/reload-plugins
```

## Triggers

The skill auto-fires when:

- The assistant is about to call the `Agent` tool (especially with `isolation: "worktree"`).
- The user says any of: "dispatch an agent", "spawn an agent", "do this in parallel", "do this in a sub-agent", "fan this out", "hand this off".
