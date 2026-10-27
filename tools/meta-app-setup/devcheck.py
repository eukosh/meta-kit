"""Throwaway helper for the dev-app task ticket: OAuth logins and live checks.

Stdlib only. Never prints a token or secret: ids, scopes, dates and Graph error
codes only. Reads app.json and dev-setup.env from the social-kit config dir and
writes login files in the layout decided for social-kit.
"""

import argparse
import hashlib
import hmac
import http.server
import json
import os
import secrets
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

GRAPH_VERSION = os.environ.get("DEV_GRAPH_VERSION", "v26.0")
FB_GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
TH_GRAPH = "https://graph.threads.com"
PORT = 8765
REDIRECT = f"http://localhost:{PORT}/callback"

FB_SCOPES = [
    "pages_show_list", "pages_read_engagement", "pages_manage_posts", "pages_manage_engagement",
    "pages_read_user_content", "pages_manage_metadata", "pages_messaging", "read_insights",
    "business_management", "instagram_basic", "instagram_content_publish",
    "instagram_manage_comments", "instagram_manage_insights", "instagram_manage_messages",
    "instagram_manage_contents", "instagram_manage_engagement",
]
TH_SCOPES = [
    "threads_basic", "threads_content_publish", "threads_delete", "threads_keyword_search",
    "threads_location_tagging", "threads_manage_insights", "threads_manage_mentions",
    "threads_manage_replies", "threads_profile_discovery", "threads_read_replies",
]


def config_dir() -> Path:
    if os.environ.get("SKIT_CONFIG_DIR"):
        return Path(os.environ["SKIT_CONFIG_DIR"])
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/social-kit"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "social-kit"


def app() -> dict:
    return json.loads((config_dir() / "app.json").read_text())


def write_private(path: Path, data: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def when(ts) -> str:
    if not ts:
        return "never"
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%d")


class GraphError(Exception):
    def __init__(self, status, body):
        err = body.get("error", body) if isinstance(body, dict) else {"message": str(body)}
        self.short = f"HTTP {status} code={err.get('code')} sub={err.get('error_subcode')}: {str(err.get('message'))[:140]}"
        super().__init__(self.short)


def call(method: str, url: str, token: str | None = None, params: dict | None = None, proof: str | None = None):
    params = dict(params or {})
    if token:
        params["access_token"] = token
        if proof:
            params["appsecret_proof"] = hmac.new(proof.encode(), token.encode(), hashlib.sha256).hexdigest()
    data = None
    if method == "POST":
        data = urllib.parse.urlencode(params).encode()
    else:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
        except Exception:
            body = {"message": e.reason}
        raise GraphError(e.code, body) from None


def browser_code(auth_url: str, state: str) -> str:
    """Open the consent page and wait for the redirect on localhost, or take the pasted redirect URL."""
    got: dict = {}
    redirect = urllib.parse.parse_qs(urllib.parse.urlparse(auth_url).query)["redirect_uri"][0]
    if not redirect.startswith("http://localhost"):
        print(f"Opening the consent page. If no browser opens, visit:\n{auth_url}\n", flush=True)
        webbrowser.open(auth_url)
        pasted = input("After approving, the browser lands on a page that may not load.\n"
                       "Paste that page's full address here: ").strip()
        got.update({k: v[0] for k, v in urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query).items()})
        if "error" in got:
            sys.exit(f"Consent failed: {got.get('error')} {got.get('error_reason', '')} {got.get('error_description', '')}")
        if got.get("state") != state:
            sys.exit("State mismatch; aborting.")
        return got["code"].removesuffix("#_")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if urllib.parse.urlparse(self.path).path.rstrip("/") == "/callback":
                got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Done. You can close this tab and go back to the terminal.")

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Opening the consent page. If no browser opens, visit:\n{auth_url}\n", flush=True)
    webbrowser.open(auth_url)
    deadline = time.time() + 600
    while not got and time.time() < deadline:
        server.timeout = 5
        server.handle_request()
    server.server_close()
    if not got:
        sys.exit("No redirect within 10 minutes.")
    if "error" in got:
        sys.exit(f"Consent failed: {got.get('error')} {got.get('error_reason', '')} {got.get('error_description', '')}")
    if got.get("state") != state:
        sys.exit("State mismatch; aborting.")
    return got["code"].removesuffix("#_")


