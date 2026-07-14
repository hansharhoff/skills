#!/usr/bin/env bash
# Locate the transcript JSONL for a Claude Code session.
#
# Claude Code stores each session as a JSONL file at
#   $HOME/.claude/projects/<workspace-slug>/<session-id>.jsonl
# where <workspace-slug> is the absolute workspace path with every "/" replaced
# by "-" (so /home/hans/workspaces -> -home-hans-workspaces).
#
# Usage:
#   get-session.sh                 # newest session for the current workspace
#   get-session.sh <session-id>    # a specific session id (with or without .jsonl)
#   get-session.sh /path/to.jsonl  # an explicit file
#   get-session.sh --dump [...]    # print the JSONL contents instead of the path
#
# Prints the resolved path on stdout (or the file contents with --dump).
# Exits non-zero with a message on stderr if nothing is found.
set -euo pipefail

DUMP=0
if [[ "${1:-}" == "--dump" ]]; then DUMP=1; shift; fi
ARG="${1:-}"

projects_dir="${HOME}/.claude/projects"

resolve() {
  # 1) explicit existing file
  if [[ -n "$ARG" && -f "$ARG" ]]; then
    echo "$ARG"; return 0
  fi

  # 2) a session id -> search every project dir for <id>.jsonl (newest wins)
  if [[ -n "$ARG" ]]; then
    local id="${ARG%.jsonl}"
    local hit
    hit="$(find "$projects_dir" -maxdepth 2 -type f -name "${id}.jsonl" -printf '%T@ %p\n' 2>/dev/null \
            | sort -rn | head -1 | cut -d' ' -f2-)"
    if [[ -n "$hit" ]]; then echo "$hit"; return 0; fi
    echo "get-session: no transcript found for session id '$id'" >&2
    return 3
  fi

  # 3) no arg -> newest .jsonl in the current workspace's project dir
  local ws="${CLAUDE_PROJECT_DIR:-$PWD}"
  local slug
  slug="$(printf '%s' "$ws" | sed 's:/:-:g')"
  local dir="${projects_dir}/${slug}"
  if [[ ! -d "$dir" ]]; then
    # Fallback: newest transcript across ALL projects (best-effort).
    dir="$projects_dir"
  fi
  local newest
  newest="$(find "$dir" -maxdepth 2 -type f -name '*.jsonl' -printf '%T@ %p\n' 2>/dev/null \
             | sort -rn | head -1 | cut -d' ' -f2-)"
  if [[ -z "$newest" ]]; then
    echo "get-session: no .jsonl transcripts under $dir" >&2
    return 4
  fi
  echo "$newest"
}

path="$(resolve)"
if [[ "$DUMP" == "1" ]]; then
  cat "$path"
else
  echo "$path"
fi
