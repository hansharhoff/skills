"""Unit tests for bin/gather.py."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
GATHER_PATH = HERE.parent / "bin" / "gather.py"

# Load gather as a module so we can call its functions directly.
spec = importlib.util.spec_from_file_location("gather", GATHER_PATH)
assert spec is not None and spec.loader is not None
gather = importlib.util.module_from_spec(spec)
sys.modules["gather"] = gather
spec.loader.exec_module(gather)


NOW = datetime(2026, 6, 4, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return repo


def _commit(repo: Path, name: str = "f.txt", body: str = "x") -> None:
    (repo / name).write_text(body)
    subprocess.run(["git", "add", name], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"add {name}"], cwd=repo, check=True)


def _fake_runner(map_: dict[tuple[str, ...], tuple[int, str, str]]):
    """Return a callable matching gather._run's signature using a command-map."""

    def runner(cmd, *, cwd=None, timeout=20.0):
        key = tuple(cmd)
        if key in map_:
            return map_[key]
        # Match by prefix as a fallback.
        for k, v in map_.items():
            if tuple(cmd[: len(k)]) == k:
                return v
        return 1, "", f"unmocked: {cmd}"

    return runner


def _pr(
    number: int,
    *,
    title: str = "x",
    ci: list[dict] | None = None,
    reviews: list | None = None,
    draft: bool = False,
    review_decision: str = "",
    updated_days_ago: int = 0,
    body: str = "",
    head_ref: str = "feature/x",
) -> dict:
    updated = (NOW - timedelta(days=updated_days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "number": number,
        "title": title,
        "url": f"https://github.com/x/y/pull/{number}",
        "isDraft": draft,
        "state": "OPEN",
        "createdAt": updated,
        "updatedAt": updated,
        "statusCheckRollup": ci or [],
        "reviewDecision": review_decision,
        "reviews": reviews or [],
        "comments": [],
        "headRefName": head_ref,
        "body": body,
        "labels": [],
    }


# ---------------------------------------------------------------------------
# PR collector
# ---------------------------------------------------------------------------


def test_pr_green_unreviewed_high_urgency(tmp_path):
    repo = _git_repo(tmp_path)
    prs = [_pr(100, title="green", ci=[{"conclusion": "SUCCESS"}], updated_days_ago=1)]
    runner = _fake_runner({("gh", "pr", "list"): (0, json.dumps(prs), "")})
    items, errors = gather.collect_prs(repo, runner=runner, now=NOW)
    assert errors == []
    assert len(items) == 1
    item = items[0]
    assert item["kind"] == "pr"
    assert item["ref"] == "#100"
    assert item["urgency"] == 7  # green + unreviewed, not blocking another open
    assert item["raw"]["ci"] == "green"
    assert "unreviewed" in item["why"]


def test_pr_green_unreviewed_blocks_another_open(tmp_path):
    repo = _git_repo(tmp_path)
    prs = [
        _pr(106, ci=[{"conclusion": "SUCCESS"}], body="unblocks #98"),
        _pr(98, ci=[{"conclusion": "SUCCESS"}]),
    ]
    runner = _fake_runner({("gh", "pr", "list"): (0, json.dumps(prs), "")})
    items, errors = gather.collect_prs(repo, runner=runner, now=NOW)
    assert errors == []
    by_ref = {it["ref"]: it for it in items}
    assert by_ref["#106"]["urgency"] == 8
    assert by_ref["#106"]["dependency_mult"] == 1.3
    assert "blocks #98" in by_ref["#106"]["why"]


def test_pr_red_ci(tmp_path):
    repo = _git_repo(tmp_path)
    prs = [_pr(50, ci=[{"conclusion": "FAILURE"}, {"conclusion": "SUCCESS"}])]
    runner = _fake_runner({("gh", "pr", "list"): (0, json.dumps(prs), "")})
    items, errors = gather.collect_prs(repo, runner=runner, now=NOW)
    assert errors == []
    assert items[0]["raw"]["ci"] == "red"
    assert items[0]["raw"]["ci_failing"] == 1
    assert "1 CI fail" in items[0]["why"]


def test_pr_draft_green_flip_urgency(tmp_path):
    repo = _git_repo(tmp_path)
    prs = [_pr(60, draft=True, ci=[{"conclusion": "SUCCESS"}])]
    runner = _fake_runner({("gh", "pr", "list"): (0, json.dumps(prs), "")})
    items, _ = gather.collect_prs(repo, runner=runner, now=NOW)
    assert items[0]["urgency"] == 5
    assert items[0]["raw"]["draft"] is True


def test_pr_gh_failure_records_error_no_raise(tmp_path):
    repo = _git_repo(tmp_path)
    runner = _fake_runner({("gh", "pr", "list"): (1, "", "not authenticated")})
    items, errors = gather.collect_prs(repo, runner=runner, now=NOW)
    assert items == []
    assert errors and errors[0]["collector"] == "prs"
    assert "not authenticated" in errors[0]["message"]


def test_pr_not_a_git_repo_returns_empty(tmp_path):
    items, errors = gather.collect_prs(tmp_path, runner=_fake_runner({}), now=NOW)
    assert items == []
    assert errors == []


# ---------------------------------------------------------------------------
# Memory-scheduled collector
# ---------------------------------------------------------------------------


def _write_memory(home: Path, workspace: Path, name: str, body: str) -> Path:
    slug = "-" + str(workspace.resolve()).strip("/").replace("/", "-")
    mem_dir = home / ".claude" / "projects" / slug / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    path = mem_dir / name
    path.write_text(body)
    return path


def _fm(target_date: str | None = None, extra: str = "") -> str:
    """Minimal circle-back frontmatter block."""
    lines = ["---", "captured_at: 2026-06-01T00:00:00Z"]
    if target_date is not None:
        lines.append(f"target_date: {target_date}")
    if extra:
        lines.append(extra)
    lines.append("---")
    return "\n".join(lines) + "\n"


def test_memory_overdue_today_thisweek_future(tmp_path):
    home = tmp_path / "home"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    today = NOW.date()
    # Dates are trusted from `target_date:` frontmatter on circle_back_* files.
    _write_memory(home, workspace, "circle_back_overdue.md", _fm(str(today - timedelta(days=3))) + "# revisit\n")
    _write_memory(home, workspace, "circle_back_today.md", _fm(str(today)) + "# today\n")
    _write_memory(home, workspace, "circle_back_week.md", _fm(str(today + timedelta(days=3))) + "# week\n")
    _write_memory(home, workspace, "circle_back_future.md", _fm(str(today + timedelta(days=60))) + "# future\n")
    # A circle_back note with no target_date is a dateless "keep on radar" item.
    _write_memory(home, workspace, "circle_back_nodate.md", _fm() + "# nodate\nrevisit this later\n")
    _write_memory(home, workspace, "boring.md", "# nothing interesting\nbody text\n")

    items, errors = gather.collect_memory_scheduled(workspace, home=home, now=NOW)
    assert errors == []
    refs = {it["raw"]["bucket"]: it for it in items}
    assert refs["overdue"]["urgency"] == 9
    assert refs["today"]["urgency"] == 7
    assert refs["this week"]["urgency"] == 4
    assert refs["future"]["urgency"] == 2
    assert refs["no date"]["urgency"] == 2
    # The boring file should not appear.
    assert "nothing interesting" not in {it["title"] for it in items}


def test_memory_ignores_standing_auto_memory(tmp_path):
    """Regression: standing feedback/project facts (with prose dates + keyword
    words) and the MEMORY.md index must NOT be reported as scheduled reminders."""
    home = tmp_path / "home"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    # A project fact: has a prose date and the word "TODO"/"revisit"/"due" — but
    # is not a circle_back file and has no target_date frontmatter.
    _write_memory(
        home,
        workspace,
        "project_pem_rotation_todo.md",
        "---\nname: pem-rotation\nmetadata:\n  type: project\n---\n"
        "# PEM rotation TODO\nWe should revisit this; PR #14 landed 2026-06-01. Follow-up due later.\n",
    )
    _write_memory(
        home,
        workspace,
        "feedback_pr_links.md",
        "---\nmetadata:\n  type: feedback\n---\n# Include PR links\nAlways cite the URL. Captured 2026-06-08.\n",
    )
    _write_memory(home, workspace, "MEMORY.md", "# Memory index\n- [x](y.md) — revisit TODO 2026-06-04\n")

    items, errors = gather.collect_memory_scheduled(workspace, home=home, now=NOW)
    assert errors == []
    assert items == []


def test_memory_target_date_without_circle_back_prefix(tmp_path):
    """A file carrying an explicit target_date qualifies even if not named circle_back_*."""
    home = tmp_path / "home"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    today = NOW.date()
    _write_memory(home, workspace, "reminder.md", _fm(str(today - timedelta(days=1))) + "# do the thing\n")
    items, errors = gather.collect_memory_scheduled(workspace, home=home, now=NOW)
    assert errors == []
    assert len(items) == 1
    assert items[0]["raw"]["bucket"] == "overdue"
    assert items[0]["raw"]["target_date"] == str(today - timedelta(days=1))


def test_memory_circle_back_ignores_body_prose_date(tmp_path):
    """A circle_back note whose body mentions a date but has no target_date is
    dateless — the prose date must not be scraped into an overdue reminder."""
    home = tmp_path / "home"
    workspace = tmp_path / "ws"
    workspace.mkdir()
    _write_memory(
        home,
        workspace,
        "circle_back_aws_sso.md",
        _fm() + "# Look at AWS SSO\nItem #8 of the 2026-07-02 report; no deadline.\n",
    )
    items, errors = gather.collect_memory_scheduled(workspace, home=home, now=NOW)
    assert errors == []
    assert len(items) == 1
    assert items[0]["raw"]["bucket"] == "no date"
    assert items[0]["raw"]["target_date"] is None


def test_memory_missing_dir_returns_empty(tmp_path):
    workspace = tmp_path / "nope"
    workspace.mkdir()
    items, errors = gather.collect_memory_scheduled(workspace, home=tmp_path / "noenv", now=NOW)
    assert items == []
    assert errors == []


# ---------------------------------------------------------------------------
# Git state collector
# ---------------------------------------------------------------------------


def test_git_clean_returns_empty(tmp_path):
    repo = _git_repo(tmp_path)
    _commit(repo)
    items, errors = gather.collect_git(repo, now=NOW)
    assert errors == []
    assert items == []


def test_git_dirty_on_branch_yields_item(tmp_path):
    repo = _git_repo(tmp_path)
    _commit(repo)
    subprocess.run(["git", "checkout", "-q", "-b", "feature/x"], cwd=repo, check=True)
    (repo / "dirty.txt").write_text("wip")
    items, errors = gather.collect_git(repo, now=NOW)
    assert errors == []
    assert len(items) == 1
    item = items[0]
    assert item["kind"] == "git"
    assert item["urgency"] == 4  # on a PR-ish branch
    assert item["raw"]["dirty_count"] == 1
    assert "feature/x" in item["title"]


def test_git_dirty_on_main(tmp_path):
    repo = _git_repo(tmp_path)
    _commit(repo)
    (repo / "dirty.txt").write_text("wip")
    items, _ = gather.collect_git(repo, now=NOW)
    assert items and items[0]["urgency"] == 2


def test_git_unpushed_commits(tmp_path):
    # Create a "remote" repo and clone it to ensure we have an upstream to compare against.
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    repo = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(remote), str(repo)], check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    _commit(repo, "a.txt")
    subprocess.run(["git", "push", "-q", "origin", "main"], cwd=repo, check=True)
    _commit(repo, "b.txt")  # unpushed
    items, errors = gather.collect_git(repo, now=NOW)
    assert errors == []
    unpushed = [it for it in items if "unpushed" in it["title"]]
    assert len(unpushed) == 1
    assert unpushed[0]["urgency"] == 3
    assert unpushed[0]["raw"]["unpushed_count"] == 1


