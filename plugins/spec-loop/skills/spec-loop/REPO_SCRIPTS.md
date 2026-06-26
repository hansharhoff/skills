# Repo scripts

Spec-loop wraps its recurring git / filesystem operations behind one named
script so a single permission rule allowlists them all. Loaded on demand by
[`SKILL.md`](SKILL.md) — only needed during **Bootstrap** (installing the
script) or when the user asks to update the wrapper.

## Why

Every direct `git diff <hash>..HEAD` is a fresh permission prompt because
hashes vary. Wrapping these behind one script with a stable invocation
(`<spec-dir>/scripts/spec-loop.sh <verb> …`) lets the user allow it once
and never see another prompt for the loop's read-only operations.

## What gets installed

One file: `<spec-dir>/scripts/spec-loop.sh`. Bootstrap copies it once;
updates land via the skill (the template below is the source of truth).

`<spec-dir>` defaults to `specs/`; an `.spec-loop.toml` at the repo root can
override it (see [`SPEC_CONVENTIONS.md`](SPEC_CONVENTIONS.md)). The script
reads that config the same way the skill does.

### `<spec-dir>/scripts/spec-loop.sh`

```bash
#!/usr/bin/env bash
# Spec-loop command wrapper.
# Source of truth: plugins/spec-loop/skills/spec-loop/REPO_SCRIPTS.md
#
# Reads .spec-loop.toml at the repo root (if present) to learn the spec
# directory and the default code paths for code-diff. Resolves a deliverable
# to its deliverable folder under <spec-dir>/domain/<name>/, reads the
# last-aligned commit hash from the co-located LEDGER.md, and runs the
# loop's read-only git/filesystem operations.

set -euo pipefail

# --- config (.spec-loop.toml at repo root) ---------------------------------
#
# A tiny TOML-ish config is read with grep+sed — no toml parser required.
# Recognised keys:
#   spec_dir = "specs"               # spec root (default: specs)
#   code_dirs = ["src", "packages"]  # default pathspec for code-diff (default: nothing — diff everything)
#
# Missing config → all defaults. Lines with leading `#` are ignored.

_read_cfg() {
  local key="$1" default="$2" file=".spec-loop.toml"
  [[ -f "$file" ]] || { echo "$default"; return; }
  local val
  val=$(grep -E "^\s*${key}\s*=" "$file" | head -1 | sed -E "s/^\s*${key}\s*=\s*//; s/^\"//; s/\"$//")
  [[ -n "$val" ]] && echo "$val" || echo "$default"
}

SPEC_DIR=$(_read_cfg spec_dir specs)
CODE_DIRS_RAW=$(_read_cfg code_dirs "")

_deliverable_dir() {
  local name="$1"
  if   [[ -d "$SPEC_DIR/domain/$name" ]]; then echo "$SPEC_DIR/domain/$name"
  elif [[ -d "$SPEC_DIR/$name"        ]]; then echo "$SPEC_DIR/$name"
  else
    echo "spec-loop: deliverable '$name' not found at $SPEC_DIR/domain/$name (or $SPEC_DIR/$name)" >&2
    exit 1
  fi
}

# state dir is .sdd inside the deliverable's implementation/
_state_dir() { echo "$(_deliverable_dir "$1")/implementation/.sdd"; }

_last_aligned() {
  local ledger="$(_state_dir "$1")/LEDGER.md"
  if [[ ! -f "$ledger" ]]; then
    echo "spec-loop: no LEDGER.md at $ledger — run Bootstrap first" >&2
    exit 1
  fi
  # matches: "- Last-aligned commit: <hash>"
  local hash
  hash=$(grep -iE '^- *Last-aligned commit:' "$ledger" | head -1 | sed -E 's/.*: *//' | tr -d ' ')
  if [[ -z "$hash" ]]; then
    echo "spec-loop: no 'Last-aligned commit:' line in $ledger" >&2
    exit 1
  fi
  echo "$hash"
}

# Parse code_dirs from the array-of-strings TOML form on a single line.
# Examples accepted:
#   code_dirs = ["src"]
#   code_dirs = ["packages/api", "packages/frontend"]
_code_dirs_array() {
  # Strip brackets + quotes + spaces, split on comma.
  echo "$CODE_DIRS_RAW" | sed -E 's/^\[//; s/\]$//; s/"//g; s/, */ /g; s/  */ /g'
}

