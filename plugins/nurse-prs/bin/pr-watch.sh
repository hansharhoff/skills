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
set -uo pipefail

repo="${1:?usage: pr-watch.sh <owner/repo>}"
me="$(gh api user --jq .login 2>/dev/null || echo '')"
interval="${PR_WATCH_INTERVAL:-60}"

last="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
strip='(.body // "") | gsub("[\n\r\t]+"; " ") | .[0:220]'

while true; do
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
