#!/usr/bin/env python3
"""Collect CLI-available signals for the whats-next skill.

Reads the current workspace's open PRs (via `gh`), memory-scheduled notes
(from the Claude Code memory directory), and local git state. Emits a single
JSON object on stdout. Always exits 0 — per-collector errors push to the
`errors[]` array in the output.

See plugins/whats-next/SPEC.md for the full contract.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    # gh emits e.g. "2026-06-04T12:34:56Z"
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _days_since(dt: datetime, *, now: datetime | None = None) -> float:
    n = now or _now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (n - dt).total_seconds() / 86400.0


def _recency_multiplier(days: float) -> float:
    if days < 1:
        return 1.00
    if days <= 3:
        return 1.10
    if days <= 7:
        return 1.25
    if days <= 30:
        return 1.40
    return 1.50


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: float = 20.0) -> tuple[int, str, str]:
    """Run a subprocess. Returns (returncode, stdout, stderr). Never raises."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as exc:
        return 127, "", f"command not found: {exc}"
    except subprocess.TimeoutExpired:
        return 124, "", f"command timed out: {' '.join(cmd)}"
    except Exception as exc:  # noqa: BLE001 — we explicitly want to swallow everything
        return 1, "", f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# PR collector
# ---------------------------------------------------------------------------


PR_JSON_FIELDS = (
    "number,title,url,isDraft,state,createdAt,updatedAt,"
    "statusCheckRollup,reviewDecision,reviews,comments,"
    "headRefName,body,labels"
)


