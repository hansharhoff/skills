#!/usr/bin/env python3
"""Create / update / list posts on hansharhoff.dk/blog via the WordPress REST API.

Reads credentials from credentials.env next to this script.
Notes about this specific site:
  - The TLS certificate chain does not fully validate (host-side, Simply.com),
    so certificate verification is relaxed for the connection.
  - A host WAF challenges browser-like User-Agents and blocks front-end page
    fetches (HTTP 454/455). Do NOT verify a post by fetching its public URL with
    a script -- trust the API response (status/link) instead. Keep the default
    (non-browser) User-Agent; do not send a "Mozilla" UA.

Examples:
  python3 publish.py list
  python3 publish.py create --title "My post" --content-file post.html --status draft
  python3 publish.py update --id 297 --content-file post.html
  python3 publish.py publish --id 297      # flip an existing draft to live
"""
import os, sys, json, ssl, base64, argparse, subprocess, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))

def _resolve(val):
    """Resolve a 1Password secret reference (op://...) via the `op` CLI; pass others through."""
    if val.startswith("op://"):
        try:
            out = subprocess.run(["op", "read", val], capture_output=True, text=True, check=True)
            return out.stdout.strip()
        except FileNotFoundError:
            raise SystemExit("1Password CLI `op` not found. Install it and sign in, or use a plaintext value.")
        except subprocess.CalledProcessError as e:
            raise SystemExit(f"Could not read {val} from 1Password: {e.stderr.strip()}")
    return val

def load_creds():
    """Credentials come from (in order of precedence): environment variables, then
    credentials.env in this folder. Any value may be a 1Password reference (op://...)."""
    creds = {}
    path = os.path.join(HERE, "credentials.env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip()
    for k in ("WP_SITE", "WP_USER", "WP_APP_PW"):          # env overrides the file
        if os.environ.get(k):
            creds[k] = os.environ[k]
    missing = [k for k in ("WP_SITE", "WP_USER", "WP_APP_PW") if not creds.get(k)]
    if missing:
        raise SystemExit("Missing credentials: " + ", ".join(missing) +
                         f".\nSet them as env vars or in {path} (copy credentials.env.example).")
    site = _resolve(creds["WP_SITE"]).rstrip("/")
    user = _resolve(creds["WP_USER"])
    pw = _resolve(creds["WP_APP_PW"]).replace(" ", "")     # WP ignores spaces in app passwords
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return site, auth

def call(method, path, auth, body=None):
    site, _ = None, None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(path, data=data, method=method, headers=headers)
    try:
        r = urllib.request.urlopen(req, context=ctx, timeout=45)
        return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:500]}

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="action", required=True)
    p_list = sub.add_parser("list"); p_list.add_argument("--per-page", type=int, default=10)
    p_get = sub.add_parser("get"); p_get.add_argument("--id", type=int, required=True)
    for name in ("create", "update", "publish"):
        p = sub.add_parser(name)
        if name != "create":
            p.add_argument("--id", type=int, required=True)
        p.add_argument("--title")
        p.add_argument("--content-file")
        p.add_argument("--excerpt")
        p.add_argument("--status", choices=["draft", "publish", "pending", "private"])
        p.add_argument("--categories", help="comma-separated category IDs")
        p.add_argument("--tags", help="comma-separated tag IDs")
    args = ap.parse_args()

    site, auth = load_creds()
    base = f"{site}/wp-json/wp/v2/posts"

    if args.action == "list":
        s, d = call("GET", f"{base}?per_page={args.per_page}&status=publish,draft,pending,private", auth)
        print("HTTP", s)
        for p in (d if isinstance(d, list) else []):
            print(f'  [{p["id"]}] {p["status"]:8} {p["title"]["rendered"]}  -> {p["link"]}')
        return
    if args.action == "get":
        s, d = call("GET", f"{base}/{args.id}?context=edit", auth)
        print("HTTP", s, json.dumps(d, indent=2)[:1500]); return

    payload = {}
    if getattr(args, "title", None): payload["title"] = args.title
    if getattr(args, "content_file", None):
        with open(args.content_file, encoding="utf-8") as f: payload["content"] = f.read()
    if getattr(args, "excerpt", None): payload["excerpt"] = args.excerpt
    if getattr(args, "status", None): payload["status"] = args.status
    if getattr(args, "categories", None): payload["categories"] = [int(x) for x in args.categories.split(",")]
    if getattr(args, "tags", None): payload["tags"] = [int(x) for x in args.tags.split(",")]

    if args.action == "create":
        payload.setdefault("status", "draft")   # safe default: never auto-publish
        s, d = call("POST", base, auth, payload)
    elif args.action == "update":
        s, d = call("POST", f"{base}/{args.id}", auth, payload)
    elif args.action == "publish":
        payload["status"] = "publish"
        s, d = call("POST", f"{base}/{args.id}", auth, payload)

    print("HTTP", s)
    if isinstance(d, dict) and "id" in d:
        print("id:", d["id"], "status:", d.get("status"))
        print("link:", d.get("link"))
        print("edit:", f'{site}/wp-admin/post.php?post={d["id"]}&action=edit')
    else:
        print(d)

if __name__ == "__main__":
    main()