def fb_assets(token: str, secret: str) -> list[dict]:
    fields = "id,name,username,access_token,tasks,instagram_business_account{id,username}"
    pages = call("GET", f"{FB_GRAPH}/me/accounts", token, {"fields": fields, "limit": 100}, secret).get("data", [])
    return [
        {
            "platform": "facebook", "id": p["id"], "name": p.get("name"), "username": p.get("username"),
            "tasks": p.get("tasks"), "page_token": p.get("access_token"),
            "instagram": p.get("instagram_business_account"),
        }
        for p in pages
    ]


def fb_debug(token: str, a: dict) -> dict:
    return call("GET", f"{FB_GRAPH}/debug_token", f"{a['app_id']}|{a['app_secret']}", {"input_token": token})["data"]


def save_fb_login(kind: str, token: str, a: dict) -> Path:
    d = fb_debug(token, a)
    me = call("GET", f"{FB_GRAPH}/me", token, {"fields": "id,name"}, a["app_secret"])
    assets = fb_assets(token, a["app_secret"])
    login = {
        "kind": kind, "app_id": a["app_id"], "user_id": me["id"], "name": me.get("name"),
        "token": token, "issued_at": d.get("issued_at"), "expires_at": d.get("expires_at"),
        "data_access_expires_at": d.get("data_access_expires_at"), "scopes": d.get("scopes", []),
        "granular_scopes": d.get("granular_scopes", []), "assets": assets,
    }
    path = config_dir() / "logins" / f"facebook-{me['id']}.json"
    write_private(path, login)
    print(f"Login {kind}: {me.get('name')} ({me['id']}), app {d.get('app_id')}")
    print(f"  token expires {when(d.get('expires_at'))}, data access until {when(d.get('data_access_expires_at'))}")
    print(f"  scopes: {' '.join(sorted(d.get('scopes', [])))}")
    for asset in assets:
        ig = asset["instagram"] or {}
        pd = fb_debug(asset["page_token"], a) if asset["page_token"] else {}
        print(f"  Page {asset['name']} ({asset['id']}) tasks={asset['tasks']} page token expires {when(pd.get('expires_at'))}"
              f" -> Instagram {ig.get('username')} ({ig.get('id')})")
    print(f"  saved {path}")
    return path


def cmd_login_facebook(args):
    a = app()
    state = secrets.token_urlsafe(16)
    url = "https://www.facebook.com/{}/dialog/oauth?{}".format(GRAPH_VERSION, urllib.parse.urlencode({
        "client_id": a["app_id"], "redirect_uri": args.redirect, "state": state,
        "response_type": "code", "scope": ",".join(args.scopes or FB_SCOPES),
    }))
    code = browser_code(url, state)
    short = call("GET", f"{FB_GRAPH}/oauth/access_token", None, {
        "client_id": a["app_id"], "client_secret": a["app_secret"], "redirect_uri": args.redirect, "code": code,
    })["access_token"]
    long = call("GET", f"{FB_GRAPH}/oauth/access_token", None, {
        "grant_type": "fb_exchange_token", "client_id": a["app_id"], "client_secret": a["app_secret"],
        "fb_exchange_token": short,
    })["access_token"]
    save_fb_login("oauth", long, a)


