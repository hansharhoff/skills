#!/usr/bin/env python3
"""Turn a Claude Code session transcript (.jsonl) into a compact JSON digest.

The point is to do the mechanical, deterministic accounting here so the model
never has to read the raw transcript (which can be tens of MB). The model reads
this digest instead, then writes the narrative retrospective.

What it extracts:
  - counts (user / assistant messages, tool calls, tool errors, compactions)
  - wall-clock duration
  - token trajectory: the prompt size (context) at each turn, its peak, and the
    growth between successive *human* messages -> this is what powers the
    "/clear vs /compact" advice.
  - per-tool usage tally
  - a capped list of tool errors (with short snippets)
  - the ordered list of *human* messages, each annotated with the context size
    at that point and how much context grew since the previous human message
  - compaction / continuation events

Usage:
  analyze.py [path-to.jsonl]        # explicit file
  analyze.py                        # auto-locate newest for this workspace

Always prints one JSON object to stdout. Best-effort: malformed lines are
skipped, never fatal.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

MAX_USER_MSGS = 120       # cap the human-message list so the digest stays small
MAX_ERRORS = 25
USER_TEXT_TRUNC = 400     # chars per human message kept


def locate() -> str | None:
    """Mirror get-session.sh: newest .jsonl in this workspace's project dir."""
    projects = Path.home() / ".claude" / "projects"
    ws = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    slug = ws.replace("/", "-")
    d = projects / slug
    search = d if d.is_dir() else projects
    cands = list(search.rglob("*.jsonl"))
    if not cands:
        return None
    return str(max(cands, key=lambda p: p.stat().st_mtime))


def parse_ts(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


def content_blocks(msg):
    """Normalize an anthropic message's content into a list of blocks."""
    c = msg.get("content")
    if isinstance(c, str):
        return [{"type": "text", "text": c}]
    if isinstance(c, list):
        return c
    return []


def context_size(usage):
    """Total prompt tokens that turn = fresh input + cache read + cache write."""
    if not isinstance(usage, dict):
        return None
    return (
        (usage.get("input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
    )


def is_human_text(text: str) -> tuple[bool, str]:
    """Classify a user-role text block. Returns (is_genuine_human, note)."""
    t = text.strip()
    if not t:
        return False, "empty"
    low = t.lower()
    if t.startswith("<local-command") or "<command-name>" in t or "<command-stdout" in low:
        return True, "slash-command"
    if t.startswith("This session is being continued"):
        return False, "compaction-preamble"
    if t.startswith("Caveat:"):
        return False, "caveat"
    return True, ""


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else locate()
    if not path or not os.path.isfile(path):
        print(json.dumps({"error": f"transcript not found: {path!r}"}))
        return

    counts = {"user_msgs": 0, "assistant_msgs": 0, "tool_calls": 0,
              "tool_errors": 0, "compactions": 0, "lines": 0, "bad_lines": 0}
    tools: dict[str, int] = {}
    errors: list[dict] = []
    human_msgs: list[dict] = []      # {i, ts, text, note, tool_calls_since}
    compactions: list[dict] = []
    assistant_ctx: list[dict] = []   # {ts, ctx, out} in order
    first_ts = last_ts = None
    total_output = 0
    tool_calls_since_human = 0

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            counts["lines"] += 1
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                counts["bad_lines"] += 1
                continue

            etype = e.get("type")
            ts = parse_ts(e.get("timestamp"))
            if ts:
                first_ts = first_ts or ts
                last_ts = ts

            # compaction / continuation markers
            if etype == "summary" or e.get("isCompactSummary") or e.get("subtype") == "compact":
                counts["compactions"] += 1
                compactions.append({"i": counts["user_msgs"], "ts": e.get("timestamp")})
                continue

            msg = e.get("message") or {}
            role = msg.get("role") or etype

            if role == "assistant":
                counts["assistant_msgs"] += 1
                usage = msg.get("usage") or {}
                out = usage.get("output_tokens") or 0
                total_output += out
                ctx = context_size(usage)
                if ctx is not None:
                    assistant_ctx.append({"ts": e.get("timestamp"), "ctx": ctx, "out": out})
                for b in content_blocks(msg):
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        counts["tool_calls"] += 1
                        tool_calls_since_human += 1
                        name = b.get("name", "?")
                        tools[name] = tools.get(name, 0) + 1
                continue

            if role == "user":
                blocks = content_blocks(msg)
                # tool_result blocks => not a human turn; scan for errors
                had_tool_result = False
                for b in blocks:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        had_tool_result = True
                        if b.get("is_error"):
                            counts["tool_errors"] += 1
                            if len(errors) < MAX_ERRORS:
                                c = b.get("content")
                                if isinstance(c, list):
                                    c = " ".join(
                                        x.get("text", "") for x in c if isinstance(x, dict)
                                    )
                                errors.append({
                                    "after_human_msg": counts["user_msgs"],
                                    "snippet": (str(c) or "")[:220],
                                })
                if had_tool_result:
                    continue
                if e.get("isMeta"):
                    continue
                # genuine human message: gather its text
                text = " ".join(
                    b.get("text", "") for b in blocks
                    if isinstance(b, dict) and b.get("type") == "text"
                ).strip()
                keep, note = is_human_text(text)
                if not keep:
                    continue
                counts["user_msgs"] += 1
                if len(human_msgs) < MAX_USER_MSGS:
                    human_msgs.append({
                        "i": counts["user_msgs"],
                        "ts": e.get("timestamp"),
                        "text": text[:USER_TEXT_TRUNC],
                        "note": note,
                        "tool_calls_before": tool_calls_since_human,
                    })
                tool_calls_since_human = 0

    # Attach context size to each human message: the context of the FIRST
    # assistant turn at or after that message's timestamp.
    def ctx_at(ts_str):
        ts = parse_ts(ts_str)
        if not ts:
            return None
        best = None
        for a in assistant_ctx:
            ats = parse_ts(a["ts"])
            if ats and ats >= ts:
                best = a["ctx"]
                break
        return best

    prev = None
    for m in human_msgs:
        m["context_tokens"] = ctx_at(m["ts"])
        if m["context_tokens"] is not None and prev is not None:
            m["growth_since_prev"] = m["context_tokens"] - prev
        else:
            m["growth_since_prev"] = None
        if m["context_tokens"] is not None:
            prev = m["context_tokens"]

    peak_ctx = max((a["ctx"] for a in assistant_ctx), default=None)
    final_ctx = assistant_ctx[-1]["ctx"] if assistant_ctx else None
    hours = None
    if first_ts and last_ts:
        hours = round((last_ts - first_ts).total_seconds() / 3600, 2)

    digest = {
        "jsonl_path": path,
        "session_id": Path(path).stem,
        "workspace": os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(),
        "counts": counts,
        "duration": {
            "start": first_ts.isoformat() if first_ts else None,
            "end": last_ts.isoformat() if last_ts else None,
            "hours": hours,
        },
        "tokens": {
            "total_output": total_output,
            "peak_context": peak_ctx,
            "final_context": final_ctx,
        },
        "tools": dict(sorted(tools.items(), key=lambda kv: -kv[1])),
        "tool_errors": errors,
        "compactions": compactions,
        "human_messages": human_msgs,
        "notes": [
            "context_tokens = full prompt size that turn (input + cache read + cache write).",
            "growth_since_prev = how much context grew since the previous human message; "
            "large growth then a topic switch is a /clear or /compact signal.",
            f"human_messages capped at {MAX_USER_MSGS}; tool_errors at {MAX_ERRORS}.",
        ],
    }
    print(json.dumps(digest, indent=2))


if __name__ == "__main__":
    main()
