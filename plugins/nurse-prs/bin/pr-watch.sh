#!/usr/bin/env bash
# pr-watch.sh <owner/repo> — poll a GitHub repo for activity worth an
# autonomous response and emit one stdout line per new item since the previous
# tick. Designed to be run as a Claude Code `persistent` Monitor: each line
# becomes an event that cues another nurse-prs loop pass.
#
# Surfaces (by anyone OTHER than the authenticated gh user — your own writes
# are filtered out so you don't react to yourself):
#   - new PRs / issues
#   - new issue/PR conversation comments
#   - new inline review (diff) comments
#   - submitted reviews (approve / request-changes / comment) on open PRs
#
# Transient gh failures are swallowed (|| true) so one bad request never kills
# the watch. Arms from "now", so only NEW activity is reported (no backlog).
#
# Usage:  bash pr-watch.sh Merchandising-Solutions/ai
#
# Bot/App-identity accounts (no personal gh auth, e.g. a GitHub App
# installation token):
#   PR_WATCH_TOKEN_CMD  — command whose stdout is exported as GH_TOKEN, run
#                         once at start and again each tick (App installation
#                         tokens expire after ~1h). Unset = plain gh auth.
#   PR_WATCH_ME         — login to filter own writes by (App tokens get a 403
#                         from /user, so autodetection fails for them).
#
#   PR_WATCH_TOKEN_CMD=appretio-mint-token PR_WATCH_ME='appretio-bot[bot]' \
#     bash pr-watch.sh <owner/repo>
set -uo pipefail

repo="${1:?usage: pr-watch.sh <owner/repo>}"
interval="${PR_WATCH_INTERVAL:-60}"

# Optional token hook: mint/refresh GH_TOKEN from PR_WATCH_TOKEN_CMD.
token_cmd="${PR_WATCH_TOKEN_CMD:-}"
refresh_token() {
  [ -n "$token_cmd" ] || return 0
  GH_TOKEN="$(bash -c "$token_cmd" 2>/dev/null)" && export GH_TOKEN
}
refresh_token

# Fail loud, not silent: a watch that can't read the repo is a dead watch.
if ! gh api "repos/$repo" --jq .full_name >/dev/null 2>&1; then
  echo "[pr-watch] ERROR: cannot read $repo via gh — check auth (GH_TOKEN / PR_WATCH_TOKEN_CMD / gh auth). Aborting." >&2
  exit 1
fi

# Own identity, for filtering out our own writes. App installation tokens
# cannot call /user (403), so allow an explicit override.
me="${PR_WATCH_ME:-$(gh api user --jq .login 2>/dev/null || echo '')}"
if [ -z "$me" ]; then
  echo "[pr-watch] WARN: own identity unresolved — own writes will NOT be filtered; set PR_WATCH_ME." >&2
fi

last="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
strip='(.body // "") | gsub("[\n\r\t]+"; " ") | .[0:220]'

while true; do
  refresh_token   # App installation tokens expire ~1h; re-mint each tick.
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  # 1. Brand-new issues & PRs created by someone other than us.
  gh api "repos/$repo/issues?since=$last&state=all&sort=created&direction=asc&per_page=50" \
    --jq ".[] | select(.user.login != \"$me\") | select(.created_at >= \"$last\") |
          \"[NEW \(if .pull_request then \"PR\" else \"issue\" end) #\(.number)] \(.title) (by \(.user.login))\"" \
    2>/dev/null || true

  # 2. New issue/PR-conversation comments.
  gh api "repos/$repo/issues/comments?since=$last&sort=created&direction=asc&per_page=100" \
    --jq ".[] | select(.user.login != \"$me\") | select(.created_at >= \"$last\") |
          \"[comment #\(.issue_url | split(\"/\") | last)] \(.user.login): \" + ($strip)" \
    2>/dev/null || true

  # 3. New inline review (diff) comments on PRs.
  gh api "repos/$repo/pulls/comments?since=$last&sort=created&direction=asc&per_page=100" \
    --jq ".[] | select(.user.login != \"$me\") | select(.created_at >= \"$last\") |
          \"[review-comment PR #\(.pull_request_url | split(\"/\") | last) \(.path):\(.line // .original_line // 0)] \(.user.login): \" + ($strip)" \
    2>/dev/null || true

  # 4. Submitted reviews (approve / request-changes / comment) on open PRs.
  for pr in $(gh pr list --repo "$repo" --state open --json number --jq '.[].number' 2>/dev/null); do
    gh api "repos/$repo/pulls/$pr/reviews" \
      --jq ".[] | select(.user.login != \"$me\") | select((.submitted_at // \"\") >= \"$last\") |
            \"[REVIEW PR #$pr] \(.user.login) \(.state): \" + ($strip)" \
      2>/dev/null || true
  done

  last="$now"
  sleep "$interval"
done
