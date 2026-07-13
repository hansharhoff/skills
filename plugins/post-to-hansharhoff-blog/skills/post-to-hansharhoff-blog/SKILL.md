---
name: post-to-hansharhoff-blog
description: Publish or update posts on Hans's personal WordPress blog at hansharhoff.dk/blog. Use when the user asks to post, publish, draft, or update something on "my blog", hansharhoff.dk, or hansharhoff.dk/blog. Handles auth, the site's broken TLS chain, and its bot-protection WAF.
---

# Post to hansharhoff.dk/blog

Publishes to Hans's self-hosted WordPress (host: Simply.com) via the REST API.

## Credentials
`publish.py` needs `WP_SITE`, `WP_USER`, `WP_APP_PW`. It loads them, in order of precedence:
1. **Environment variables** `WP_SITE` / `WP_USER` / `WP_APP_PW`.
2. **`credentials.env`** in this folder (copy `credentials.env.example` → `credentials.env`, `chmod 600`).
   This file is **gitignored — never commit it.**

`WP_APP_PW` is a WordPress **Application Password** (WP admin → Users → Profile → Application Passwords;
revocable there). Any value may be a **1Password reference** like `op://Private/hansharhoff-blog/credential`,
which `publish.py` resolves at runtime via the `op` CLI — so no plaintext secret need ever touch disk.
Tip: on a new machine you can just mint a *fresh* Application Password there instead of copying the secret.

Never print the password in output or commit it anywhere.

## Golden rule — approval before going live
Hans's standing instruction: **always show him exactly what will be published and get explicit
approval before anything goes live.** Therefore:
1. Draft the post content as WordPress-block HTML in a local file.
2. Show it to him (a rendered Artifact preview is ideal) and wait for explicit approval.
3. Only after he approves, publish live. `publish.py create` defaults to `status=draft` on purpose —
   publishing live is a deliberate second step (`--status publish`, or `publish.py publish --id N`).

## How to publish
Use `publish.py` in this folder (reads `credentials.env` itself):

```
python3 publish.py list                                             # recent posts + IDs
python3 publish.py create --title "T" --content-file post.html      # creates a DRAFT
python3 publish.py create --title "T" --content-file post.html --status publish   # live (only after approval)
python3 publish.py update --id 297 --content-file post.html         # edit existing (keeps its status)
python3 publish.py publish --id 297                                 # flip a draft to live
python3 publish.py get --id 297                                     # inspect a post
```
Optional flags: `--excerpt "..."`, `--categories 1,4`, `--tags 12,15`.

Content is the `content` field: WordPress **block** HTML (`<!-- wp:paragraph -->…`) renders as proper
blocks in the editor; plain HTML also works.

## Site-specific gotchas (important)
- **TLS chain is incomplete — KNOWN & ACCEPTED, do NOT re-raise it.** The server sends only the leaf
  cert and omits the Let's Encrypt intermediate (issuer CN "YR1"), so strict clients get
  `unable to verify the first certificate` (OpenSSL verify code 21). Hans is aware and has chosen to
  leave it; don't flag it, audit it, or suggest fixing it again. Just work around it: `publish.py`
  relaxes certificate verification so requests connect (still HTTPS-encrypted).
- **Bot-protection WAF**: the host challenges browser-like requests and blocks front-end page fetches
  and `?rest_route=` with HTTP **454/455** ("Checking your browser" / "Security Incident Detected").
  Consequences:
  - Do **not** verify a published post by fetching its public URL with a script — it'll get challenged.
    Trust the API response (`status`, `link`, HTTP 201/200) instead, or have Hans open it in a browser.
  - Keep the default (non-browser) User-Agent. Sending a `Mozilla/...` UA triggers the challenge;
    plain `curl`/`urllib` UAs pass. `publish.py` already does this.
- REST API base: `https://hansharhoff.dk/blog/wp-json/wp/v2/`.

## After publishing
Give Hans the live `link` and the `edit:` URL from the output. Offer tweaks (title, tags, category,
images). The default category is 1 (Uncategorized) unless `--categories` is given.
