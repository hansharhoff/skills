---
name: agent-team-workflow
description: >
  Use BEFORE dispatching any sub-Agent (especially with isolation:
  "worktree"), and when the user says "dispatch", "spawn an agent",
  "do this in parallel", "do this in a sub-agent", "fan this out",
  "hand this off", or similar phrasings. Keeps the main agent
  responsive while the sub-agent runs orthogonal work, and avoids the
  silent-failure modes of worktree isolation (locked worktrees,
  uncommitted carry-over, premature "completed" reports for long-running
  CLI work). Codifies the in-session strategy (when to dispatch vs do
  work in main) AND the mechanics (pre-dispatch git-status check,
  explicit branch convention, return contract, post-merge cleanup).
  Scope: a single Claude Code session. Inter-session orchestration
  (Mayor / workers, proactive agents on a long-lived host) is a
  separate concern — see `ai/docs/agentic-levelup-proposal.md` path 4.
---

# agent-team-workflow

Run sub-agents alongside a warm main agent so the human's questions aren't blocked by implementation work, AND avoid the silent-failure modes of worktree isolation.

## When to use a sub-agent vs do work in main

| Work | Where |
|---|---|
| Tiny tweak (rename label, fix typo, one-line config change) | **Main agent.** Sub-agent overhead exceeds saved time. |
| Multi-step but short (under 2 min wall-clock) | **Main agent.** Same reason. |
| Multi-step + reads multiple files OR generates a substantial diff | **Sub-agent.** Frees main to answer human questions. |
| Long-running CLI invocation (over 5 min — sweeps, downloads, builds) | **Sub-agent in background**, plus a `Monitor` for completion. See the long-running section below. |
| Two or more orthogonal tasks at the same time | **Multiple sub-agents in parallel.** One Agent tool call per task, all in a single message. |

If you spawn a sub-agent for tiny work, the dispatch + return + merge overhead is at least 30 seconds even when everything works. Reserve sub-agents for work that's at least multi-step OR runs long enough to actually block back-and-forth with the human.

## Before dispatching

1. **Check the main worktree's state.** Run `git status --porcelain`. If anything is uncommitted, decide:
   - Is this work the sub-agent should branch off? → commit it first, OR pass `HEAD` explicitly as the base in the prompt.
   - Is this work the sub-agent should NOT see? → stash it first (`git stash push -m "<reason>"`).

   Don't let the sub-agent inherit unrelated dirty state — it leads to merge collisions later.

2. **Decide the branch name** before invoking the Agent. Pattern: `<prefix>/<short-slug>` where `<prefix>` matches the convention you're using on the integration branch (e.g. `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, or a topic prefix like `viewer/<slug>` when working on a feature stream). Put the branch name **explicitly in the agent's prompt** — don't let the sub-agent pick.

3. **State the integration branch** in the prompt explicitly. "Branch off `<integration-branch>`" — don't leave it implicit. The sub-agent's git context defaults to whatever `HEAD` was at dispatch, which may not be what you want.

4. **State the return contract** in the prompt. Demand the sub-agent's final report include:
   - Files created / modified (full paths).
   - Test counts (if tests added/changed).
   - The branch name (so you can merge it).
   - The commit SHA (helps when force-pushes are needed later).
   - Any deviations from the prompt, with one-line reasons each.
   - Any open questions the agent punted on.

5. **Set a budget** in the prompt. "Aim for under 15 min, report at first clean checkpoint." This makes the agent surface partial progress instead of polishing for an hour.

6. **For long-running CLI work**, add to the prompt: "Background the CLI via `run_in_background: true`. Return STARTED + initial-state-OK after the first 10 healthy log lines. Do NOT wait for completion. Hand back the log path so the main agent can `Monitor` it." This avoids the "agent returned completed but the CLI is still running" trap.

## Dispatching

- Use `Agent` tool with `isolation: "worktree"` for any work that modifies files. The flag creates a temporary worktree at `.claude/worktrees/agent-<hash>` so the main worktree's files stay untouched.
- For multiple parallel sub-agents, send a **single message with multiple Agent tool calls** — they run concurrently. Sequential messages dispatch sequentially.
- If you need the sub-agents' outputs to feed each other, dispatch sequentially across multiple messages. If they're truly orthogonal, dispatch in one message.

## When the sub-agent returns

1. **Verify the report has all the required fields.** If anything is missing (no commit SHA, no test counts, no list of files), ask the agent to fill it in BEFORE merging. Don't merge a report you can't audit.

2. **Switch to the integration branch in the main worktree.**
   ```
   git checkout <integration-branch>
   ```

3. **Merge the sub-agent's branch.** Default:
   ```
   git merge <agent-branch> --no-ff -m "Merge <agent-branch> — <one-line summary>"
   ```
   The `--no-ff` keeps the sub-agent's history visible in the merge graph and makes it easy to revert as a unit later.

4. **Restart any live processes the merge affects.** If the integration branch is running a server / viewer / dev process, kill + relaunch so the new code is what the human is interacting with. Don't leave the human staring at a viewer that doesn't have their change.

5. **Cleanup:**
   - Delete the sub-agent's branch: `git branch -d <agent-branch>` (use `-D` only if the merge was via squash and you're sure).
   - Remove the worktree: `git worktree remove --force .claude/worktrees/agent-<hash>`.
   - Run `git status` in the main worktree one more time. If there are stray untracked files the sub-agent left behind (scratch scripts, log files, build artifacts), decide: commit, add to `.gitignore`, or `rm`. Don't let them accumulate.

## When the sub-agent returns from long-running CLI work

The "STARTED + initial-state-OK" return idiom means the agent exits while the CLI is still running. Specifically:

1. Don't treat the agent's "completed" as "the work is done". Treat it as "the work is RUNNING and looks healthy so far".
2. Read the agent's return for the log path + PID.
3. Arm a `Monitor` on the log path with a filter that catches both success signals AND failure signatures (`Traceback`, `Error`, `FAILED`, `Killed`, `OOM`). Silence is not success.
4. When the `Monitor` fires success, that's the real "done" — proceed with merge / restart / etc.

## Anti-patterns

- **Spawning a sub-agent for tiny work.** Cost > benefit below ~2 min.
- **Leaving the worktree mounted.** `git worktree list` should not accumulate stale agent worktrees. Every merge ends with the agent's worktree removed.
- **Accepting "agent completed" at face value for long-running CLI work.** The agent process can complete while the CLI it backgrounded is still running.
- **Force-pushing the agent's branch without `--force-with-lease`.** If the agent's branch is shared (uncommon but possible), `--force-with-lease` is the safer floor.
- **Letting the sub-agent pick its own branch name.** Different agents pick incompatible patterns; the main agent then has to mentally translate. State the name in the prompt.
- **Skipping the post-return `git status` in main.** This is where you catch the untracked-file-from-the-sub-agent regression.

## Scope

This skill governs sub-`Agent` dispatches inside a **single Claude Code session**.

Inter-session orchestration — multiple Claude processes coordinated by a long-running Mayor (per [Steve Yegge's Gas Town](https://substack.com/@steveyegge/note/c-118918593) terminology) — is a separate concern, sketched in `ai/docs/agentic-levelup-proposal.md` path 4. The patterns rhyme (coordinator + isolated workers + structured returns), but the lifecycles and mechanics differ enough that the inter-session piece deserves its own treatment.

When the Mayor work lands, individual worker sessions will still benefit from this skill internally — every worker that spawns its own sub-agents via the `Agent` tool inherits these same merge / cleanup mechanics. The skill composes downward inside that architecture.
