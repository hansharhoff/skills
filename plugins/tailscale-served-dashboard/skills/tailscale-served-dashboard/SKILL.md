---
name: tailscale-served-dashboard
description: "Use when turning a locally-running web app, dashboard, or HTTP service on this Mac into something reachable from the user's other devices that survives reboots and crashes. Triggers: 'make this a service', 'serve this dashboard', 'expose this on my tailnet', 'keep it running', launchd setup, tailscale serve for a local port. macOS + Tailscale specific."
---

# Tailscale-Served Dashboard Service

## Overview

Turn an ad-hoc local web app into a durable, tailnet-reachable service with three layers:

1. **Bind to `127.0.0.1`** — the app listens only on loopback (never `0.0.0.0`).
2. **Front it with `tailscale serve`** — HTTPS + real cert, reachable only from the user's tailnet devices, not the public internet.
3. **Supervise with a launchd `LaunchDaemon`** (system domain) — starts at boot, relaunches on crash/exit, kept awake by `caffeinate` so background collectors keep sampling.

**Use a `LaunchDaemon` (system domain), NOT a per-user `LaunchAgent`.** The agent's shell is a background/SSH session that can't reach the `gui/$UID` domain a LaunchAgent needs, and a system daemon also survives reboots without anyone logging in. The daemon runs as root by default, so it sets `UserName`/`GroupName` to drop to the user — that keeps `Path.home()` and SQLite state under `/Users/hans`.

Reference implementations on this Mac: `com.hans.airthings-dashboard` and `com.hans.sysh-dashboard` (both `/Library/LaunchDaemons/`).

## The Three Files

For a service `<svc>` whose app listens on local `<PORT>`, exposed at tailnet `https://<host>.ts.net:<HTTPS>`:

### 1. Run script — `~/.local/bin/run-<svc>.sh`

```bash
#!/bin/bash
set -euo pipefail
TS=/Applications/Tailscale.app/Contents/MacOS/Tailscale
PYTHON=/Users/hans/homebrew/bin/python3.14   # pin abs path; daemon PATH is minimal
APP=/Users/hans/.local/bin/<svc>
PORT=<PORT>

# Idempotent + additive: only touch the :HTTPS mapping if our proxy is absent.
if [ -x "$TS" ]; then
    if ! "$TS" serve status 2>/dev/null | grep -q "127.0.0.1:${PORT}"; then
        "$TS" serve --bg --https=<HTTPS> / "http://127.0.0.1:${PORT}" || true
    fi
fi

# exec so caffeinate owns the launchd-tracked PID; -i -s keeps the Mac awake.
exec /usr/bin/caffeinate -i -s "$PYTHON" "$APP" --host 127.0.0.1 --port "$PORT"
```

### 2. LaunchDaemon plist — `/Library/LaunchDaemons/com.hans.<svc>.plist`

Must be owned `root:wheel`, mode `644`. Key elements: `ProgramArguments` → the run
script; **`UserName`/`GroupName`** (e.g. `hans`/`staff`) to drop from root to the user;
`EnvironmentVariables` pinning `HOME=/Users/hans` (so `~`-relative state resolves) and a
sane `PATH`; `RunAtLoad` + `KeepAlive` true; `ThrottleInterval` 10; `Standard{Out,Error}Path`
under `~/Library/Logs`. See `com.hans.airthings-dashboard.plist` for the canonical template, or use the scaffold.

### 3. Installer — `~/.local/bin/install-<svc>.sh` (the user runs it)

A single self-contained script that the user runs in their own Terminal. It calls
`sudo` internally (prompts for password there — never from the agent shell, which
has no TTY), is idempotent, and verifies health at the end:

```bash
pkill -f 'run-<svc>.sh'; pkill -f '<svc>'        # free the port
sudo cp <staged>.plist /Library/LaunchDaemons/ && sudo chown root:wheel <dest> && sudo chmod 644 <dest>
sudo launchctl bootout   system/com.hans.<svc> 2>/dev/null || true
sudo launchctl bootstrap system/ <dest>
# then curl 127.0.0.1:<PORT> until 200, print `launchctl print system/<label>`
```

## Scaffold a new service in one command

`scaffold.sh` writes all three files — run script, staged daemon plist (idempotent,
won't clobber an existing serve port), and the installer — then tells the user the
one command to run:

```bash
# scaffold.sh sits next to this SKILL.md
./scaffold.sh \
  --name sysh-dashboard --port 8766 --https 8765 \
  --app ~/.local/bin/sysh-dashboard
# → run ~/.local/bin/install-sysh-dashboard.sh yourself to load it
```

Run `scaffold.sh --help` for all flags (`--python`, `--user`, `--group`, `--no-caffeinate`, `--no-python`, `--args`).

## Critical gotchas

| Gotcha | Why it bites | Fix |
|---|---|---|
| **Don't use a LaunchAgent / `gui/$UID`** | The agent's shell is a background/SSH session (`launchctl managername` → `Background`); `gui/$UID` returns `125: Domain does not support specified action`. A LaunchAgent also needs a login session to run. | Use a system `LaunchDaemon` (`launchctl bootstrap system/`) with `UserName`/`GroupName` to drop to the user. |
| **`sudo` can't prompt from the agent shell** | No TTY; `sudo` hangs or fails silently. Don't ask the user to paste sudo into the agent session either. | Generate a single `install-<svc>.sh` that calls sudo internally; the user runs that one script in their own Terminal. Stage the plist somewhere user-writable first. |
| **Daemon runs as root** | `Path.home()` → `/var/root`, SQLite/state orphaned. | Set `UserName`/`GroupName` and pin `HOME` in `EnvironmentVariables`. |
| **Clobbering existing serve mappings** | `tailscale serve` with an already-used `--https=<port>` overwrites it. | ALWAYS `tailscale serve status` first; pick an unused `--https` port; the run script's `grep` guard makes re-asserting additive. |
| **Empty `PATH` under launchd** | Minimal env; shell-outs (`vm_stat`, `top`) fail. | Pin `PATH` in `EnvironmentVariables`; absolute paths to python and the app. |
| **Collector sleeps with the Mac** | Idle-sleep pauses sampling, gaps in history. | `caffeinate -i -s` in the run script. Drop it (`--no-caffeinate`) for stateless view-only dashboards. |
| **Port held by a manual instance** | Killing the old process then loading the daemon races; KeepAlive throttle-retries if the port is busy. | `pkill -f <svc>` before bootstrapping; let the daemon own the port. |
| **macOS Tailscale CLI not on PATH** | App Store build doesn't add to PATH. | Use `/Applications/Tailscale.app/Contents/MacOS/Tailscale`. |

## Verify (after the user loads it)

```bash
sudo launchctl print system/com.hans.<svc> | grep -E 'state|pid'   # running
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:<PORT>/  # 200 local
/Applications/Tailscale.app/Contents/MacOS/Tailscale serve status  # mapping present
```

Then open `https://<host>.ts.net:<HTTPS>/` from another tailnet device.

## Common mistakes

- Reaching for a per-user **LaunchAgent** / `launchctl … gui/$UID` — fails from the agent's background shell and needs a login session. Use a system LaunchDaemon.
- Binding `0.0.0.0`/the tailscale IP directly instead of `127.0.0.1` + `serve` — loses the real TLS cert and widens exposure. Prefer `serve` (see user's global guidance).
- Reaching for `tailscale funnel` — that's public internet, a different blast radius. Never without explicit confirmation.
- Assuming `bootstrap` worked — verify with `sudo launchctl print system/<label>`.
