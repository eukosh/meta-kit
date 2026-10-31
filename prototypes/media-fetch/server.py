"""PROTOTYPE, throwaway. Serves test media and logs every request Meta makes.

Run: uv run --no-project python prototypes/media-fetch/server.py
Then expose it: cloudflared tunnel --url http://127.0.0.1:8770

Routes (TEST is any label the probe puts in the path, so log lines map to tests):
  /m/TEST/FILE        the file, correct Content-Type, Range supported
  /r302/TEST/FILE     302 to /m/TEST/FILE   (/r301 for 301)
  /noct/TEST/FILE     no Content-Type header
  /octet/TEST/FILE    Content-Type: application/octet-stream
  /robots.txt         allow all
Touching media/KILL makes every media route answer 404 until the file is removed.
"""

import json
import mimetypes
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).parent
MEDIA = HERE / "media"
LOG = HERE / "fetch-log.jsonl"
KILL = MEDIA / "KILL"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def record(self, status, sent):
        h = self.headers
        entry = {
            "t": round(time.time(), 3),
            "method": self.command,
            "url": self.path,
            "status": status,
            "bytes": sent,
            "ip": h.get("CF-Connecting-IP") or h.get("X-Forwarded-For") or self.client_address[0],
            "ua": h.get("User-Agent"),
            "range": h.get("Range"),
            "accept": h.get("Accept"),
            "ip_country": h.get("CF-IPCountry"),
            "headers": {k: v for k, v in h.items() if k.lower().startswith(("x-fb", "x-meta", "if-"))},
        }
        with LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")
        print(f"{time.strftime('%H:%M:%S')} {self.command} {self.path} -> {status} {sent}B {entry['ua']} range={entry['range']}", flush=True)

    def reply(self, status, body=b"", headers=None, head=False):
        self.send_response(status)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if not head:
            self.wfile.write(body)
        self.record(status, 0 if head else len(body))

    def handle_any(self, head):
        path = urlsplit(self.path).path
        if path == "/robots.txt":
            # ROBOTS=allow|disallow-empty|404 picks the variant, to see what rupload's fetcher accepts.
            mode = os.environ.get("ROBOTS", "allow")
            if mode == "404":
                return self.reply(404, b"", head=head)
            body = b"User-agent: *\nAllow: /\n" if mode == "allow" else b"User-agent: *\nDisallow:\n"
            return self.reply(200, body, {"Content-Type": "text/plain"}, head)
        parts = path.strip("/").split("/")
        if len(parts) != 3:
            return self.reply(404, b"", head=head)
        route, test, name = parts
        if route in ("r301", "r302"):
            return self.reply(int(route[1:]), b"", {"Location": f"/m/{test}/{name}"}, head)
        file = MEDIA / name
        if route not in ("m", "noct", "octet") or not file.is_file() or KILL.exists():
            return self.reply(404, b"", head=head)
        data = file.read_bytes()
        headers = {"Accept-Ranges": "bytes"}
        if route == "m":
            headers["Content-Type"] = mimetypes.guess_type(name)[0]
        elif route == "octet":
            headers["Content-Type"] = "application/octet-stream"
        status, body = 200, data
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            start_s, end_s = rng[6:].split(",")[0].split("-")
            start = int(start_s) if start_s else len(data) - int(end_s)
            end = int(end_s) if start_s and end_s else len(data) - 1
            end = min(end, len(data) - 1)
            status, body = 206, data[start : end + 1]
            headers["Content-Range"] = f"bytes {start}-{end}/{len(data)}"
        self.reply(status, body, headers, head)

    def do_GET(self):
        self.handle_any(head=False)

    def do_HEAD(self):
        self.handle_any(head=True)


if __name__ == "__main__":
    print(f"serving {MEDIA} on 127.0.0.1:8770, logging to {LOG}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8770), Handler).serve_forever()