def cmd_login_unified(args):
    """Facebook Login for Business configuration that issues a system-user token (Instagram Unified login)."""
    a = app()
    state = secrets.token_urlsafe(16)
    url = "https://www.facebook.com/{}/dialog/oauth?{}".format(GRAPH_VERSION, urllib.parse.urlencode({
        "client_id": a["app_id"], "redirect_uri": args.redirect, "state": state, "config_id": args.config_id,
        "response_type": "code", "override_default_response_type": "true",
    }))
    code = browser_code(url, state)
    token = call("GET", f"{FB_GRAPH}/oauth/access_token", None, {
        "client_id": a["app_id"], "client_secret": a["app_secret"], "redirect_uri": args.redirect, "code": code,
    })["access_token"]
    d = fb_debug(token, a)
    print(f"  debug_token: type={d.get('type')} user_id={d.get('user_id')} profile_id={d.get('profile_id')}")
    for g in d.get("granular_scopes", []):
        print(f"  granular {g.get('scope')}: {g.get('target_ids')}")
    me = call("GET", f"{FB_GRAPH}/me", token, {"fields": "id,name"}, a["app_secret"])
    ig_ids = sorted({t for g in d.get("granular_scopes", []) if g["scope"].startswith("instagram") for t in g.get("target_ids", [])})
    assets = []
    for ig in ig_ids:
        try:
            info = call("GET", f"{FB_GRAPH}/{ig}", token, {"fields": "id,username"}, a["app_secret"])
            assets.append({"platform": "instagram", "id": info["id"], "username": info.get("username")})
        except GraphError as e:
            print(f"  FAIL  read {ig}: {e.short}")
    try:
        assets += fb_assets(token, a["app_secret"])
    except GraphError as e:
        print(f"  /me/accounts: {e.short}")
    login = {
        "kind": "unified", "app_id": a["app_id"], "user_id": me["id"], "name": me.get("name"), "token": token,
        "issued_at": d.get("issued_at"), "expires_at": d.get("expires_at"),
        "data_access_expires_at": d.get("data_access_expires_at"), "scopes": d.get("scopes", []),
        "granular_scopes": d.get("granular_scopes", []), "config_id": args.config_id, "assets": assets,
    }
    path = config_dir() / "logins" / f"facebook-{me['id']}.json"
    write_private(path, login)
    print(f"Login unified: {me.get('name')} ({me['id']})")
    print(f"  token expires {when(d.get('expires_at'))}, data access until {when(d.get('data_access_expires_at'))}")
    print(f"  scopes: {' '.join(sorted(d.get('scopes', [])))}")
    print(f"  assets: {[(x.get('platform'), x.get('username') or x.get('name')) for x in assets]}")
    print(f"  saved {path}")


def cmd_login_threads(args):
    a = app()
    state = secrets.token_urlsafe(16)
    url = "https://threads.com/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": a["threads_app_id"], "redirect_uri": args.redirect, "state": state,
        "response_type": "code", "scope": ",".join(args.scopes or TH_SCOPES),
    })
    code = browser_code(url, state)
    short = call("POST", f"{TH_GRAPH}/oauth/access_token", None, {
        "client_id": a["threads_app_id"], "client_secret": a["threads_app_secret"], "code": code,
        "grant_type": "authorization_code", "redirect_uri": args.redirect,
    })["access_token"]
    long = call("GET", f"{TH_GRAPH}/access_token", None, {
        "grant_type": "th_exchange_token", "client_secret": a["threads_app_secret"], "access_token": short,
    })
    token = long["access_token"]
    me = call("GET", f"{TH_GRAPH}/v1.0/me", token, {"fields": "id,username"})
    try:
        d = call("GET", f"{TH_GRAPH}/v1.0/debug_token",
                 f"TH|{a['threads_app_id']}|{a['threads_app_secret']}", {"input_token": token}).get("data", {})
    except GraphError as e:
        print(f"  debug_token failed: {e.short}")
        d = {}
    login = {
        "kind": "threads", "app_id": a["threads_app_id"], "user_id": me["id"], "token": token,
        "issued_at": d.get("issued_at"), "expires_at": d.get("expires_at") or int(time.time()) + int(long.get("expires_in", 0)),
        "data_access_expires_at": d.get("data_access_expires_at"), "scopes": d.get("scopes", []),
        "assets": [{"platform": "threads", "id": me["id"], "username": me.get("username")}],
    }
    path = config_dir() / "logins" / f"threads-{me['id']}.json"
    write_private(path, login)
    print(f"Login threads: @{me.get('username')} ({me['id']}), type {d.get('type')}")
    print(f"  token expires {when(login['expires_at'])}")
    print(f"  scopes: {' '.join(sorted(d.get('scopes', [])))}")
    print(f"  saved {path}")


