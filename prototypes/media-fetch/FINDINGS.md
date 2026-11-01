# Prototype: how Meta fetches media URLs during publishing

PROTOTYPE, throwaway branch `prototype/media-fetch`, never merged. Resolves [issue #23](https://github.com/eukosh/social-kit/issues/23).

Run 2026-10-31 against Graph API v26.0 and Threads v1.0, app `social-kit`, assets `language_ranch` (Instagram, Threads) and the Language Ranch Page, all with the stored Page and Threads tokens. Media came from `server.py` on the laptop, exposed through a Cloudflare Quick Tunnel (`cloudflared tunnel --url`), which logs every request. `probe.py` made the calls. 28 Instagram containers, 9 Threads containers, 5 unpublished Page photos, 1 unpublished Page video, 3 Page reel sessions (1 finished as a draft), and 4 public writes, the publishes at least 15 minutes apart.

A re-check on 2026-11-01, after a second-opinion review, added a cache check and 2 more public writes (a video on Instagram and on Threads, published with the tunnel shut down). Results from it are marked **(re-check)**.

## Answers

1. **An ephemeral tunnel works.** Instagram, Threads and Page uploads all fetched from a `trycloudflare.com` host. No 403s, 429s or timeouts on the URL fetchers.
2. **Meta fetches once, during the create call.** Every container's fetch reached the server as exactly one GET (two with a redirect), done before the create call returned (images) or within seconds of it (video). No HEAD, no `Range`, no robots.txt read, no request at status polls or at publish. **(re-check)** Quick Tunnels don't cache: `cf-cache-status` was `DYNAMIC` on repeated GETs of `.jpg` and `.mp4`, both with and without `Cache-Control: no-store`, and every repeat reached the origin. So the server log saw every fetch; no repeat was answered by Cloudflare's edge. `server.py` now sends `no-store` anyway.
3. **The URL only has to live until the container is FINISHED** (Instagram, Threads) or the upload call returns (Pages). Shown four times, once per platform and media type:
   - Instagram image: a container made 70 minutes earlier published after its tunnel hostname had stopped resolving.
   - Threads image carousel: published 14 minutes after creation, with the server answering 404.
   - **(re-check)** Instagram 5 MB reel: FINISHED 23 s after create, tunnel shut down (Cloudflare answered 530), published a minute later. Publish took 20 s.
   - **(re-check)** Threads 5 MB video: FINISHED 27 s after create, tunnel shut down, published 14 minutes later.

   None of the publishes sent a request to the host. Stories and Instagram carousels were not published against a dead host; they create containers the same way, so the same is expected but not shown. Create to FINISHED: images 1 to 10 s, 5 MB videos 20 to 30 s, a 76 MB, 60 s video 56 s.
4. **A bucket is not required.** It remains a valid user choice: presigned-style query strings and 301/302 redirects work everywhere.
5. **Content-Type and format don't matter to the fetcher.** No `Content-Type` and `application/octet-stream` were accepted at container creation on every platform. PNG was accepted for Instagram feed images (the docs say JPEG only), Threads and Pages. None of these variants was published, so "accepted" means the container reached FINISHED.
6. **Instagram's resumable bytes upload (`rupload`) suits small files.** 5 MB and 25 MB files went through and were FINISHED right after the upload returned; duration didn't matter (40 s at 5 MB passed). 50 MB and 76 MB failed with `ProcessingFailedError` "Request processing failed". The upload call takes 20 to 25 s even when it works, so it looks like synchronous processing with a deadline: the limit is likely time-bound (connection speed plus processing), not a fixed size cap, and was only measured on this laptop's home connection. A chunked attempt (8 MB pieces by `offset`) also failed, but Meta doesn't document chunking for this endpoint, so that run proves nothing. The same 76 MB file went through `video_url` without trouble.
7. **`file_url` on `rupload` is blocked behind a Quick Tunnel.** Cloudflare injects its managed robots.txt in front of the origin's, with `Disallow: /` for `meta-externalfetcher` and `meta-externalagent`. The `rupload` fetcher reads robots.txt (UA `facebookexternalhit`, `Range: bytes=0-512000`) and refuses: `FileUrlProcessingError` "403 Restricted by robots.txt", on Instagram and on Page reels alike. The origin's own robots.txt can't override it. The `image_url` / `video_url` / Page `url` / `file_url` on `/videos` fetchers never read robots.txt. That's a risk worth naming: if Meta starts honouring it there too, Quick Tunnels stop working. A named tunnel on the user's own Cloudflare account (where the managed robots.txt is a zone setting) or another tunnel provider probably avoids it; not tested.
8. **Pages:** `/photos` with `url` (UA `facebookplatform/1.0`) and `/videos` with `file_url` (UA `facebookexternalua`, ready 17 s later, unpublished) both work. `publish_video` isn't on the app and an unpublished `/videos` upload doesn't need it; publishing a `/videos` upload wasn't tried. Page reels take bytes on `rupload` (start, upload 2.7 s, finish as `DRAFT`, ready 17 s later). The Wikimedia PNG refusal (code 324) didn't reproduce from our host, so it was host-specific.
9. **The unpublished-Page-photo trick works** (its `fbcdn` URL gave a FINISHED Instagram container), but it stays undocumented and stays out.

## Fetch profile

| | Instagram | Threads | Page photo | Page video |
|---|---|---|---|---|
| User agent | `facebookexternalhit/1.1` | `facebookexternalhit/1.1` | `facebookplatform/1.0` | `facebookexternalua` |
| Seen from | Meta IPv6, `2a03:2880::/32` | same | same | same |
| Requests per file | 1 GET (+1 per redirect) | same | same | same |
| HEAD, `Range`, robots.txt | none | none | none | none |
| When | during the create call | during the create call | during the upload call | during the upload call |
| Create to FINISHED | image 1 to 10 s, video 20 to 56 s | image 1 to 10 s, video 27 s | 2 s | 17 s |
| Redirects, query string, no or wrong Content-Type | accepted | accepted | accepted | not tried |

`rupload` with `file_url` is the only fetcher that reads robots.txt. The source range is two days' sample, not something to build an allowlist on.

## Public writes

- **Instagram image post** ([`DfKCCzzl0eo`](https://www.instagram.com/p/DfKCCzzl0eo/)): published from the very first container, 70 minutes old, after its tunnel hostname had died and with the server answering 404. Publish took 3.5 s and sent no request to the host.
- **Threads carousel** ([`DfKJeG5DpmT`](https://www.threads.com/@language_ranch/post/DfKJeG5DpmT)): two image children, each created with its own `alt_text`, published 14 minutes later with the media answering 404. No request reached the host. **Per-child alt text works**: the published post returns each child's `alt_text` under `children{alt_text}`. A container doesn't expose `alt_text` before publish (code 100 "nonexisting field"), and the carousel post itself has none.
- **Page photo story** (post `1414223057586215`): an unpublished `/photos` upload by `url`, then `photo_stories` with its `photo_id`. Took 5 s.
- **Page video story** (post `1116064671321123`): `video_stories` start, bytes on `rupload` (2.8 s), finish, published 22 s later. No URL needed.
- **(re-check) Instagram reel** ([`DfNMgD9oYj4`](https://www.instagram.com/reel/DfNMgD9oYj4/), media `18145073515590770`): see answer 3.
- **(re-check) Threads video** ([`DfNMv5sDC2e`](https://www.threads.com/@language_ranch/post/DfNMv5sDC2e), media `18080126009389462`): see answer 3. At publish the tunnel hostname no longer resolved.

Cleanup: deleting all Instagram and Threads posts worked, including the two re-check posts. Deleting a Page story by its story `post_id` failed with code 100, subcode 33 "Unsupported delete request". That's Meta's catch-all ("does not exist, cannot be loaded due to missing permissions, or does not support this operation"), so it doesn't prove stories can't be deleted by id. The id did come from `GET /{page}/stories`. **(re-check)** A `GET` by that id failed the same way, but the story had expired by then, so it settles nothing; the token holds `pages_read_engagement` and `pages_manage_posts`. Deleting the video behind a video story removes the story. Deleting the photo behind a photo story returned `success: false`, and the story stayed up until it expired. The unpublished photos, the unpublished video, the draft reel and the two abandoned reel sessions were all deleted.

## Not measured

- Stories and Instagram carousels published against a dead host (see answer 3).
- Publishing the PNG, no-Content-Type and octet-stream containers, and publishing a Page `/videos` upload.
- Multi-photo Page posts (`attached_media` with unpublished photos) and `temporary=true` photo uploads for scheduled posts, both asked for on the Pages surface decision.
- Deleting a fresh Page story by its id, with a `GET` first.
- Non-standard ports: every route skit would use (tunnels, buckets) serves on 443.
- A real S3 or R2 presigned URL; the query string was simulated.
- Videos over 76 MB through `video_url`, and where the `rupload` limit sits on other connections.
- `rupload` with an Instagram Login token: we have none.

## Files

- `server.py`: logging media server, with redirect, Content-Type, 404-switch and robots.txt variants. Sends `Cache-Control: no-store`.
- `probe.py`: container and upload calls; writes `results.jsonl`. Never prints tokens.
- `gen-media.sh`: generates the test media, including the 20 s and 40 s cuts and the 40 s low-bitrate file used for `rupload`.
- `batch-*.sh`: the paced runs as they were executed.
