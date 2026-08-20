---
name: resumable-sessions
description: "Use when Claude Code sessions should survive a reboot, a crash, or an accidentally closed terminal — coming back with their conversation, cwd and permission mode intact. Triggers: 'restart my sessions after a reboot', 'my session died / I closed the wrong window', 'recover that conversation', 'keep my agents running', 'survive reboots', long-lived tmux sessions, `claude --continue` / `--resume`, login-and-interval supervisors (launchd, systemd user timer, Task Scheduler). Also use for the one-off rescue of a single lost session."
---

# Resumable Sessions

## Overview

A Claude Code session dies with its terminal. Reboot, `kill`, a closed window, a dropped SSH
connection — the conversation is safely on disk, but the *place it was living* is gone. Recovering
it by hand every time is the thing to automate.

Three layers, in order. Each fails differently, so build and verify them one at a time:

1. **Detach the session from the terminal** — sessions live in a multiplexer (tmux), never in a
   bare terminal window.
2. **One idempotent bootstrap script** — recreates the whole layout and re-resumes each
   conversation. This is the heart of it; everything else is a trigger.
3. **The OS runs that script** — at login *and* on a short interval. The interval is what turns
   "restored when I next log in" into "self-healing".

If the user only wants to rescue one lost conversation right now, skip to
**[Manual recovery](#manual-recovery)** — that's a 30-second job, not an install.

## Layer 1 — sessions live in a multiplexer

One tmux session (say `main`), one window per project, each window `cd`'d into that project. The
multiplexer survives a closed terminal, an SSH drop, and a crashed emulator; it does not survive a
reboot or `tmux kill-server`, which is what layers 2–3 are for.

Reattach from anywhere with `tmux attach -t main`. On a remote box that's the whole recovery story
for everything except reboots.

## Layer 2 — the bootstrap script

Copy `templates/session-bootstrap.sh` to `~/.local/bin/session-bootstrap`, edit the `NAMES`/`DIRS`
arrays, `chmod +x`, and **commit it to the user's dotfiles**. A script that exists only in
`~/.local/bin` is unbacked-up and does not follow them to the next machine.

The template is deliberately small; what matters is the set of decisions baked into it, each of
which is a bug if you get it wrong:

| Decision | Why |
|---|---|
| Exit 0 early if the session exists | Makes the script safe to run every few minutes, which is what Layer 3 needs. **This is the load-bearing property** — without it you get logon-only recovery, or duplicate sessions. |
| `tmux has-session -t "=$SESSION"` | The `=` anchors an exact match. Without it, a stale `main-old` satisfies the check and the real session is never created. |
| `tmux new-window -c "$DIR"` | `claude --continue` resolves *the most recent conversation for the current directory*. Wrong cwd, wrong conversation — silently. |
| Re-assert `--permission-mode` | Permission mode is runtime state that `--continue` does **not** restore. A session that comes back in `default` mode blocks on its first tool prompt, which looks like a hang. |
| `\|\| claude` fallback | `--continue` fails outright in a directory with no prior conversation — e.g. a brand-new project in the list. |
| `send-keys` into a shell, not a pane command | A pane whose process *is* `claude` disappears when Claude exits, taking the scrollback with it. Sending keystrokes to a normal shell leaves a prompt behind you can read and retry from. |
| Log every run | A trigger that never fired and a trigger that fired and failed look identical without a log. This is the first thing you'll want when it doesn't work. |
| One script, one list of projects | Resist a per-project starter script. That path ends in three overlapping starters and no single source of truth. |

**Optional `--repair` mode, worth adding once the basics work:** walk
`tmux list-panes -a -F '#{pane_id} #{pane_current_command}'` and re-send the launch command to any
pane sitting at a bare shell. Combined with Layer 3's interval trigger, that recovers *crashed*
sessions, not just missing ones.

## Layer 3 — the OS runs it

Two triggers, same command: **at login**, and **every 5 minutes**. The second one is the one people
skip and then miss, because it covers everything the first doesn't — a killed tmux server, an OOM,
a distro or VM restart that happens without a login event.

Pick the native supervisor:

- **macOS** — a per-user `LaunchAgent` in `~/Library/LaunchAgents/`, `RunAtLoad` true plus
  `StartInterval 300`. Prefer a LaunchAgent (user domain) over a LaunchDaemon here: the script needs
  the user's `HOME`, PATH, and tmux socket, and it only makes sense once someone is logged in.
  Load with `launchctl bootstrap gui/$UID <plist>`. Note that a LaunchAgent's environment is
  minimal — use absolute paths for `tmux` and `claude`, or set `PATH` in `EnvironmentVariables`.
- **Linux** — a systemd **user** unit plus a `.timer` (`OnBootSec`, `OnUnitActiveSec=5min`), enabled
  with `systemctl --user enable --now`. Run `loginctl enable-linger $USER` so the units survive
  logout on a headless box.
- **Windows** — Task Scheduler: trigger *At log on*, with "Repeat task every 5 minutes" for the
  duration *Indefinitely*. Launch it through a hidden shim (a one-line `.vbs` calling
  `WScript.Shell.Run … , 0, False`) so no console window flashes on screen. Two settings bite:
  **uncheck "Stop the task if it runs longer than…"** (a long-lived task gets terminated at that
  limit and the scheduler then reports it as failed while things still look fine), and on a laptop
  **uncheck both battery conditions**, or the task won't start on battery and stops the moment the
  plug comes out.

Whatever the platform, hand the user any command that needs elevation or a GUI dialog to run
themselves — agent shells have no TTY for a password prompt and no access to the login session.

## What this does *not* restore

Say this out loud to the user; it's the most common misunderstanding.

- `--continue` brings back the **conversation**, in a TTY **waiting for input**. It does not resume
  work that was in flight. Unattended continuation is a different tool: a scheduled
  `claude -p "…"` run.
- In-flight background tasks, running commands, and dev servers from the old session are gone.
- MCP servers reconnect fresh; anything mid-handshake or interactively authenticated may need
  re-auth.
- Permission mode, model overrides, and other CLI flags are **not** state — re-pass them (that's
  why the bootstrap script does).

## Manual recovery

For a single lost session, no install required:

- `claude --continue` in the project directory — resumes that directory's most recent conversation.
- `claude --resume` — interactive picker over that directory's conversations. This is the one to
  reach for when the wrong window got closed, or when `--continue` grabs a stray short session
  instead of the real one.
- Transcripts live under `~/.claude/projects/<slugified-cwd>/*.jsonl`, newest last. Nothing is lost
  when a terminal dies, so recovery is always possible — worst case, read the JSONL directly.
- If tmux is still running and only the client detached: `tmux attach -t main`, or
  `tmux ls` to see what's there.

## Verification — run all of it, show the output

1. `bash -n ~/.local/bin/session-bootstrap`, then run it **twice** with
   `TMUX_WS_CMD='echo test'`: the first run creates the layout, the second must log
   "already exists" and change nothing.
2. Real run, then
   `tmux list-panes -a -F '#{window_index} #{window_name} #{pane_current_command} #{pane_current_path}'`
   — `claude` in every window, each in its own project path.
3. Prove the self-heal: `tmux kill-session -t main`, then trigger the supervisor on demand
   (`launchctl kickstart -k gui/$UID/<label>` / `systemctl --user start <unit>` /
   `schtasks /run /tn "<task>"`) and confirm the layout comes back.
4. Confirm the supervisor's own health — `launchctl print gui/$UID/<label>` (look at `last exit
   code`), `systemctl --user status <unit>`, or `schtasks /query /tn "<task>" /v /fo LIST`
   (`Last Result: 0`). A trigger that silently errors is the usual failure.
5. `tail ~/.local/state/session-bootstrap.log` — one line per run, including the no-ops.
6. Dotfiles: script committed, and the supervisor unit either committed or documented.

## Finish by writing it down

Save a memory recording: the multiplexer session name, where the script and its log live, which
supervisor units/tasks exist, and any known gap (e.g. "a reboot with no login leaves everything
down"). This setup spans the shell, the dotfiles repo, and an OS-level scheduler — nothing in the
project repo reveals it, so an undocumented chain gets rediscovered from scratch every time.