def cmd_import_system_user(args):
    a = app()
    env = config_dir() / "dev-setup.env"
    lines = env.read_text().splitlines()
    tok = next(l.split("=", 1)[1].strip("'") for l in lines if l.startswith("DEV_SYSTEM_USER_TOKEN="))
    save_fb_login("system_user", tok, a)
    env.write_text("\n".join(l for l in lines if not l.startswith("DEV_SYSTEM_USER_TOKEN=")) + "\n")
    print("  removed the token from dev-setup.env; the login file holds the only copy")


def cmd_rediscover(args):
    """Re-read Pages and their linked Instagram accounts for the stored Facebook logins."""
    a = app()
    found = False
    for login in logins():
        if login["kind"] in ("oauth", "system_user"):
            save_fb_login(login["kind"], login["token"], a)
            found |= any((x.get("instagram") or {}).get("username") for x in json.loads(
                (config_dir() / "logins" / f"facebook-{login['user_id']}.json").read_text())["assets"])
    print("\nInstagram linked to a Page: " + ("YES" if found else "NO"))
    sys.exit(0 if found else 1)


def logins() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted((config_dir() / "logins").glob("facebook-*.json"))]


def cmd_check(args):
    """Live checks 1 and 2: which Facebook-side tokens the Instagram endpoints accept."""
    a = app()
    s = a["app_secret"]
    tokens: list[tuple[str, str]] = []
    ig_id = page_id = None
    for login in logins():
        tokens.append((f"{login['kind']} user", login["token"]))
        for asset in login["assets"]:
            if asset.get("platform") == "instagram" and not ig_id:
                ig_id = asset["id"]
            if asset.get("platform") == "instagram":
                continue
            if asset.get("instagram") and (not args.ig or asset["instagram"].get("username") == args.ig):
                ig_id, page_id = asset["instagram"]["id"], asset["id"]
                tokens.append((f"{login['kind']} page", asset["page_token"]))
                break
    if not ig_id:
        sys.exit("No Instagram account found in any Facebook login.")

    media_id = None
    for _, t in tokens:
        try:
            media_id = call("GET", f"{FB_GRAPH}/{ig_id}/media", t, {"limit": 1}, s)["data"][0]["id"]
            break
        except Exception:
            continue

    probes = {
        "profile": ("GET", f"{ig_id}", {"fields": "id,username,followers_count,media_count"}),
        "feed": ("GET", f"{ig_id}/media", {"fields": "id,media_type,timestamp", "limit": 3}),
        "comments": ("GET", f"{media_id}/comments", {"fields": "id,timestamp", "limit": 3}),
        "account insights": ("GET", f"{ig_id}/insights", {"metric": "reach", "period": "day"}),
        "media insights": ("GET", f"{media_id}/insights", {"metric": "reach"}),
        "publishing limit": ("GET", f"{ig_id}/content_publishing_limit", {}),
        "ig conversations": ("GET", f"{page_id}/conversations", {"platform": "instagram", "limit": 1}),
    }
    if args.image_url:
        probes["create container"] = ("POST", f"{ig_id}/media", {"image_url": args.image_url, "caption": args.caption})

    containers: dict[str, str] = {}
    for label, t in tokens:
        print(f"\n[{label} token]")
        for name, (method, path, params) in probes.items():
            try:
                out = call(method, f"{FB_GRAPH}/{path}", t, params, s)
                if name == "create container":
                    containers[label] = out["id"]
                print(f"  OK    {name}")
            except GraphError as e:
                print(f"  FAIL  {name}: {e.short}")

    if args.publish_with:
        cmd_publish_delete(args, a, tokens, ig_id, containers)


