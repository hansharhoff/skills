# post-to-hansharhoff-blog

Publish and update posts on the WordPress blog at **hansharhoff.dk/blog** via the WordPress
REST API. Also handles two quirks of that host: an incomplete TLS certificate chain and a
bot-protection WAF that blocks browser-like requests.

> This is a personal plugin tied to one specific site. It's shared as a worked example of
> driving WordPress from Claude Code with **credentials kept out of the repo**.

## Setup

Credentials are read (in order of precedence) from environment variables, then a local
`credentials.env` file — which is **gitignored and never committed**.

```bash
cd skills/post-to-hansharhoff-blog
cp credentials.env.example credentials.env   # then edit; chmod 600 credentials.env
```

`WP_APP_PW` is a WordPress **Application Password** (WP admin → Users → Profile → Application
Passwords). It can be a literal value, or a **1Password reference** such as
`op://Private/hansharhoff-blog/credential`, which is resolved at runtime via the `op` CLI so no
plaintext secret is stored on disk. On a new machine you can simply mint a fresh Application
Password there instead of copying the secret.

## Usage

```bash
python3 skills/post-to-hansharhoff-blog/publish.py list
python3 skills/post-to-hansharhoff-blog/publish.py create --title "T" --content-file post.html   # draft
python3 skills/post-to-hansharhoff-blog/publish.py publish --id 297                               # go live
```

New posts default to **draft**; going live is a deliberate second step. See `SKILL.md` for the
full workflow and the site-specific TLS/WAF notes.
