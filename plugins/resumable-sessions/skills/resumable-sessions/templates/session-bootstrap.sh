#!/usr/bin/env bash
# Recreate the standard tmux workspace session: one window per project, each
# resuming that project's most recent Claude Code conversation.
#
# Idempotent — a no-op if the session already exists, so it is safe to run from
# a login hook AND on a short interval (every 5 min). That is what makes
# recovery self-healing instead of login-only.
#
# Install: copy to ~/.local/bin/session-bootstrap, edit NAMES/DIRS, chmod +x,
#          commit to your dotfiles.
# Usage:   session-bootstrap [session-name]     (default: main)
# Env:     TMUX_WS_CMD — override the per-window command (used for testing)
#
# Portable to bash 3.2 (macOS system bash). No GNU-only flags.
set -euo pipefail

SESSION="${1:-main}"

# --- edit me -----------------------------------------------------------------
NAMES=("projectA" "projectB")
DIRS=("$HOME/src/project-a" "$HOME/src/project-b")
# -----------------------------------------------------------------------------

# Two things --continue does NOT restore, so they are re-asserted at launch:
#   --permission-mode : runtime state; a session that comes back in `default`
#                       mode blocks on its first tool prompt and looks hung.
#   the `|| claude`   : --continue fails outright in a directory that has no
#                       prior conversation (e.g. a newly added project).
CMD="${TMUX_WS_CMD:-claude --continue --permission-mode auto || claude --permission-mode auto}"

LOG="${SESSION_BOOTSTRAP_LOG:-$HOME/.local/state/session-bootstrap.log}"
mkdir -p "$(dirname "$LOG")"
log() { printf '%s %s\n' "$(date +%FT%T%z)" "$*" >>"$LOG"; }

command -v tmux >/dev/null 2>&1 || { log "FATAL: tmux not on PATH"; exit 1; }

# "=" anchors an exact name match; without it a stale `main-old` would satisfy
# the check and the real session would never be created.
if tmux has-session -t "=$SESSION" 2>/dev/null; then
    log "session '$SESSION' already exists — nothing to do"
    exit 0
fi

# -c "$DIR" matters: `claude --continue` resolves the most recent conversation
# for the CURRENT DIRECTORY. Wrong cwd, wrong conversation, silently.
tmux new-session -d -s "$SESSION" -n "${NAMES[0]}" -c "${DIRS[0]}"
for i in $(seq 1 $(( ${#NAMES[@]} - 1 )) ); do
    tmux new-window -t "$SESSION:" -n "${NAMES[$i]}" -c "${DIRS[$i]}"
done

# send-keys into a normal shell rather than making the command the pane process,
# so a pane drops to a prompt (with its scrollback) instead of closing when
# claude exits.
for i in $(seq 0 $(( ${#NAMES[@]} - 1 )) ); do
    tmux send-keys -t "$SESSION:$i" "$CMD" Enter
done

tmux select-window -t "$SESSION:0"
log "session '$SESSION' created with ${#NAMES[@]} windows"