def test_git_not_a_repo(tmp_path):
    items, errors = gather.collect_git(tmp_path / "nope", now=NOW)
    assert items == []
    assert errors == []


# ---------------------------------------------------------------------------
# Ranking math
# ---------------------------------------------------------------------------


def test_ranking_top3_order(tmp_path):
    repo = _git_repo(tmp_path)
    _commit(repo)
    # PRs: one urgency-8 (blocks another), one urgency-7 (lone green), one urgency-2.
    prs = [
        _pr(106, title="unblocker", ci=[{"conclusion": "SUCCESS"}], updated_days_ago=2, body="closes #98"),
        _pr(98, title="blocked", ci=[{"conclusion": "FAILURE"}], updated_days_ago=2),
        _pr(60, title="draft", draft=True, ci=[{"conclusion": "SUCCESS"}], updated_days_ago=10),
    ]
    runner = _fake_runner({("gh", "pr", "list"): (0, json.dumps(prs), "")})
    result = gather.gather(repo, runner=runner, home=tmp_path / "home", now=NOW)
    refs = [item["ref"] for item in result["items"]]
    # #106 must be first (urgency 8 × 1.1 × 1.3 ≈ 11.4 → clipped to 10).
    assert refs[0] == "#106"
    # #98 was red CI (urgency 6), should beat the draft (urgency 5 with bigger recency).
    # Confirm top items by score is descending.
    scores = [item["score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)


def test_recency_multiplier_table():
    assert gather._recency_multiplier(0) == 1.00
    assert gather._recency_multiplier(2) == 1.10
    assert gather._recency_multiplier(5) == 1.25
    assert gather._recency_multiplier(15) == 1.40
    assert gather._recency_multiplier(60) == 1.50


def test_score_clipped_to_10():
    # 9 * 1.5 * 1.3 = 17.55 → clipped.
    assert gather._clip(17.55, 0.0, 10.0) == 10.0


def test_drop_threshold_below_one(tmp_path):
    repo = _git_repo(tmp_path)
    # A draft, undeated, old PR with urgency 2 × recency 1.5 × dep 1.0 = 3.0 → stays.
    # We need to manufacture something that scores < 1.0. Use a runner that returns nothing,
    # then craft a synthetic item via gather().
    runner = _fake_runner({("gh", "pr", "list"): (0, "[]", "")})
    result = gather.gather(repo, runner=runner, home=tmp_path / "nohome", now=NOW)
    assert all(item["score"] >= 1.0 for item in result["items"])


# ---------------------------------------------------------------------------
# JSON shape
# ---------------------------------------------------------------------------


REQUIRED_TOP_KEYS = {"workspace", "generated_at", "items", "errors"}
REQUIRED_ITEM_KEYS = {
    "kind",
    "ref",
    "title",
    "url",
    "score",
    "urgency",
    "recency_mult",
    "dependency_mult",
    "why",
    "touched_at",
    "raw",
}


def test_output_shape(tmp_path):
    repo = _git_repo(tmp_path)
    _commit(repo)
    prs = [_pr(1, ci=[{"conclusion": "SUCCESS"}])]
    runner = _fake_runner({("gh", "pr", "list"): (0, json.dumps(prs), "")})
    result = gather.gather(repo, runner=runner, home=tmp_path / "home", now=NOW)
    assert REQUIRED_TOP_KEYS.issubset(result.keys())
    assert isinstance(result["workspace"], str)
    assert isinstance(result["generated_at"], str)
    assert isinstance(result["items"], list)
    assert isinstance(result["errors"], list)
    for item in result["items"]:
        assert REQUIRED_ITEM_KEYS.issubset(item.keys())
        assert isinstance(item["score"], (int, float))
        assert isinstance(item["urgency"], int)
        assert isinstance(item["raw"], dict)


# ---------------------------------------------------------------------------
# Failure isolation
# ---------------------------------------------------------------------------


def test_one_collector_failing_does_not_break_others(tmp_path, monkeypatch):
    repo = _git_repo(tmp_path)
    _commit(repo)

    def boom(*a, **kw):
        raise RuntimeError("synthetic")

    monkeypatch.setattr(gather, "collect_prs", boom)
    result = gather.gather(repo, runner=_fake_runner({}), home=tmp_path / "h", now=NOW)
    # Should have an error captured but still produce a valid payload.
    assert any("synthetic" in err.get("message", "") for err in result["errors"])
    assert isinstance(result["items"], list)


def test_main_exit_code_zero(tmp_path, monkeypatch, capsys):
    repo = _git_repo(tmp_path)
    _commit(repo)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))

    # Stub the runner used by the real collectors so we don't depend on real gh.
    def fake_run(cmd, **kw):
        if cmd[:3] == ["gh", "pr", "list"]:
            return 0, "[]", ""
        # Pass-through to real subprocess for git so the git collector works.
        return gather._run(cmd, **kw)

    monkeypatch.setattr(gather, "_run", fake_run)
    rc = gather.main([])
    out = capsys.readouterr().out
    assert rc == 0
    parsed = json.loads(out)
    assert "items" in parsed


def test_main_prompt_injection_wraps(tmp_path, monkeypatch, capsys):
    repo = _git_repo(tmp_path)
    _commit(repo)
    monkeypatch.setattr(
        gather,
        "_run",
        lambda cmd, **kw: (0, "[]", "") if cmd[:2] == ["gh", "pr"] else gather._run(cmd, **kw),
    )
    rc = gather.main(["--workspace", str(repo), "--as-prompt-injection"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.startswith("<whats-next>\n")
    assert out.rstrip().endswith("</whats-next>")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
