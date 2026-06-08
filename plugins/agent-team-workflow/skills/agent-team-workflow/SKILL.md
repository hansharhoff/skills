---
name: agent-team-workflow
description: >
  Triggers BEFORE the assistant calls the Agent tool with
  isolation: "worktree", AND when the user says "dispatch", "spawn an
  agent", "do this in parallel", "in a sub-agent", "fan this out",
  "hand this off". Procedure for keeping the main agent responsive
  while sub-agents do isolated work: pre-dispatch git-status check,
  explicit branch convention, return contract with commit-SHA
  verification, post-merge cleanup, isolation-drift recovery.
  Scope: a single Claude Code session.
---

# agent-team-workflow

Run sub-agents alongside a warm main agent so the human's questions aren't blocked by implementation work, AND catch the silent-failure modes of worktree isolation (locked worktrees, uncommitted carry-over, premature "completed" reports for long-running CLI, isolation drift).

## When to use a sub-agent vs do work in main

| Work | Where |
|---|---|
| Tiny tweak (rename label, fix typo, one-line config change) | **Main agent.** Sub-agent overhead exceeds saved time. |
| Multi-step but short (under 2 min wall-clock) | **Main agent.** Same reason. |
| Multi-step + reads multiple files OR generates a substantial diff | **Sub-agent.** Frees main to answer human questions. |
| Long-running CLI invocation (over 5 min — sweeps, downloads, builds) | **Sub-agent in background**, plus a `Monitor` for completion. See the long-running section. |
| Two or more orthogonal tasks at the same time | **Multiple sub-agents in parallel.** One Agent tool call per task, all in a single message. |

Dispatch + return + merge has a ~30 s floor even when everything works. Reserve sub-agents for work that's at least multi-step OR runs long enough to actually block back-and-forth with the human.

## Before dispatching

1. **Run `git status --porcelain`.** If empty → proceed. If non-empty:
   - List the modified/untracked files in chat.
   - Ask the human: "should the sub-agent inherit these changes (I'll commit first), work without seeing them (I'll stash), or branch off the dirty HEAD as-is?"
   - Don't guess. Wait for the answer. Carrying unintended dirty state through a sub-agent is the most common silent-merge-conflict source.

2. **Decide the branch name before invoking `Agent`.** Pattern: `<prefix>/<short-slug>` where `<prefix>` matches the convention on the integration branch (`feat/<slug>`, `fix/<slug>`, `chore/<slug>`, or a topic prefix like `viewer/<slug>`). Put the branch name **explicitly in the prompt**. Don't let the sub-agent pick — different agents pick incompatible patterns and the main has to translate later.

3. **State the integration branch in the prompt explicitly.** "Branch off `<integration-branch>`". The sub-agent's git context defaults to whatever `HEAD` is at dispatch, which may not be what you want.

4. **State the return contract.** Demand the report include:
   - Files created / modified (full paths).
   - Test counts (added / total) if tests changed.
   - The branch name + the **commit SHA** (so you can verify the commit actually exists).
   - Deviations from the prompt, one-line reason each.
   - Open questions the agent punted on.

5. **Set a budget.** "Aim for under 15 min, report at first clean checkpoint." Surfaces partial progress instead of polishing for an hour.

6. **For long-running CLI work**, add: "Background the CLI via `run_in_background: true`. Return STARTED + initial-state-OK after the first ~10 healthy log lines. Do NOT wait for completion. Hand back the log path + PID so the main agent can `Monitor` it."

## Dispatching

- `Agent` tool with `isolation: "worktree"` for any work that modifies files.
- Multiple parallel sub-agents → **single message with multiple Agent tool calls** (concurrent). Sequential messages → sequential dispatch.
- If sub-agent outputs need to feed each other → sequential. Truly orthogonal → parallel.

## When the sub-agent returns

1. **Verify the report has all required fields.** If any of `branch name`, `commit SHA`, `files modified`, `test counts` is missing, ask the agent to fill it in BEFORE proceeding.

2. **Verify the commit actually exists.**
   ```
   git log --oneline -1 <agent-branch>
   ```
   If the SHA doesn't match the report (or the branch doesn't exist), the agent's `git commit` didn't actually run — likely a pre-commit hook silently failed OR the agent confused staged-but-uncommitted for committed. Recover by switching to the agent's worktree (or the agent's branch if isolation drifted), inspecting, and re-running the commit.