def cmd_publish_delete(args, a, tokens, ig_id, containers):
    s = a["app_secret"]
    label = args.publish_with
    token = dict(tokens)[label]
    container = containers.get(label)
    if not container:
        sys.exit(f"No container was created with the {label} token; nothing to publish.")
    print(f"\n[publish then delete, {label} token]")
    for _ in range(30):
        status = call("GET", f"{FB_GRAPH}/{container}", token, {"fields": "status_code"}, s).get("status_code")
        if status == "FINISHED":
            break
        time.sleep(2)
    try:
        media = call("POST", f"{FB_GRAPH}/{ig_id}/media_publish", token, {"creation_id": container}, s)["id"]
        print(f"  OK    media_publish -> media {media}")
    except GraphError as e:
        print(f"  FAIL  media_publish: {e.short}")
        return
    if args.keep:
        link = call("GET", f"{FB_GRAPH}/{media}", token, {"fields": "permalink"}, s).get("permalink")
        print(f"  kept live: {link}\n  delete later with: devcheck.py delete {media} --first '{label}'")
        return
    delete_media(media, tokens, label, s)


def delete_media(media, tokens, first, s):
    for other, t in [x for x in tokens if x[0] == first] + [x for x in tokens if x[0] != first]:
        try:
            call("DELETE", f"{FB_GRAPH}/{media}", t, None, s)
            print(f"  OK    delete with {other} token")
            return
        except GraphError as e:
            print(f"  FAIL  delete with {other} token: {e.short}")
    print(f"  !! media {media} is still live: delete it in the Instagram app")


def fb_tokens() -> list[tuple[str, str]]:
    tokens = []
    for login in logins():
        tokens.append((f"{login['kind']} user", login["token"]))
        tokens += [(f"{login['kind']} page", x["page_token"]) for x in login["assets"] if x.get("page_token")]
    return tokens


def cmd_delete(args):
    print(f"[delete {args.media_id}]")
    delete_media(args.media_id, fb_tokens(), args.first, app()["app_secret"])


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)
    for name, fn in (("login-facebook", cmd_login_facebook), ("login-threads", cmd_login_threads)):
        sp = sub.add_parser(name)
        sp.add_argument("--redirect", default=REDIRECT)
        sp.add_argument("--scopes", nargs="*")
        sp.set_defaults(fn=fn)
    sp = sub.add_parser("login-unified")
    sp.add_argument("config_id")
    sp.add_argument("--redirect", default=REDIRECT)
    sp.set_defaults(fn=cmd_login_unified)
    sub.add_parser("import-system-user").set_defaults(fn=cmd_import_system_user)
    sub.add_parser("rediscover").set_defaults(fn=cmd_rediscover)
    sp = sub.add_parser("check")
    sp.add_argument("--ig", help="Instagram username to test against")
    sp.add_argument("--image-url", help="public JPEG; adds a container-creation probe (nothing is published)")
    sp.add_argument("--caption", default="social-kit API test. Deleting this right away.")
    sp.add_argument("--publish-with", help="token label, e.g. 'oauth page': publish its container, then delete")
    sp.add_argument("--keep", action="store_true", help="publish but leave the post up; delete with the delete command")
    sp.set_defaults(fn=cmd_check)
    sp = sub.add_parser("delete")
    sp.add_argument("media_id")
    sp.add_argument("--first", default="oauth page", help="token label to try first")
    sp.set_defaults(fn=cmd_delete)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
