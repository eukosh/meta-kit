# Prototype: how Meta fetches media URLs during publishing

PROTOTYPE, throwaway branch `prototype/media-fetch`, never merged. Resolves [issue #23](https://github.com/eukosh/social-kit/issues/23).

Run 2026-10-31 against Graph API v26.0 and Threads v1.0, app `social-kit`, assets `language_ranch` (Instagram, Threads) and the Language Ranch Page, all with the stored Page and Threads tokens. Media came from `server.py` on the laptop, exposed through a Cloudflare Quick Tunnel (`cloudflared tunnel --url`), which logs every request. `probe.py` made the calls. 28 Instagram containers, 9 Threads containers, 5 unpublished Page photos, 1 unpublished Page video, 3 Page reel sessions (1 finished as a draft), and 4 public writes, the publishes at least 15 minutes apart.

## Answers

1. **An ephemeral tunnel works.** Instagram, Threads and Page uploads all fetched from a `trycloudflare.com` host. No 403s, 429s or timeouts on the URL fetchers.
2. **Meta fetches once, during the create call, and never again.** Every container got exactly one GET (two with a redirect), finished before the create call returned (images) or within seconds of it (video). No HEAD, no `Range`, no robots.txt read, no re-fetch at status polls or at publish.
3. **The URL only has to live until the container is FINISHED** (Instagram, Threads) or the upload call returns (Pages). An Instagram container made 70 minutes earlier published fine after its tunnel hostname had died and the server answered 404. Measured windows: images about 1 to 5 s; a 5 MB reel 20 to 30 s; a 76 MB, 60 s reel 56 s. Cleanup is safe as soon as the status says FINISHED.
4. **A bucket is not required.** It remains a valid user choice: presigned-style query strings and 301/302 redirects work everywhere.
5. **Content-Type and format don't matter to the fetcher.** No `Content-Type` or `application/octet-stream` was accepted on every platform. PNG was accepted for Instagram feed images (the docs say JPEG only), Threads and Pages.
6. **Instagram's resumable bytes upload (`rupload`) is a small-file route only.** It works for reels and stories (5 MB and 25 MB files were FINISHED right after the upload returned), and duration doesn't matter (40 s at 5 MB passed). At 50 MB and 76 MB it fails with `ProcessingFailedError` "Request processing failed", whether sent in one go or in 8 MB chunks. Chunks are acknowledged with `PartialRequestError` (retriable) and the last one hangs about 31 s, then fails. The upload call itself takes about 20 to 25 s, so it looks like synchronous processing with a deadline. The same 76 MB file went through `video_url` without trouble.
7. **`file_url` on `rupload` is blocked behind a Quick Tunnel.** Cloudflare injects its managed robots.txt in front of the origin's, with `Disallow: /` for `meta-externalfetcher` and `meta-externalagent`. The `rupload` fetcher reads robots.txt (UA `facebookexternalhit`, `Range: bytes=0-512000`) and refuses: `FileUrlProcessingError` "403 Restricted by robots.txt", on Instagram and on Page reels alike. The origin's own robots.txt can't override it. The `image_url` / `video_url` / Page `url` / `file_url` on `/videos` fetchers never read robots.txt. That's a risk worth naming: if Meta starts honouring it there too, Quick Tunnels stop working. A named tunnel on the user's own Cloudflare account, or another tunnel, avoids it.
8. **Pages:** `/photos` with `url` (UA `facebookplatform/1.0`) and `/videos` with `file_url` (UA `facebookexternalua`, ready 17 s later, unpublished) both work. `publish_video` isn't needed: it isn't on the app. Page reels take bytes on `rupload` (start, upload 2.7 s, finish as `DRAFT`, ready 17 s later). The Wikimedia PNG refusal (code 324) didn't reproduce from our host, so it was host-specific.
9. **The unpublished-Page-photo trick works** (its `fbcdn` URL gave a FINISHED Instagram container), but it stays undocumented and stays out.

## Fetch profile

| | Instagram | Threads | Page photo | Page video |
|---|---|---|---|---|
| User agent | `facebookexternalhit/1.1` | `facebookexternalhit/1.1` | `facebookplatform/1.0` | `facebookexternalua` |
| Source | Meta IPv6, `2a03:2880::/32` | same | same | same |
| Requests per file | 1 GET (+1 per redirect) | same | same | same |
| HEAD, `Range`, robots.txt | none | none | none | none |
| When | during the create call | during the create call | during the upload call | during the upload call |
| Create to FINISHED | image 3 to 5 s, video 20 to 56 s | image 4 to 10 s, video 28 s | 2 s | 17 s |
| Redirects, query string, no or wrong Content-Type | accepted | accepted | accepted | not tried |

`rupload` with `file_url` is the only fetcher that reads robots.txt.

## Public writes

- **Instagram image post** ([`DfKCCzzl0eo`](https://www.instagram.com/p/DfKCCzzl0eo/)): published from the very first container, 70 minutes old, after its tunnel hostname had died and with the server answering 404. Publish took 3.5 s and sent no request to the host.
- **Threads carousel** ([`DfKJeG5DpmT`](https://www.threads.com/@language_ranch/post/DfKJeG5DpmT)): two image children, each created with its own `alt_text`, published 14 minutes later with the media answering 404. No request reached the host. **Per-child alt text works**: the published post returns each child's `alt_text` under `children{alt_text}`. A container doesn't expose `alt_text` before publish (code 100 "nonexisting field"), and the carousel post itself has none.
- **Page photo story** (post `1414223057586215`): an unpublished `/photos` upload by `url`, then `photo_stories` with its `photo_id`. Took 5 s.
- **Page video story** (post `1116064671321123`): `video_stories` start, bytes on `rupload` (2.8 s), finish, published 22 s later. No URL needed.

## Not measured

- Non-standard ports: every route skit would use (tunnels, buckets) serves on 443.
- A real S3 or R2 presigned URL; the query string was simulated.
- Videos over 76 MB through `video_url`, and the exact `rupload` size ceiling (somewhere between 25 and 50 MB for this bitrate).
- `rupload` with an Instagram Login token: we have none.

## Files

- `server.py`: logging media server, with redirect, Content-Type, 404-switch and robots.txt variants.
- `probe.py`: container and upload calls; writes `results.jsonl`. Never prints tokens.
- `gen-media.sh`: generates the test media.
- `batch-*.sh`: the paced runs as they were executed.
