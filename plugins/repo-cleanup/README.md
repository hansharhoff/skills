# repo-cleanup

A Claude Code skill that systematically audits a repository for quality issues, fixes trivial problems automatically, and presents a prioritized report.

## What it does

When you invoke this skill, it:

- Discovers project tooling (linters, formatters, type checkers, test runners)
- Runs all automated checks in parallel
- Performs manual audit for documentation issues, dead code, duplication, config consistency
- Presents a grouped, prioritized report
- Asks targeted questions about items needing judgment
- Fixes issues based on your triage decisions

## Usage

```
/repo-cleanup
```

Also triggers on requests like "clean up the repo", "audit the codebase", "check for issues", "find inconsistencies", "are there any stale TODOs", etc.
