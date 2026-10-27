# Media ingestion: routes from a local file to something Meta can publish

Researched 2026-10-27 against developers.facebook.com (Graph API v26.0 docs), plus the vendor docs for the third-party routes. Resolves issue #6. Primary sources only; community lore is labelled as such.

## Summary

- Instagram and Threads publishing endpoints take media as a **public URL that Meta fetches** (`image_url`, `video_url`, `cover_url`). The one documented bytes route is Instagram **video** via a resumable upload session on `rupload.facebook.com`; images have no bytes route on either platform.
- Facebook Pages accept **bytes directly**: photos as a multipart file, videos via the Resumable Upload API handle, chunked upload, or a `file_url`. Page Reels take bytes or a `file_url` on `rupload.facebook.com`.
- Meta's docs say nothing about redirects, content types, how many times a URL is fetched, or how long it must stay up. They do state (Page Reels) that **fbcdn URLs are rejected** and that hosts blocking `facebookexternalhit` via `robots.txt` are rejected. The Page-unpublished-photo-as-`image_url` trick is **undocumented for Instagram** and officially rejected for Page video; treat it as unsupported.
- No policy text forbids an S3-compatible bucket, a tunnel, or a user-supplied URL. The docs explicitly allow "a file hosted on a public facing server, such as a CDN".

## What each publishing endpoint accepts

### Instagram (Content Publishing API)