def collect_prs(
    workspace: Path,
    *,
    runner=_run,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect open PRs authored by the current user for the workspace's remote.

    Returns (items, errors). Never raises.
    """
    errors: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    now = now or _now()

    if not (workspace / ".git").exists():
        # Not a git repo — nothing to do.
        return items, errors

    rc, out, err = runner(
        [
            "gh",
            "pr",
            "list",
            "--author",
            "@me",
            "--state",
            "open",
            "--json",
            PR_JSON_FIELDS,
            "--limit",
            "50",
        ],
        cwd=workspace,
    )
    if rc != 0:
        errors.append(
            {
                "collector": "prs",
                "message": (err or out or "gh pr list failed").strip()[:500],
            }
        )
        return items, errors

    try:
        prs = json.loads(out) if out.strip() else []
    except json.JSONDecodeError as exc:
        errors.append({"collector": "prs", "message": f"gh json parse: {exc}"})
        return items, errors

    # First pass: collect raw + detect cross-PR mentions for dependency boost.
    raw_prs: list[dict[str, Any]] = []
    mentioned_numbers: set[int] = set()
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        raw_prs.append(pr)
        body = pr.get("body") or ""
        for m in re.finditer(r"#(\d+)", body):
            mentioned_numbers.add(int(m.group(1)))

    open_numbers = {pr.get("number") for pr in raw_prs if isinstance(pr.get("number"), int)}

    for pr in raw_prs:
        try:
            item = _build_pr_item(pr, mentioned_numbers, open_numbers, now=now)
        except Exception as exc:  # noqa: BLE001
            errors.append({"collector": "prs", "message": f"pr build: {exc}"})
            continue
        if item is not None:
            items.append(item)

    return items, errors


def _ci_status_from_rollup(rollup: Any) -> tuple[str, int, int]:
    """Return (status, passing, failing). status in {green,red,pending,unknown}."""
    if not isinstance(rollup, list):
        return "unknown", 0, 0
    passing = 0
    failing = 0
    pending = 0
    for check in rollup:
        if not isinstance(check, dict):
            continue
        conclusion = (check.get("conclusion") or "").upper()
        status = (check.get("status") or "").upper()
        state = (check.get("state") or "").upper()
        if conclusion in {"SUCCESS"} or state in {"SUCCESS"}:
            passing += 1
        elif conclusion in {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED"} or state in {
            "FAILURE",
            "ERROR",
        }:
            failing += 1
        elif status in {"IN_PROGRESS", "QUEUED", "PENDING", "WAITING"} or state in {"PENDING"}:
            pending += 1
    if failing > 0:
        return "red", passing, failing
    if pending > 0:
        return "pending", passing, failing
    if passing > 0:
        return "green", passing, failing
    return "unknown", passing, failing


def _build_pr_item(
    pr: dict[str, Any],
    mentioned_numbers: set[int],
    open_numbers: set[int],
    *,
    now: datetime,
) -> dict[str, Any] | None:
    number = pr.get("number")
    if not isinstance(number, int):
        return None
    title = pr.get("title") or ""
    url = pr.get("url") or ""
    draft = bool(pr.get("isDraft"))
    review_decision = (pr.get("reviewDecision") or "").upper()
    reviews = pr.get("reviews") or []
    comments_field = pr.get("comments")
    if isinstance(comments_field, list):
        comments_count = len(comments_field)
    elif isinstance(comments_field, int):
        comments_count = comments_field
    else:
        comments_count = 0
    reviews_count = len(reviews) if isinstance(reviews, list) else 0

    ci_status, passing, failing = _ci_status_from_rollup(pr.get("statusCheckRollup"))

    updated = _parse_iso(pr.get("updatedAt") or "") or now
    days = _days_since(updated, now=now)

    blocks_open = any(n in open_numbers and n != number for n in mentioned_numbers)

    # Urgency per SPEC table.
    if draft and ci_status == "green":
        urgency = 5
    elif draft:
        urgency = 2
    elif ci_status == "green" and review_decision == "CHANGES_REQUESTED":
        urgency = 6
    elif ci_status == "green" and reviews_count == 0 and blocks_open:
        urgency = 8
    elif ci_status == "green" and reviews_count == 0:
        urgency = 7
    elif ci_status == "pending":
        urgency = 4
    elif ci_status == "red":
        urgency = 6  # red usually needs a human look
    else:
        urgency = 2

    recency = _recency_multiplier(days)
    dependency = 1.3 if blocks_open else 1.0
    score = _clip(urgency * recency * dependency, 0.0, 10.0)

    # Why string
    why_bits: list[str] = []
    if ci_status == "green":
        why_bits.append("green")
    elif ci_status == "red":
        why_bits.append(f"{failing} CI fail{'s' if failing != 1 else ''}")
    elif ci_status == "pending":
        why_bits.append("CI pending")
    if draft:
        why_bits.append("draft")
    if reviews_count == 0 and not draft:
        why_bits.append("unreviewed")
    elif review_decision == "CHANGES_REQUESTED":
        why_bits.append("changes requested")
    if days >= 1:
        why_bits.append(f"{int(days)}d")
    if blocks_open:
        related = sorted(n for n in mentioned_numbers if n in open_numbers and n != number)
        if related:
            why_bits.append(f"blocks #{related[0]}")

    return {
        "kind": "pr",
        "ref": f"#{number}",
        "title": title,
        "url": url,
        "score": round(score, 2),
        "urgency": urgency,
        "recency_mult": round(recency, 2),
        "dependency_mult": round(dependency, 2),
        "why": " · ".join(why_bits) if why_bits else "open",
        "touched_at": _iso(updated),
        "raw": {
            "ci": ci_status,
            "ci_passing": passing,
            "ci_failing": failing,
            "reviews": reviews_count,
            "comments": comments_count,
            "draft": draft,
            "review_decision": review_decision or None,
            "head_ref": pr.get("headRefName"),
        },
    }


# ---------------------------------------------------------------------------
# Memory-scheduled collector
# ---------------------------------------------------------------------------


DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
KEYWORD_RE = re.compile(r"\b(remind me|revisit|TODO|circle back|follow[- ]up|due)\b", re.IGNORECASE)
TOMORROW_RE = re.compile(r"\bTOMORROW\b")
# A due-date is trusted ONLY from an explicit `target_date:` field (the
# circle-back frontmatter schema), never scraped from arbitrary body prose —
# a date mentioned in the body is usually a reference/report date, not a
# deadline.
TARGET_DATE_RE = re.compile(r"^\s*target_date:\s*[\"']?(\d{4}-\d{2}-\d{2})", re.MULTILINE)
# Genuine reminders written by CAPTURE mode are `circle_back_*.md`.
CIRCLE_BACK_PREFIX = "circle_back"


def _workspace_slug(workspace: Path) -> str:
    """Mirror the slug Claude Code uses for the memory directory.

    Claude Code's per-project memory dir is `$HOME/.claude/projects/<slug>/memory/`
    where the slug is the absolute path with `/` rewritten to `-` and a leading dash.
    """
    return "-" + str(workspace.resolve()).strip("/").replace("/", "-")


def _memory_dir(workspace: Path, *, home: Path | None = None) -> Path:
    home = home or Path(os.environ.get("HOME", str(Path.home())))
    return home / ".claude" / "projects" / _workspace_slug(workspace) / "memory"


def collect_memory_scheduled(
    workspace: Path,
    *,
    home: Path | None = None,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Scan memory files for date markers and TODO-ish keywords."""
    errors: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    now = now or _now()
    today = now.date()

    mem_dir = _memory_dir(workspace, home=home)
    if not mem_dir.exists() or not mem_dir.is_dir():
        return items, errors

    try:
        files = sorted(p for p in mem_dir.glob("*.md") if p.is_file())
    except OSError as exc:
        errors.append({"collector": "memory_scheduled", "message": f"glob: {exc}"})
        return items, errors

    ordinal = 0
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(
                {
                    "collector": "memory_scheduled",
                    "message": f"read {path.name}: {exc}",
                }
            )
            continue

        has_keyword = bool(KEYWORD_RE.search(text))
        has_tomorrow = bool(TOMORROW_RE.search(text))
        target_match = TARGET_DATE_RE.search(text)

        # Only genuine circle-back reminders are scheduled items. Standing
        # auto-memory (feedback/project/reference facts, plus the MEMORY.md
        # index) lives in the same directory and routinely contains prose
        # dates and words like "revisit" / "TODO" / "due" — those must NOT be
        # mistaken for due reminders. A file qualifies iff it is a
        # `circle_back_*` note or carries an explicit `target_date:` field.
        is_reminder = path.name.startswith(CIRCLE_BACK_PREFIX) or target_match is not None
        if not is_reminder:
            continue

        # Trust a due-date only from `target_date:` or the TOMORROW keyword —
        # never from body prose. A reminder with neither is a dateless
        # "keep on radar" note.
        target: datetime | None = None
        if target_match:
            try:
                target = datetime.strptime(target_match.group(1), "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                target = None
        if target is None and has_tomorrow:
            from datetime import timedelta

            target = datetime.combine(today, datetime.min.time()).replace(
                tzinfo=timezone.utc
            ) + timedelta(days=1)

        try:
            stat = path.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        except OSError:
            mtime = now

        if target is not None:
            delta_days = (target.date() - today).days
            if delta_days < 0:
                urgency = 9  # overdue
                bucket = "overdue"
            elif delta_days == 0:
                urgency = 7
                bucket = "today"
            elif delta_days <= 7:
                urgency = 4
                bucket = "this week"
            else:
                urgency = 2
                bucket = "future"
        else:
            # Keyword-only, no date.
            urgency = 2
            bucket = "no date"

        recency = _recency_multiplier(_days_since(mtime, now=now))
        dependency = 1.0
        score = _clip(urgency * recency * dependency, 0.0, 10.0)

        # Title: first non-empty line stripped of markdown.
        title = ""
        for line in text.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                title = stripped
                break
        if not title:
            title = path.stem

        ordinal += 1
        items.append(
            {
                "kind": "memory_scheduled",
                "ref": f"M{ordinal}",
                "title": title[:200],
                "url": str(path),
                "score": round(score, 2),
                "urgency": urgency,
                "recency_mult": round(recency, 2),
                "dependency_mult": round(dependency, 2),
                "why": f"{bucket} · {path.name}",
                "touched_at": _iso(mtime),
                "raw": {
                    "file": str(path),
                    "bucket": bucket,
                    "target_date": target.date().isoformat() if target else None,
                    "matched_keyword": has_keyword,
                },
            }
        )

    return items, errors


# ---------------------------------------------------------------------------
# Git state collector
# ---------------------------------------------------------------------------


def collect_git(
    workspace: Path,
    *,
    runner=_run,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Inspect dirty files + unpushed commits."""
    errors: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    now = now or _now()

    if not (workspace / ".git").exists():
        return items, errors

    rc, out, err = runner(["git", "status", "--porcelain"], cwd=workspace)
    if rc != 0:
        errors.append({"collector": "git", "message": (err or out or "git status").strip()[:500]})
        return items, errors

    dirty_lines = [line for line in out.splitlines() if line.strip()]
    dirty_count = len(dirty_lines)

    rc2, branch_out, branch_err = runner(["git", "branch", "--show-current"], cwd=workspace)
    branch = branch_out.strip() if rc2 == 0 else ""
    if rc2 != 0 and branch_err:
        errors.append({"collector": "git", "message": branch_err.strip()[:500]})

    # Detect PR branch heuristically: non-main, non-master.
    on_pr_branch = bool(branch) and branch not in {"main", "master"}

    ordinal = 0
    if dirty_count > 0:
        ordinal += 1
        urgency = 4 if on_pr_branch else 2
        recency = 1.0
        score = _clip(urgency * recency, 0.0, 10.0)
        items.append(
            {
                "kind": "git",
                "ref": f"G{ordinal}",
                "title": f"uncommitted on {branch or '(no branch)'}",
                "url": str(workspace),
                "score": round(score, 2),
                "urgency": urgency,
                "recency_mult": round(recency, 2),
                "dependency_mult": 1.0,
                "why": f"{dirty_count} file{'s' if dirty_count != 1 else ''} · likely WIP",
                "touched_at": _iso(now),
                "raw": {
                    "branch": branch,
                    "dirty_count": dirty_count,
                    "on_pr_branch": on_pr_branch,
                },
            }
        )

    # Unpushed commits: only if we have an upstream.
    rc3, upstream_out, _ = runner(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=workspace,
    )
    if rc3 == 0 and upstream_out.strip():
        rc4, log_out, log_err = runner(
            ["git", "log", "@{u}..HEAD", "--oneline"],
            cwd=workspace,
        )
        if rc4 == 0:
            unpushed_lines = [line for line in log_out.splitlines() if line.strip()]
            if unpushed_lines:
                ordinal += 1
                urgency = 3
                score = _clip(urgency * 1.0, 0.0, 10.0)
                items.append(
                    {
                        "kind": "git",
                        "ref": f"G{ordinal}",
                        "title": f"unpushed on {branch or '(no branch)'}",
                        "url": str(workspace),
                        "score": round(score, 2),
                        "urgency": urgency,
                        "recency_mult": 1.0,
                        "dependency_mult": 1.0,
                        "why": f"{len(unpushed_lines)} commit{'s' if len(unpushed_lines) != 1 else ''} ahead",
                        "touched_at": _iso(now),
                        "raw": {
                            "branch": branch,
                            "unpushed_count": len(unpushed_lines),
                            "first_subject": unpushed_lines[0],
                        },
                    }
                )
        elif log_err:
            errors.append({"collector": "git", "message": log_err.strip()[:500]})

    return items, errors


# ---------------------------------------------------------------------------
# Top-level gather + sort
# ---------------------------------------------------------------------------


def _sort_key(item: dict[str, Any]) -> tuple[float, int, str, str]:
    # Higher score first → negate. Tiebreak: higher urgency, more recent touched_at, alpha title.
    score = float(item.get("score") or 0.0)
    urgency = int(item.get("urgency") or 0)
    touched = item.get("touched_at") or ""
    title = item.get("title") or ""
    return (-score, -urgency, _negate_iso(touched), title.lower())


def _negate_iso(iso: str) -> str:
    # We want more-recent first → sort newer before older. Strings sort lex; invert by
    # subtracting from "9999". Simple approach: prefix newer with smaller key.
    # Build numeric key from the ISO chars; missing → far past.
    if not iso:
        return "~"  # tilde > digits, so empty sorts last
    return "".join(chr(0x39 - (ord(c) - 0x30)) if c.isdigit() else c for c in iso)


def gather(
    workspace: Path,
    *,
    runner=_run,
    home: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or _now()
    workspace = workspace.resolve()

    all_items: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []

    for collector in (
        lambda: collect_prs(workspace, runner=runner, now=now),
        lambda: collect_memory_scheduled(workspace, home=home, now=now),
        lambda: collect_git(workspace, runner=runner, now=now),
    ):
        try:
            items, errors = collector()
        except Exception as exc:  # noqa: BLE001 — outer safety net
            all_errors.append(
                {
                    "collector": getattr(collector, "__name__", "unknown"),
                    "message": f"unhandled: {type(exc).__name__}: {exc}",
                }
            )
            continue
        all_items.extend(items)
        all_errors.extend(errors)

    # Drop threshold + sort.
    filtered = [item for item in all_items if float(item.get("score") or 0.0) >= 1.0]
    filtered.sort(key=_sort_key)

    return {
        "workspace": str(workspace),
        "generated_at": _iso(now),
        "items": filtered,
        "errors": all_errors,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_workspace(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).expanduser()
    return Path.cwd()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gather CLI-collectable signals for the whats-next skill.",
    )
    parser.add_argument("--workspace", help="Workspace path (default: $CLAUDE_PROJECT_DIR or cwd)")
    parser.add_argument(
        "--as-prompt-injection",
        action="store_true",
        help="Wrap output in <whats-next>…</whats-next> for the SessionStart hook.",
    )
    args = parser.parse_args(argv)

    workspace = _resolve_workspace(args.workspace)
    payload = gather(workspace)
    body = json.dumps(payload, indent=2, ensure_ascii=False)

    if args.as_prompt_injection:
        sys.stdout.write("<whats-next>\n")
        sys.stdout.write(body)
        sys.stdout.write("\n</whats-next>\n")
    else:
        sys.stdout.write(body)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
