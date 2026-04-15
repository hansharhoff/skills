# Repo Cleanup Checklist

Use this as the master checklist. Run each section, collect findings, then present the grouped report.

## 1. Documentation (Priority: Medium)

### Markdown files
- Glob for `**/*.md` and read each
- Check for typos, grammar issues, broken links
- Check references to files/functions/CLI flags that no longer exist (verify with Glob/Grep)
- Check for outdated version numbers, tool names, or instructions
- Check for inconsistencies between docs (e.g., README says one thing, research/readme.md says another)

### Docstrings
- Grep for functions/classes missing docstrings in `src/`, `common/`, `scripts/`
- Check that docstring parameter names match actual function signatures
- Check for docstrings referencing renamed/removed parameters

### Inline comments
- Look for TODO/FIXME/HACK/XXX comments — report age if possible via git blame
- Look for commented-out code blocks (dead code)
- Check for comments that contradict the code they describe

### CLAUDE.md
- Verify tool recommendations match actual project config
- Verify pre-commit workflow matches `.pre-commit-config.yaml`

## 2. Pre-commit & Linting (Priority: High)

### Pre-commit config
- Read `.pre-commit-config.yaml`
- Check for hooks referencing tools not in dependencies
- Check for commented-out hooks that should be enabled or removed
- Check hook versions against latest available (use `pre-commit autoupdate --dry-run` if available)
- Run `pre-commit run --all-files` and report failures

### Linter config consistency
- Compare `.flake8` rules with `ruff` config in `pyproject.toml` — flag redundant/conflicting rules
- Check if `.flake8` is still needed (ruff may cover everything)
- Check for linter plugins in dependencies that aren't referenced in config

### Run linters
- `uv run ruff check .` — report issues
- `uv run ruff format --check .` — report formatting issues

## 3. Tests (Priority: High)

### Test health
- Run `uv run pytest tests -m "not slow" -v --tb=short` and collect failures
- Identify tests that have been failing for a long time (check git history if needed)
- Look for skipped tests with no explanation
- Check for empty test files or test files with no test functions

### Test coverage gaps
- Run tests with coverage: `uv run pytest tests -m "not slow" --cov=src --cov=common --cov-report=term-missing -q`
- Identify source files in `src/` and `common/` with no corresponding test file
- Flag public functions/classes with no test coverage
- For each low-coverage module, list the uncovered functions and line ranges
- Rank coverage gaps by importance: production-critical code > utilities > research

### Test quality
- Check for tests that don't assert anything
- Check for tests with overly broad exception catching

## 4. Type Hints (Priority: Medium)

- Run type checker — prefer `ty check` (use `uvx ty check` if the repo doesn't have ty installed),
  otherwise fall back to `uv run pyright` or `uv run mypy`
- Report type errors grouped by file
- **Only fix high-priority type errors** (e.g., wrong argument types, missing attributes, incompatible
  return types). Skip minor issues (e.g., missing annotations, broad `Any` types) unless the fix is
  trivial (one-line change, obvious correct type).
- Flag functions missing return type annotations in `src/` and `common/` (report only, don't auto-fix)
- Flag functions with `Any` types that could be more specific (report only, don't auto-fix)

## 5. Dependencies (Priority: Low)

- Check `pyproject.toml` for pinned versions that may be outdated
- Look for unused dependencies (imports not found in codebase)
- Check for dependencies listed in multiple places

## 6. Config & Environment (Priority: Medium)

- Compare `.env.example` variables with actual usage in code (Grep for `os.environ`, `os.getenv`, Pydantic settings fields)
- Check for env vars used in code but missing from `.env.example`
- Check for env vars in `.env.example` that are no longer used
- Validate JSON configs in `resources/` parse correctly
- Check for hardcoded paths, URLs, or credentials in source code

## 7. Dead Code (Priority: Low)

- Look for imported but unused modules
- Look for defined but uncalled functions (consider `vulture` config in pyproject.toml)
- Look for files that are not imported anywhere and not entry points

## 8. Documentation Consolidation (Priority: Medium)

- Identify repeated content across markdown files (e.g., setup instructions in README and research/readme.md)
- Flag sections that say the same thing in different words — propose a single source of truth
- Look for copy-pasted paragraphs or near-identical sections across docs
- Check if information in comments duplicates what's already in docs

## 9. Code Duplication (Priority: Medium)

- Look for near-identical functions or code blocks across modules
- Identify copy-pasted logic that could be extracted into a shared utility
- Check for repeated patterns that differ only in a parameter or two
- Look for similar data transformation pipelines across scripts
- Flag modules with overlapping responsibilities that could be merged

## 10. CI/CD (Priority: Medium)

- Read `.github/workflows/*.yml`
- Check for references to tools/scripts that no longer exist
- Check Python version consistency across workflows, pyproject.toml, and .python-version
- Check for hardcoded values that should be in config
