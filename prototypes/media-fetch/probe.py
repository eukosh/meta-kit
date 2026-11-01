"""PROTOTYPE, throwaway. Creates Meta media containers that point at server.py and records what happens.

Stdlib only; never prints a token. Every call goes to results.jsonl with its test label, so
fetch-log.jsonl lines (which carry the same label in the URL path) can be joined to it.

  TUNNEL=https://x.trycloudflare.com uv run --no-project python prototypes/media-fetch/probe.py <cmd> ...

Only the publish-*, *-story and *-delete commands make anything public or remove it.
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
CONF = Path(os.environ.get("SKIT_CONFIG_DIR", Path.home() / "Library/Application Support/social-kit"))
V = "v26.0"
FB = f"https://graph.facebook.com/{V}"
TH = "https://graph.threads.net/v1.0"
RESULTS = HERE / "results.jsonl"


def creds():
    app = json.loads((CONF / "app.json").read_text())
    fb = json.loads((CONF / "logins/facebook-1435497015427790.json").read_text())
    th = json.loads(next((CONF / "logins").glob("threads-*.json")).read_text())
    page = fb["assets"][0]
    return {
        "secret": app["app_secret"],
        "page_id": page["id"],
        "page_token": page["page_token"],
        "ig_id": page["instagram"]["id"],
        "th_id": th["user_id"],
        "th_token": th["token"],
    }


C = creds()


def note(test, step, **kw):
    entry = {"t": round(time.time(), 3), "test": test, "step": step, **kw}
    with RESULTS.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    print(json.dumps(entry), flush=True)


def call(method, url, params=None, token=None, proof=True, headers=None, body=None):
    params = dict(params or {})
    if token:
        params["access_token"] = token
        if proof:
            params["appsecret_proof"] = hmac.new(C["secret"].encode(), token.encode(), hashlib.sha256).hexdigest()
    qs = urllib.parse.urlencode(params)
    if method == "POST" and body is None:
        req = urllib.request.Request(url, data=qs.encode(), method="POST", headers=headers or {})
    else:
        req = urllib.request.Request(f"{url}?{qs}" if qs else url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return {"ok": True, "body": json.loads(r.read() or b"{}")}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            err = json.loads(raw)
            err = err.get("error", err)
        except Exception:
            err = {"message": raw[:300].decode(errors="replace")}
        return {"ok": False, "http": e.code, "error": {k: err.get(k) for k in ("code", "error_subcode", "message", "error_user_title", "error_user_msg", "debug_info") if k in err}}


def media_url(test, route, name, query=False):
    base = os.environ["TUNNEL"].rstrip("/")
    url = f"{base}/{route}/{test}/{name}"
    return url + "?X-Amz-Signature=deadbeef&X-Amz-Expires=3600" if query else url


# ---------- Instagram ----------

def ig_create(test, params):
    note(test, "ig_create", params=params)
    t0 = time.time()
    r = call("POST", f"{FB}/{C['ig_id']}/media", params, C["page_token"])
    note(test, "ig_create_result", secs=round(time.time() - t0, 1), **r)
    if r["ok"]:
        return r["body"]["id"]


def ig_poll(test, cid, limit=600):
    t0 = time.time()
    while True:
        r = call("GET", f"{FB}/{cid}", {"fields": "status_code,status"}, C["page_token"])
        code = r.get("body", {}).get("status_code")
        if not r["ok"] or code in ("FINISHED", "ERROR", "EXPIRED", "PUBLISHED") or time.time() - t0 > limit:
            note(test, "ig_status", container=cid, secs=round(time.time() - t0, 1), **r)
            return code
        time.sleep(5)


def cmd_ig(a):
    p = {}
    if a.file.endswith(".mp4"):
        p["video_url"] = media_url(a.test, a.route, a.file, a.query)
        p["media_type"] = a.kind or "REELS"
    else:
        p["image_url"] = a.url or media_url(a.test, a.route, a.file, a.query)
        if a.kind:
            p["media_type"] = a.kind
    if a.child:
        p["is_carousel_item"] = "true"
    cid = ig_create(a.test, p)
    if cid:
        ig_poll(a.test, cid)


def cmd_ig_carousel(a):
    kids = []
    for i, name in enumerate(a.files):
        p = {"is_carousel_item": "true"}
        p["video_url" if name.endswith(".mp4") else "image_url"] = media_url(f"{a.test}-{i}", "m", name)
        if name.endswith(".mp4"):
            p["media_type"] = "VIDEO"
        cid = ig_create(f"{a.test}-{i}", p)
        if not cid or ig_poll(f"{a.test}-{i}", cid) != "FINISHED":
            return
        kids.append(cid)
    cid = ig_create(a.test, {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": a.caption or ""})
    if cid:
        ig_poll(a.test, cid)


def cmd_ig_resumable(a):
    path = HERE / "media" / a.file
    cid = ig_create(a.test, {"media_type": a.kind, "upload_type": "resumable"})
    if not cid:
        return
    hdr = {"Authorization": f"OAuth {C['page_token']}"}
    if a.file_url:
        hdr["file_url"] = media_url(a.test, "m", a.file)
        body = b""
    else:
        data = path.read_bytes()
        hdr["file_size"] = str(len(data))
    t0 = time.time()
    url = f"https://rupload.facebook.com/ig-api-upload/{V}/{cid}"
    if a.file_url:
        r = call("POST", url, headers=hdr, body=body)
    else:
        step = a.chunk_mb * 1024 * 1024 if a.chunk_mb else len(data)
        for off in range(0, len(data), step):
            r = call("POST", url, headers={**hdr, "offset": str(off)}, body=data[off : off + step])
            if a.chunk_mb:
                note(a.test, "rupload_chunk", offset=off, secs=round(time.time() - t0, 1), **r)
            if not r["ok"]:
                break
    note(a.test, "rupload", secs=round(time.time() - t0, 1), via="file_url" if a.file_url else "bytes", **r)
    if r["ok"]:
        ig_poll(a.test, cid)


def cmd_ig_publish(a):
    t0 = time.time()
    r = call("POST", f"{FB}/{C['ig_id']}/media_publish", {"creation_id": a.container}, C["page_token"])
    note(a.test, "ig_publish", container=a.container, secs=round(time.time() - t0, 1), **r)
    if r["ok"]:
        g = call("GET", f"{FB}/{r['body']['id']}", {"fields": "permalink,media_type,media_url,children{media_url}"}, C["page_token"])
        note(a.test, "ig_published_media", **g)


def cmd_ig_delete(a):
    note(a.test, "ig_delete", media=a.media, **call("DELETE", f"{FB}/{a.media}", token=C["page_token"]))


# ---------- Threads ----------

def th_create(test, params):
    params = {**params}
    note(test, "th_create", params=params)
    t0 = time.time()
    r = call("POST", f"{TH}/{C['th_id']}/threads", params, C["th_token"], proof=False)
    note(test, "th_create_result", secs=round(time.time() - t0, 1), **r)
    if r["ok"]:
        return r["body"]["id"]


def th_poll(test, cid, limit=600):
    t0 = time.time()
    while True:
        r = call("GET", f"{TH}/{cid}", {"fields": "status,error_message"}, C["th_token"], proof=False)
        st = r.get("body", {}).get("status")
        if not r["ok"] or st in ("FINISHED", "ERROR", "EXPIRED", "PUBLISHED") or time.time() - t0 > limit:
            note(test, "th_status", container=cid, secs=round(time.time() - t0, 1), **r)
            return st
        time.sleep(5)


def cmd_th(a):
    p = {"media_type": "VIDEO" if a.file.endswith(".mp4") else "IMAGE"}
    p["video_url" if a.file.endswith(".mp4") else "image_url"] = media_url(a.test, a.route, a.file, a.query)
    if a.alt:
        p["alt_text"] = a.alt
    if a.child:
        p["is_carousel_item"] = "true"
    cid = th_create(a.test, p)
    if cid:
        th_poll(a.test, cid)


def cmd_th_carousel(a):
    kids = []
    for i, name in enumerate(a.files):
        p = {"media_type": "IMAGE", "image_url": media_url(f"{a.test}-{i}", "m", name), "is_carousel_item": "true",
             "alt_text": f"Test image {i + 1}: generated colour test pattern"}
        cid = th_create(f"{a.test}-{i}", p)
        if not cid or th_poll(f"{a.test}-{i}", cid) != "FINISHED":
            return
        note(f"{a.test}-{i}", "th_child_fields", **call("GET", f"{TH}/{cid}", {"fields": "id,status,alt_text"}, C["th_token"], proof=False))
        kids.append(cid)
    cid = th_create(a.test, {"media_type": "CAROUSEL", "children": ",".join(kids), "text": a.text or ""})
    if cid:
        th_poll(a.test, cid)


def cmd_th_publish(a):
    t0 = time.time()
    r = call("POST", f"{TH}/{C['th_id']}/threads_publish", {"creation_id": a.container}, C["th_token"], proof=False)
    note(a.test, "th_publish", container=a.container, secs=round(time.time() - t0, 1), **r)
    if r["ok"]:
        for fields in ("permalink,media_type,children{id,media_type,alt_text}", "permalink,media_type,children{id,media_type}", "permalink,alt_text"):
            note(a.test, "th_published_media", fields=fields, **call("GET", f"{TH}/{r['body']['id']}", {"fields": fields}, C["th_token"], proof=False))


def cmd_th_delete(a):
    note(a.test, "th_delete", media=a.media, **call("DELETE", f"{TH}/{a.media}", token=C["th_token"], proof=False))


# ---------- Facebook Page ----------

def cmd_fb_photo(a):
    p = {"url": a.url or media_url(a.test, a.route, a.file, a.query), "published": "false"}
    if a.temporary:
        p["temporary"] = "true"
    note(a.test, "fb_photo", params=p)
    t0 = time.time()
    r = call("POST", f"{FB}/{C['page_id']}/photos", p, C["page_token"])
    note(a.test, "fb_photo_result", secs=round(time.time() - t0, 1), **r)
    if r["ok"]:
        note(a.test, "fb_photo_fields", **call("GET", f"{FB}/{r['body']['id']}", {"fields": "images,width,height"}, C["page_token"]))


def cmd_fb_video(a):
    p = {"file_url": media_url(a.test, a.route, a.file, a.query), "published": "false", "description": "social-kit fetch test"}
    note(a.test, "fb_video", params=p)
    t0 = time.time()
    r = call("POST", f"{FB}/{C['page_id']}/videos", p, C["page_token"])
    note(a.test, "fb_video_result", secs=round(time.time() - t0, 1), **r)
    if r["ok"]:
        fb_video_poll(a.test, r["body"]["id"])


def fb_video_poll(test, vid, limit=600):
    t0 = time.time()
    while True:
        r = call("GET", f"{FB}/{vid}", {"fields": "status"}, C["page_token"])
        st = r.get("body", {}).get("status", {})
        done = st.get("video_status") in ("ready", "error", "expired") or st.get("processing_phase", {}).get("status") in ("complete", "error")
        if not r["ok"] or done or time.time() - t0 > limit:
            note(test, "fb_video_status", video=vid, secs=round(time.time() - t0, 1), **r)
            return st
        time.sleep(5)


def fb_rupload(test, kind, a):
    """video_reels / video_stories: start, upload by file_url, finish."""
    start = call("POST", f"{FB}/{C['page_id']}/{kind}", {"upload_phase": "start"}, C["page_token"])
    note(test, f"{kind}_start", **start)
    if not start["ok"]:
        return None
    vid = start["body"]["video_id"]
    hdr = {"Authorization": f"OAuth {C['page_token']}"}
    if a.bytes:
        body = (HERE / "media" / a.file).read_bytes()
        hdr.update({"offset": "0", "file_size": str(len(body))})
    else:
        hdr["file_url"] = media_url(test, a.route, a.file, a.query)
        body = b""
    t0 = time.time()
    up = call("POST", f"https://rupload.facebook.com/video-upload/{V}/{vid}", headers=hdr, body=body)
    note(test, f"{kind}_upload", secs=round(time.time() - t0, 1), via="bytes" if a.bytes else "file_url", **up)
    if not up["ok"]:
        return None
    return vid


def cmd_fb_reel(a):
    vid = fb_rupload(a.test, "video_reels", a)
    if vid:
        note(a.test, "video_status_before_finish", **call("GET", f"{FB}/{vid}", {"fields": "status"}, C["page_token"]))
        p = {"upload_phase": "finish", "video_id": vid, "video_state": "DRAFT", "description": "social-kit fetch test"}
        note(a.test, "video_reels_finish", **call("POST", f"{FB}/{C['page_id']}/video_reels", p, C["page_token"]))
        fb_video_poll(a.test, vid)


def cmd_fb_story(a):
    """Public: posts a Page story."""
    if a.file.endswith(".mp4"):
        vid = fb_rupload(a.test, "video_stories", a)
        if vid:
            note(a.test, "video_stories_finish", **call("POST", f"{FB}/{C['page_id']}/video_stories", {"upload_phase": "finish", "video_id": vid}, C["page_token"]))
            fb_video_poll(a.test, vid)
    else:
        r = call("POST", f"{FB}/{C['page_id']}/photos", {"url": media_url(a.test, a.route, a.file), "published": "false"}, C["page_token"])
        note(a.test, "fb_photo_result", **r)
        if r["ok"]:
            note(a.test, "photo_stories", **call("POST", f"{FB}/{C['page_id']}/photo_stories", {"photo_id": r["body"]["id"]}, C["page_token"]))


def cmd_fb_get(a):
    note(a.test, "fb_get", obj=a.obj, **call("GET", f"{FB}/{a.obj}", {"fields": a.fields} if a.fields else None, C["page_token"]))


def cmd_fb_delete(a):
    note(a.test, "fb_delete", obj=a.obj, **call("DELETE", f"{FB}/{a.obj}", token=C["page_token"]))


# ---------- misc ----------

def cmd_check(a):
    note("check", "ig", **call("GET", f"{FB}/{C['ig_id']}", {"fields": "username"}, C["page_token"]))
    note("check", "ig_limit", **call("GET", f"{FB}/{C['ig_id']}/content_publishing_limit", {"fields": "quota_usage,config"}, C["page_token"]))
    note("check", "page", **call("GET", f"{FB}/{C['page_id']}", {"fields": "name"}, C["page_token"]))
    note("check", "threads", **call("GET", f"{TH}/me", {"fields": "username"}, C["th_token"], proof=False))
    note("check", "threads_limit", **call("GET", f"{TH}/{C['th_id']}/threads_publishing_limit", {"fields": "quota_usage,config"}, C["th_token"], proof=False))


def cmd_kill(a):
    k = HERE / "media" / "KILL"
    k.touch() if a.state == "on" else k.unlink(missing_ok=True)
    note("kill", a.state)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    def media_args(s):
        s.add_argument("test")
        s.add_argument("file")
        s.add_argument("--route", default="m", choices=["m", "r301", "r302", "noct", "octet"])
        s.add_argument("--query", action="store_true", help="append a presigned-style query string")

    s = sub.add_parser("ig"); media_args(s); s.add_argument("--kind"); s.add_argument("--child", action="store_true"); s.add_argument("--url"); s.set_defaults(f=cmd_ig)
    s = sub.add_parser("ig-carousel"); s.add_argument("test"); s.add_argument("files", nargs="+"); s.add_argument("--caption"); s.set_defaults(f=cmd_ig_carousel)
    s = sub.add_parser("ig-resumable"); s.add_argument("test"); s.add_argument("file"); s.add_argument("--kind", default="REELS"); s.add_argument("--file-url", action="store_true"); s.add_argument("--chunk-mb", type=int); s.set_defaults(f=cmd_ig_resumable)
    s = sub.add_parser("ig-publish"); s.add_argument("test"); s.add_argument("container"); s.set_defaults(f=cmd_ig_publish)
    s = sub.add_parser("ig-delete"); s.add_argument("test"); s.add_argument("media"); s.set_defaults(f=cmd_ig_delete)
    s = sub.add_parser("th"); media_args(s); s.add_argument("--alt"); s.add_argument("--child", action="store_true"); s.set_defaults(f=cmd_th)
    s = sub.add_parser("th-carousel"); s.add_argument("test"); s.add_argument("files", nargs="+"); s.add_argument("--text"); s.set_defaults(f=cmd_th_carousel)
    s = sub.add_parser("th-publish"); s.add_argument("test"); s.add_argument("container"); s.set_defaults(f=cmd_th_publish)
    s = sub.add_parser("th-delete"); s.add_argument("test"); s.add_argument("media"); s.set_defaults(f=cmd_th_delete)
    s = sub.add_parser("fb-photo"); media_args(s); s.add_argument("--url"); s.add_argument("--temporary", action="store_true"); s.set_defaults(f=cmd_fb_photo)
    s = sub.add_parser("fb-video"); media_args(s); s.set_defaults(f=cmd_fb_video)
    s = sub.add_parser("fb-reel"); media_args(s); s.add_argument("--bytes", action="store_true"); s.set_defaults(f=cmd_fb_reel)
    s = sub.add_parser("fb-story"); media_args(s); s.add_argument("--bytes", action="store_true"); s.set_defaults(f=cmd_fb_story)
    s = sub.add_parser("fb-get"); s.add_argument("test"); s.add_argument("obj"); s.add_argument("--fields"); s.set_defaults(f=cmd_fb_get)
    s = sub.add_parser("fb-delete"); s.add_argument("test"); s.add_argument("obj"); s.set_defaults(f=cmd_fb_delete)
    sub.add_parser("check").set_defaults(f=cmd_check)
    s = sub.add_parser("kill"); s.add_argument("state", choices=["on", "off"]); s.set_defaults(f=cmd_kill)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    sys.exit(main())