3. **Check isolation actually held.**
   ```
   git branch --show-current        # in the main worktree
   git worktree list                # confirm the agent's worktree exists
   ```
   - If the main worktree's current branch IS the agent's branch (not your integration branch), the isolation drifted — the agent committed on the main worktree's checkout. See "Recovering from isolation drift" below.
   - If `git worktree list` shows no agent worktree, the agent either cleaned up after itself (rare) or never created one (more likely; treat as isolation drift).

4. **Confirm you're on the integration branch before merging.**
   ```
   git branch --show-current
   ```
   Must match your intended target. Don't skip — committing to the wrong branch is a common own-goal (especially if you've been hopping branches while the sub-agent ran).

5. **Merge.**
   ```
   git merge <agent-branch> --no-ff -m "Merge <agent-branch> — <one-line summary>"
   ```
   `--no-ff` keeps the sub-agent's history visible in the merge graph and makes it easy to revert as a unit.

6. **Restart any long-lived process the change affects.** If the integration branch backs a server / viewer / watcher / REPL, kill + relaunch. Skip if there's no such process.

7. **TaskCreate any follow-ups.** If the agent's report surfaced open questions or punted items, run `TaskCreate` BEFORE moving to the next thing. Reports that don't make it into TaskList get lost.

8. **Cleanup.**
   - `git branch -d <agent-branch>` (use `-D` only on squash merges and only if you're sure).
   - `git worktree remove --force .claude/worktrees/agent-<hash>`.
   - `git status` one more time. Untracked files the sub-agent left (scratch scripts, logs, build artifacts) get committed, gitignored, or `rm`'d. Don't let them accumulate.

## When the sub-agent returns from long-running CLI work

1. The agent's "completed" means "STARTED OK", not "DONE". The CLI is still running.
2. Read the report for `log_path` + `pid`.
3. Arm a `Monitor` on the log with a filter that catches **both success AND failure signatures** — silence is not success:
   ```
   tail -f <log_path> | grep -E --line-buffered "<success-marker>|Traceback|Error|FAILED|Killed|OOM"
   ```
   Replace `<success-marker>` with whatever the CLI logs on success (e.g. `Wrote .* to .*\.parquet`).
4. When the Monitor fires success → that's the real "done". Proceed with merge / restart / etc.

## Recovering from isolation drift

If the agent's `isolation: "worktree"` flag was ignored and the work landed on the main worktree's checkout:

1. **Don't push.** Anything pushed accidentally is harder to unwind.
2. **Identify what's there.** `git status` (uncommitted carry-over) + `git log --oneline origin/<branch>..HEAD` (commits not yet on remote).
3. **If a clean commit exists** on the main worktree but on the wrong branch: cherry-pick it onto the intended branch + reset the wrong branch. Use `git reflog` if you accidentally hard-reset.
4. **If uncommitted changes only**: stash → switch to the right branch → unstash → commit.
5. **Document in the report.** The next dispatch should anticipate the drift (the harness may not honor isolation reliably) — pass the branch name + base explicitly and verify post-return.

## Anti-patterns

- **Spawning a sub-agent for tiny work.** Cost > benefit below ~2 min.
- **Skipping the pre-dispatch `git status`.** Surprise carry-over later.
- **Trusting the agent's "completed" claim without checking `git log`.** Pre-commit hooks fail silently.
- **Trusting the agent's "completed" for long-running CLI.** The agent process can complete while the CLI is still running.
- **Merging without first running `git branch --show-current`.** Lands the merge on whatever branch you happen to be on (which may not be the integration branch).
- **Letting the sub-agent pick its own branch name.** Translation tax on every return.
- **Skipping the post-return `git status` in main.** Sub-agent untracked files accumulate.
- **Skipping `TaskCreate` for surfaced follow-ups.** Open loops vanish.

## Scope

This skill governs sub-`Agent` dispatches inside a **single Claude Code session**.

Inter-session orchestration — multiple Claude processes coordinated by a long-running coordinator on a dedicated host (the "Mayor + workers" pattern, after Steve Yegge's Gas Town write-up) — is a separate, larger concern. If your team has its own Mayor/worker design doc, the relationship is: every worker session in that architecture is itself a Claude Code session, and inside it this skill still applies to any `Agent` tool dispatches the worker makes. The skill composes downward.