case "${1:-}" in
  status)
    NAME="${2:?usage: status <deliverable>}"
    DIR=$(_deliverable_dir "$NAME"); LA=$(_last_aligned "$NAME"); HEAD=$(git rev-parse HEAD)
    echo "deliverable:     $NAME"
    echo "deliverable dir: $DIR"
    echo "last-aligned:    $LA"
    echo "HEAD:            $HEAD"
    echo
    echo "deliverable commits since alignment:"
    git log --oneline "$LA..HEAD" -- "$DIR" || true
    ;;
  diff)
    NAME="${2:?usage: diff <deliverable>}"
    DIR=$(_deliverable_dir "$NAME"); LA=$(_last_aligned "$NAME")
    # Whole deliverable folder — INTRO.md, SPEC.md, and implementation/ all in
    # one diff (the loop reads them as a single unit).
    git diff "$LA..HEAD" -- "$DIR"
    ;;
  code-diff)
    NAME="${2:?usage: code-diff <deliverable> [<pathspec>...]}"; shift 2
    LA=$(_last_aligned "$NAME")
    PATHS=("$@")
    if [[ ${#PATHS[@]} -eq 0 ]]; then
      # No explicit paths — fall back to config'd code_dirs, else everything.
      read -ra PATHS < <(_code_dirs_array)
    fi
    if [[ ${#PATHS[@]} -eq 0 ]]; then
      git log  --oneline "$LA..HEAD" || true
      echo
      git diff --stat "$LA..HEAD"
    else
      git log  --oneline "$LA..HEAD" -- "${PATHS[@]}" || true
      echo
      git diff --stat "$LA..HEAD" -- "${PATHS[@]}"
    fi
    ;;
  check-size)
    NAME="${2:?usage: check-size <deliverable>}"
    DIR=$(_deliverable_dir "$NAME"); THRESHOLD=500; over=0
    # Lists INTRO.md, SPEC.md (+ any SPEC/ split children), and implementation/*.md.
    # Skips .sdd/, design/, and any opt-in generated artifacts.
    while IFS= read -r f; do
      lines=$(wc -l < "$f" | tr -d ' ')
      if (( lines > THRESHOLD )); then printf "⚠️  %4d lines  %s\n" "$lines" "$f"; over=$((over+1))
      else printf "    %4d lines  %s\n" "$lines" "$f"; fi
    done < <({
      [[ -f "$DIR/INTRO.md" ]] && echo "$DIR/INTRO.md"
      [[ -f "$DIR/SPEC.md"  ]] && echo "$DIR/SPEC.md"
      find "$DIR/SPEC"           -maxdepth 1 -type f -name '*.md' 2>/dev/null
      find "$DIR/implementation" -maxdepth 1 -type f -name '*.md' 2>/dev/null
    } | sort -u)
    echo
    if (( over > 0 )); then
      echo "$over file(s) over threshold ($THRESHOLD lines). Consider splitting — see SPEC_CONVENTIONS.md *Splitting large specs*."
    else
      echo "All files within threshold ($THRESHOLD lines)."
    fi
    ;;
  *)
    cat >&2 <<USAGE
usage: spec-loop <verb> [args...]

verbs:
  status <deliverable>             print last-aligned hash + HEAD + commits since alignment
  diff <deliverable>               git diff <last-aligned>..HEAD over the whole deliverable folder
  code-diff <deliverable> [paths]  log + diffstat <last-aligned>..HEAD over the configured
                                   code_dirs (or given paths, or everything if neither)
  check-size <deliverable>         line counts for INTRO.md, SPEC.md (+ splits), implementation/*.md
USAGE
    exit 2
    ;;
esac
```

Make it executable: `chmod +x <spec-dir>/scripts/spec-loop.sh`.

## Invoking

Direct invocation from the repo root:

```bash
specs/scripts/spec-loop.sh status my-deliverable
specs/scripts/spec-loop.sh diff my-deliverable
specs/scripts/spec-loop.sh code-diff my-deliverable          # uses .spec-loop.toml's code_dirs
specs/scripts/spec-loop.sh code-diff my-deliverable src/api  # override
specs/scripts/spec-loop.sh check-size my-deliverable
```

If your repo overrides `spec_dir` in `.spec-loop.toml`, substitute that path
above (e.g. `docs/spec/scripts/spec-loop.sh ...`).

## Allowlist

Add **one** rule to the repo's `.claude/settings.json`:

```jsonc
{
  "permissions": {
    "Bash(specs/scripts/spec-loop.sh:*)": "allow"
  }
}
```

(Adjust the path if you've moved `<spec-dir>` via `.spec-loop.toml`.)

After that, no more per-hash permission prompts for spec-loop's read-only
operations.

## When to extend

Add a new verb to the wrapper whenever a recurring spec-loop command starts
triggering permission prompts. Keep the verb set small — four-ish verbs is
the comfort ceiling. If you're tempted to add a one-off, it probably
belongs as a regular `Bash(...)` call.

## When NOT to use

- Project-specific verification commands (Step 4's test / lint / type-check).
  Those live in `LEDGER.md`'s Config section per deliverable, with their own
  allowlist patterns.
- One-off investigation commands. The wrapper is for the loop's
  bread-and-butter operations, not for exploratory git archaeology.
