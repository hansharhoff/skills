---
name: repo-cleanup
description: >
  Audit and clean up a repository: find typos, inconsistencies, outdated references, dead code,
  failing tests, type errors, linter issues, and documentation gaps. Use this skill when the user
  asks to "clean up the repo", "audit the codebase", "check for issues", "consolidate docs",
  "find inconsistencies", or invokes /cleanup or /repo-cleanup. Also trigger on requests like
  "are there any stale TODOs", "what tests are failing", "check docs are up to date",
  "run all the checks", "find code duplication", "consolidate docs", or "check for
  redundant code".
---

# Repo Cleanup

Systematically audit a repository for quality issues, fix trivial problems automatically, and
present a prioritized report of remaining findings for the user to triage.

## Workflow

### 1. Discover project tooling

Read project config files to understand what tools are available:
- `pyproject.toml`, `.pre-commit-config.yaml`, `.flake8`, `setup.cfg`, `Makefile`, etc.
- Identify: package manager (uv/pip/poetry), linters (ruff/flake8/pylint), formatters (ruff/black),
  type checkers (ty/pyright/mypy), test runner (pytest), pre-commit hooks
- Note the run commands (e.g., `uv run pytest`, `npm test`, `cargo test`)

### 2. Run automated checks in parallel

Launch parallel agents or commands for each available tool:

| Check | Example command | Priority |
|-------|----------------|----------|
| Pre-commit hooks | `pre-commit run --all-files` | High |
| Tests + coverage | `uv run pytest tests -m "not slow" --tb=short -q --cov=src --cov=common --cov-report=term-missing` | High |
| Type checker | `ty check` (preferred, use `uvx ty check` if not installed), `uv run pyright`, or `uv run mypy .` | Medium |
| Linter | `uv run ruff check .` | High |
| Formatter | `uv run ruff format --check .` | Low |

Capture stdout/stderr from each. Do not stop on failure — collect everything.

### 3. Manual audit

While automated checks run, perform these manual inspections. See
[references/checklist.md](references/checklist.md) for the detailed checklist.

**Documentation**
- Read all `*.md` files. Check for typos, broken references to files/functions/flags that no
  longer exist (verify with Glob/Grep), outdated instructions, and inconsistencies between docs.
- Spot-check docstrings in core modules: do parameter names match signatures?
- Grep for `TODO|FIXME|HACK|XXX` — report stale ones.

**Config consistency**
- Compare `.env.example` with actual env var usage in code.
- Check that CI workflow Python versions match `pyproject.toml` / `.python-version`.
- Flag redundant config (e.g., `.flake8` when ruff covers the same rules).

**Dead code**
- Look for commented-out code blocks, unused imports, files not imported anywhere
  (that aren't entry points or scripts).

**Documentation consolidation**
- Identify repeated content across markdown files — propose single source of truth.
- Flag copy-pasted paragraphs or near-identical sections.

**Code duplication**
- Look for near-identical functions or code blocks across modules.
- Identify copy-pasted logic that could be extracted into a shared utility.
- Flag modules with overlapping responsibilities.

### 4. Present the report

Group findings by priority and category. Use this format:

```markdown
## Repo Cleanup Report

### Trivial (will auto-fix)
- [list of trivial fixes that can be applied without judgment]

### High priority
#### Failing tests
- `test_foo.py::test_bar` — AssertionError: expected X got Y
- ...

#### Linter errors
- ...

### Medium priority
#### Test coverage gaps
- `src/foo.py` — 23% covered (missing: `process_data`, `validate_input`, lines 45-80)
- `common/bar.py` — no test file exists
- ...

#### Documentation issues
- README.md:42 — references `--legacy` flag removed in commit abc123
- ...

#### Type errors (high priority only — skip minor issues unless trivially fixable)
- src/foo.py:15 — Argument of type "str" is not assignable to parameter "x" of type "int"
- ...

#### Code duplication
- src/foo.py:10 and src/bar.py:25 — near-identical data loading logic, extract to common/
- ...

#### Documentation consolidation
- README.md:15-30 and research/readme.md:5-20 — duplicate setup instructions
- ...

### Low priority
#### Stale TODOs
- src/bar.py:88 — `# TODO: remove after migration` (added 2024-01-15)
- ...

#### Dead code
- ...
```

### 5. Ask the user

After presenting the report, ask targeted questions about items that need judgment:

- **Test coverage**: "These modules have low coverage. Which are worth adding tests for?
  Should I write unit tests for X, Y, Z? Any that are intentionally untested (e.g., research scripts)?"
- **Code duplication**: "I found these duplicated patterns. Should I extract shared utilities,
  or is the duplication intentional (e.g., scripts that may diverge)?"
- **Failing tests**: "These tests have been failing. Should I fix them, skip them with a reason,
  or remove them?"

Then ask:

> Should I fix all remaining issues, a specific priority level, or specific items?

### 6. Fix issues

After the user responds:

1. **Immediately auto-fix trivial items in parallel** (formatting, typos, import sorting,
   dead commented-out code) — these don't need approval.
2. **Apply user-approved fixes** for non-trivial items. For complex changes (refactoring
   duplication, writing new tests), explain the approach briefly before applying.
3. Run `pre-commit run --all-files` to verify all fixes are clean.

## Resources

### references/
- [checklist.md](references/checklist.md) — Detailed audit checklist organized by category
