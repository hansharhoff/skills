# whats-next

A Claude Code skill that acts like a lightweight project manager for the active workspace. It pulls signals from open PRs (via `gh`), in-session tasks, scheduled memory notes, Atlassian items (when the MCP is connected), git state, and previously captured "circle back" items, then renders a ranked dashboard that fits in roughly 80% of one screen and closes with a concrete one-line question targeting the top item.

The other half of the skill is **capture**: when you say "remind me to …", "let's circle back to …", or "for later", it paraphrases the intent and stashes it as either an in-session TaskList entry or a durable memory file in the standard Claude Code memory directory — dating heuristics decide which. The goal is to turn the scattered "I should X later" comments that accumulate during a session into things you'll actually see again.

## Installation

```bash
claude plugin install whats-next@hansharhoff/skills
```

## Usage

Invoke explicitly with the slash command:

```
/whats-next
```

Or trigger via natural language — either to read the dashboard:

```
> what's next?
> where were we?
> triage
> what should I do?
```

Or to capture a new TODO:

```
> remind me to check the bestseller frontier tomorrow
> let's circle back to the copy-skip design after the merge
> for later: rerun the umaps with the new blend weights
```

A SessionStart hook also auto-runs `bin/gather.py` once at the start of every session, so the first turn already has the day's open loops in context.