| Media | Endpoint | Input | Source |
|---|---|---|---|
| Image (feed, carousel child, story) | `POST /{ig-user-id}/media` | `image_url` only | [reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Video / Reels (feed, carousel child, story) | `POST /{ig-user-id}/media` | `video_url`, or `upload_type=resumable` then bytes or `file_url` on `rupload.facebook.com` | [guide](https://developers.facebook.com/docs/instagram-platform/content-publishing) |
| Reels cover | same call | `cover_url` | [reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |

- Guide: "We will cURL your image using the passed in URL so it must be on a public server." and, under "Media on a public server": "We cURL media used in publishing attempts, so the media must be hosted on a publicly accessible server at the time of the attempt." ([content-publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing))
- Resumable video upload: `upload_type=resumable` "Create a resumbable upload session to upload large videos from an area with frequent network interruptions or other transmission failures. Only for apps that have implemented Facebook Login for Business." Supported sources: "A file located on your computer" and "A file hosted on a public facing server, such as a CDN". Upload is `POST https://rupload.facebook.com/ig-api-upload/<API_VERSION>/<IG_MEDIA_CONTAINER_ID>` with headers `Authorization: OAuth <token>`, `offset: 0`, `file_size: <bytes>` and a binary body, or the header `file_url: <https url>` instead of a body. Success: `{"success":true,"message":"Upload successful."}`. No file-size limit is stated for this path. ([content-publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing))
- Images: the docs describe resumable sessions only for videos; there is no image bytes route on the `/media` endpoint. ([content-publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing))
- URL characters: the reference "strongly recommended" the HTTP IETF character set; URLs with only US-ASCII are safe, others "can cause the request to fail". ([reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media))
- Containers expire after 24 hours; 400 containers per rolling 24 h; 100 API-published posts per 24 h (the carousel section of the guide still says 50). Poll `status_code` once per minute for at most 5 minutes; video uploads are asynchronous and `FINISHED` confirms success. ([reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media), [content-publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing))

Media specs ([reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media)):

| | Format | Max size | Dimensions / ratio | Duration |
|---|---|---|---|---|
| Feed image | JPEG only, sRGB ("Extended JPEG formats such as MPO and JPS are not supported") | 8 MB | 320–1440 px wide, 4:5 to 1.91:1 | – |
| Reels | MOV/MP4, moov atom first, no edit lists; H.264/HEVC, AAC | 300 MB | ≤1920 px wide, 9:16 recommended | 3 s – 15 min |
| Story image | JPEG, sRGB | 8 MB | 9:16 recommended | – |
| Story video | as Reels | 100 MB | 9:16 recommended | 3–60 s |
| Reels cover | JPEG, sRGB | 8 MB | 9:16 recommended, else centre-cropped | – |
| Carousel | 2–20 children, cropped to the first child's ratio (default 1:1) | | | |

Fetch-related error codes ([error codes](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/error-codes)): `2207003` "It takes too long to download the media." (retry); `2207052` "The media could not be fetched from this uri:" (confirm the URI is valid and publicly accessible); `2207004` image too large (8 MiB); `2207005` unsupported image format; `2207009` aspect ratio; `2207026` "The video format is not supported."; `2207027` "The media is not ready for publishing" (wait for `FINISHED`); `2207020` media expired (new container); `2207053` "unknown upload error" (mostly video, new container).

### Threads

- `POST /{threads-user-id}/threads` with `image_url` ("Threads retrieves your image from the URL provided, so it must be on a public server.") or `video_url` (same wording for video). No binary or resumable upload is documented anywhere in the Threads docs. ([posts](https://developers.facebook.com/docs/threads/posts))
- Recommends waiting about 30 seconds after creating a container before `threads_publish`; poll `GET /{container-id}` once per minute, at most 5 minutes. Containers expire after 24 h. 250 API-published posts per 24 h. ([posts](https://developers.facebook.com/docs/threads/posts), [troubleshooting](https://developers.facebook.com/docs/threads/troubleshooting), [overview](https://developers.facebook.com/docs/threads/overview))
- Specs ([overview](https://developers.facebook.com/docs/threads/overview)): image JPEG or PNG, ≤8 MB, 320–1440 px wide, ratio ≤10:1, sRGB; video MOV/MP4 (moov first, no edit lists), H.264/HEVC, AAC, 23–60 fps, ≤1920 px wide, ≤100 Mbps, ≤300 s, ≤1 GB. Carousel 2–20 children.
- Fetch failures surface as `error_message` on a container in `ERROR` status: `FAILED_DOWNLOADING_VIDEO`, `FAILED_PROCESSING_VIDEO`, `INVALID_DURATION`, `INVALID_ASPEC_RATIO` (sic), etc. No image-download error is listed. ([troubleshooting](https://developers.facebook.com/docs/threads/troubleshooting))

### Facebook Pages

- Photos, `POST /{page-id}/photos`: either `url` ("The URL of a photo that is already uploaded to the Internet. You must specify this or a file attachment.") or a `multipart/form-data` file attachment (field name is free; `source` by convention). Formats JPEG, BMP, PNG, GIF, TIFF; files must not exceed 4 MB; PNG should stay under 1 MB or may look pixelated. Facebook "strips all location metadata before publishing" and "resizes images to different dimensions to best support rendering in multiple sizes." ([page/photos](https://developers.facebook.com/docs/graph-api/reference/page/photos))
- Unpublished photos: `published=false`; "After you upload an unpublished photo, Facebook stores it in a temporary upload state" and "If you do not publish these photos within 24 hours, we delete them." `temporary=true` is required when the photo is used in a scheduled post. ([page/photos](https://developers.facebook.com/docs/graph-api/reference/page/photos))
- Videos, `POST /{page-id}/videos`: `source` (multipart), `file_url` ("Accessible URL of a video file. Cannot be used with `upload_phase`."), chunked `upload_phase` start/transfer/finish with `video_file_chunk`, or the Resumable Upload API handle in `fbuploader_video_file_chunk`. `published=false` plus `unpublished_content_type` (DRAFT, SCHEDULED, ADS_POST, ...) creates an unpublished video. Error 389: "Unable to fetch video file from URL." The `graph-video.facebook.com` host is deprecated in favour of `graph.facebook.com`. ([page/videos](https://developers.facebook.com/docs/graph-api/reference/page/videos), [video publishing](https://developers.facebook.com/docs/video-api/guides/publishing), [video overview](https://developers.facebook.com/docs/video-api/overview))
- Reels, `POST /{page-id}/video_reels` (`upload_phase=start` → `rupload.facebook.com/video-upload/{video_id}` with `offset`, `file_size` and bytes, or a `file_url` header → `upload_phase=finish`, `video_state` PUBLISHED/DRAFT/SCHEDULED). 3–90 s, min 540×960, 9:16. ([reels publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing))

### Resumable Upload API (`/{app-id}/uploads`)

- "The Resumable Upload API allows you to upload large files to Meta's social graph." Start `POST /{app-id}/uploads` with `file_name`, `file_length`, `file_type`; then `POST /upload:{session}` with `file_offset` header, `Authorization: OAuth` header and binary body; returns a handle `h`. Resume via `GET /upload:{session}`. Accepted types: `application/pdf`, `image/jpeg`, `image/jpg`, `image/png`, `video/mp4`. No size limit stated. ([upload guide](https://developers.facebook.com/docs/graph-api/guides/upload))
- The handle is consumed by endpoints whose reference says they accept it; the guide's only example is `/{page-id}/videos`. Neither the Instagram `/media` reference nor the Threads docs list a handle parameter, so **it is not a route into Instagram or Threads**. It yields no URL either. ([upload guide](https://developers.facebook.com/docs/graph-api/guides/upload), [ig-user/media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media))

## What Meta requires of a URL

Stated:
- Publicly reachable at the time of the attempt; Meta fetches it server-side ("cURL"). ([IG guide](https://developers.facebook.com/docs/instagram-platform/content-publishing), [Threads posts](https://developers.facebook.com/docs/threads/posts))
- For Page Reels `file_url`: "Supported protocols are http and https. Other protocols, and urls requiring authentication are not currently supported." "The API will now reject files hosted on sites that restrict access via robots.txt." Hosts must allow the `facebookexternalhit/1.1` user agent. "Files hosted on Meta CDN (e.g.. fbcdn URLs) will get rejected." ([reels publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing))
- Meta's crawler page: block by adding a disallow to `robots.txt`; crawlers may cache `robots.txt` for up to 24 hours; allowlist either the user agent strings or Meta's IP addresses, the latter being "more secure". It does not say which crawler fetches API publishing media. ([web crawlers](https://developers.facebook.com/docs/sharing/webmasters/web-crawlers))
- ASCII-only URLs recommended (Instagram). ([ig-user/media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media))

Not stated anywhere in the docs: whether redirects are followed, required `Content-Type`/`Content-Length`, whether a URL is fetched once or several times, a HEAD request, source IP ranges, or a minimum time the URL must stay up. The only time bound is implicit: a video container stays `IN_PROGRESS` while Meta downloads and processes it, so the URL must stay up at least until the container is `FINISHED`; Threads suggests ~30 s, Instagram suggests polling up to 5 minutes.

## Candidate routes from a local file

### 1. Unpublished Page photo, reuse its CDN URL as Instagram `image_url`

- What the docs support: uploading bytes to `/{page-id}/photos` with `published=false` and reading the Photo node's `images[].source` ("The different stored representations of the photo"). ([page/photos](https://developers.facebook.com/docs/graph-api/reference/page/photos), [photo](https://developers.facebook.com/docs/graph-api/reference/photo/))
- What the docs do not say: that an fbcdn URL may be passed as Instagram `image_url`/`video_url`, that unpublished-photo URLs are publicly fetchable, or how long `images[].source` URLs are valid. The Photo reference says nothing about URL lifetime or reuse.
- What the docs say against it: the Page Reels guide rejects Meta CDN URLs outright for video and points to crossposting instead. ([reels publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing)) No Instagram or Threads page carries the same sentence, but none sanctions the practice either.
- Other costs even if it works: Page limit is 4 MB vs Instagram's 8 MB; Facebook re-encodes and resizes the image, so Instagram would publish a derivative, not the original; needs a linked Page and `pages_manage_posts`, which the "with Instagram Login" path and Threads-only users do not have; the unpublished photo is deleted after 24 h. For video, Page `published=false` videos would again be fbcdn URLs, which the Reels guide rejects.
- Lore (not official): fbcdn URLs carry signature and expiry query parameters and stop working after a few days; third parties report "URL signature expired" on cdninstagram URLs. ([Zapier community](https://community.zapier.com/how-do-i-3/instagram-to-rss-image-url-expires-10513), [iframely](https://iframely.com/help/015914-how-to-deal-with-expiring-images-of-tik-tok-and-instagram)) No official statement found that this route works for Instagram.
- Verdict: undocumented, contradicted by the nearest official text, and lossy. Not a route to build a product on; at most a prototype experiment.

### 2. Resumable Upload API (`/app/uploads`)

Bytes in, handle out; consumed only by endpoints that document handle support (Page videos). Not accepted by Instagram or Threads, and produces no URL. Useful only for Page video. ([upload guide](https://developers.facebook.com/docs/graph-api/guides/upload))

### 3. Instagram resumable video upload (`rupload.facebook.com`)

The only official bytes route into Instagram. Covers video and Reels on `/media` (`upload_type=resumable`); the docs do not say whether `media_type=STORIES` or carousel children accept it. Restricted to apps using Facebook Login for Business. Not available for images. ([content-publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing))

### 4. S3-compatible bucket (S3, Cloudflare R2, etc.), user-provided

- Meta: explicitly allowed form, "A file hosted on a public facing server, such as a CDN". No policy text restricts where media is hosted (see Policy). Must not block `facebookexternalhit` and must not require authentication (per the Reels guide); a presigned URL carries its auth in the query string, which the docs neither allow nor forbid.
- S3 presigned URLs: "time-limited permission to download objects"; max expiry 7 days via CLI/SDK (SigV4), 12 hours from the console. ([AWS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html))
- R2 public access: `r2.dev` "is rate-limited and should only be used for development purposes" and "intended for non-production traffic"; production needs a custom domain. ([Cloudflare R2](https://developers.cloudflare.com/r2/buckets/public-buckets/))
- Cost to the user: an account and credentials for a third-party service; the file is public (or presigned) for the window.

### 5. Ephemeral tunnel from the laptop (e.g. Cloudflare Quick Tunnel)

- Meta: nothing forbids it; it is a public HTTPS server like any other. The local server must answer `facebookexternalhit` and must not serve a restrictive `robots.txt`.
- Cloudflare Quick Tunnels: `cloudflared tunnel --url http://localhost:8080`; "You do not need a Cloudflare account or domain."; "Quick Tunnels have no uptime guarantee."; meant "for testing and development"; up to 200 in-flight requests; a new hostname each run; anyone with the URL can reach the service; the URL dies when `cloudflared` stops. ([Cloudflare](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/))
- Cost: a binary dependency, the laptop must stay up until the container is `FINISHED` (video processing time unknown), and the tunnel's terms are "development" grade.

### 6. URL only (user supplies a public URL)

Always supported, zero infrastructure, and the baseline every other route reduces to. Pages can additionally take the file directly, so for Pages a local path needs no URL at all.

## Policy

- Meta Platform Terms: no clause about media hosting, CDN URL reuse, or caching. Relevant edges: 3.a.viii forbids processing Platform Data "for purposes other than the permitted purposes set forth in the Meta Developer Documentation"; 6.a.iv requires protecting access tokens. ([Platform Terms](https://developers.facebook.com/terms/))
- Developer Policies: 1.6 requires following all instructions in the Developer Documentation (which makes the Reels guide's fbcdn and robots.txt sentences binding where they apply); 6.2 forbids using the Instagram Platform merely to import or save user content without permission. Nothing on hosting media or on automated publishing beyond 1.7 (consent before publishing on someone's behalf). ([Developer Policies](https://developers.facebook.com/devpolicy/))
- Net: routes 3–6 are policy-clean; route 1 relies on undocumented behaviour and, for video, contradicts documented rules.

## Open questions a prototype must answer

1. Fetch behaviour: for one `image_url`, one `video_url` (plain and resumable `file_url`), one carousel and one Threads post, log every request to the host: user agent, source IPs, count, HEAD vs GET, `Range`, whether 301/302 is followed, whether a query string (presigned URL) is accepted, and whether a missing or wrong `Content-Type` fails.
2. Window: time from container creation to the last fetch, and whether anything is re-fetched at `media_publish`. This sets how long a tunnel or presigned URL must live.
3. Route 1 reality check: does `/media` accept an unpublished Page photo's `images[].source`? What does Instagram publish (dimensions, re-encoding)? Does a Page `published=false` video's `source` work as `video_url`, or is it rejected as the Reels guide says?
4. Instagram resumable upload: does it work with an "Instagram Login" token (docs say Facebook Login for Business only), for `STORIES` and carousel children, and up to what size?
5. Tunnel: does `facebookexternalhit` reach a `trycloudflare.com` host without 403/429, and how long does a 100 MB video take to reach `FINISHED`?
6. Threads: same fetch profile as Instagram, or a different crawler?
