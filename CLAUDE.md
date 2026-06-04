# Skills Marketplace

This repo is a collection of Claude Code plugins/skills. Each plugin lives in `plugins/<name>/`.

When the user asks for changes, they are referring to the skills in this repo — not to the user's own project.

## Plugin layout

Every plugin uses this structure:

```
plugins/<name>/
├── .claude-plugin/
│   └── plugin.json              # manifest — keep MINIMAL, see below
├── README.md                    # marketplace-facing
└── skills/<name>/SKILL.md       # YAML frontmatter + procedure body
```

Optional add-ons (only when actually needed):

```
plugins/<name>/
├── bin/                         # helper scripts the skill invokes
├── commands/<cmd>.md            # slash command bodies — AUTO-DISCOVERED
├── hooks/                       # only when adding hooks (see "hooks" below)
└── tests/                       # plugin-local tests
```

## `plugin.json` — keep it minimal

Match the schema the existing plugins use. Only these four fields have been verified to load reliably across recent Claude Code versions:

```json
{
  "name": "<plugin-name>",
  "description": "<one-paragraph description>",
  "author": { "name": "Hans Harhoff Andersen" }
}
```

**Do NOT add fields you haven't verified.** Specifically, the following keys looked plausible from a guess at the schema but **silently broke skill discovery** when added (commit-bisected against `whats-next` on 2026-06-04):

- `version` — not parsed; harmless but unused.
- `commands: [...]` — broke loading; slash commands are **auto-discovered** from `commands/*.md` files. No manifest entry needed.
- `hooks: [...]` — broke loading; correct hook wiring is via a separate mechanism (see below) — not via plugin.json.

If a manifest has any unrecognised top-level key, the Claude Code loader may silently fail to register the plugin's skill, resulting in a `/reload-plugins` output that shows the plugin count incremented but `skills: 0`. If you see that, suspect plugin.json first.

## Slash commands

Drop a `commands/<name>.md` file. Claude Code discovers it automatically; no manifest reference needed. The `<name>` part becomes the slash-command name (e.g. `commands/whats-next.md` → `/whats-next`).

## Hooks

Adding hooks (e.g. `SessionStart`, `Stop`) is **not** done via `plugin.json`. The correct wiring lives in Claude Code's `settings.json` (per-user or per-project), not in the plugin manifest. Before adding a hook to a plugin, check the Claude Code docs for the current hook-installation mechanism — don't guess from prose.

Until you've verified the schema, ship the plugin without the hook and have the user enable it manually via `/update-config` or by editing `settings.json`. A working skill that needs one extra setup step is better than a broken manifest that silently kills skill discovery.

## SKILL.md frontmatter

```yaml
---
name: <name>            # MUST match the plugin name and the directory
description: >          # Multi-line OK. List trigger phrases concretely.
  …what the skill does and the user-typed phrases that should activate it…
---
```

The `description` is the **only** thing the matcher uses to decide whether to trigger. Be specific about the phrases ("when the user says X, Y, or Z") rather than vague intent ("when the user wants triage").

## Marketplace catalog

`.claude-plugin/marketplace.json` at the repo root lists which plugins are installable from this marketplace. **Every new plugin must be added there** — otherwise it ships in the repo but no one can install it.

Add a new entry to the `plugins[]` array:

```json
{
  "name": "<name>",
  "source": "./plugins/<name>",
  "description": "<one-paragraph user-facing description>"
}
```

Then `git push origin main`. Users refresh with `/plugin` (which updates the marketplace) followed by `/plugin install <name>@hansharhoff/skills` and `/reload-plugins`.

## Verifying a new plugin

Before declaring a new plugin ready:

1. `pytest plugins/<name>/tests/` if the plugin has tests.
2. **Manually trigger the install path** end-to-end (Hans runs this, but the steps to watch for):
   - `/plugin` refresh marketplace — expect "N plugins bumped" message.
   - `/plugin install <name>@hansharhoff/skills` — expect "Installed 1 plugin".
   - `/reload-plugins` — expect the **skill count to increment by 1**. If it doesn't, the manifest is broken.
3. After install, the skill description appears in `/skills` (or in the system reminder listing skills).
