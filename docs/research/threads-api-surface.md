# Threads API: surface, OAuth and token lifecycle

Researched 2026-10-27 against Meta's Threads developer docs. The canonical tree is now `developers.facebook.com/documentation/threads/...` (index: <https://developers.facebook.com/documentation/threads/llms.txt>); most old `/docs/threads/...` subpages return 404, and the few that still resolve carry the same text. Permission definitions come from the Meta permissions reference. Nothing here is from third-party write-ups.

Resolves issue #4. Scope: a bring-your-own-app user with app roles only, no App Review, no Business Verification.

## Basics

- Hosts: `graph.threads.com` or `graph.threads.net`, path version `v1.0`. Both hosts are documented as interchangeable. <https://developers.facebook.com/documentation/threads/overview>
- Every call carries a **Threads user access token** (OAuth 2.0, app-scoped to the app and user pair). <https://developers.facebook.com/documentation/threads/get-started>
- `threads_basic` is required on every endpoint; each feature adds its own scope (table in "Permissions"). <https://developers.facebook.com/documentation/threads/get-started>
- Threads profiles no longer need a linked Instagram account to use the API (since 2025-09-23); `followers_count` and `follower_demographics` were opened to unlinked profiles on 2026-01-30. <https://developers.facebook.com/documentation/threads/changelog>
- The stated allowed use of `threads_basic` is a *business* app showing the user their own posts; consumer-app use is "strictly prohibited". <https://developers.facebook.com/docs/permissions>

## Publishing

Reference: <https://developers.facebook.com/documentation/threads/reference/publishing>. Guides: <https://developers.facebook.com/documentation/threads/posts>, <https://developers.facebook.com/documentation/threads/create-posts>.

### Flow

1. `POST /{threads-user-id}/threads` creates a media container; returns a container `id`.
2. `POST /{threads-user-id}/threads_publish` with `creation_id` publishes it; returns the media `id`.
3. Carousels: create each child with `is_carousel_item=true`, then a `media_type=CAROUSEL` container with `children` (comma-separated container ids), then publish.

Docs recommend waiting ~30 s between create and publish, and polling `GET /{threads-container-id}?fields=status,error_message` once a minute for at most 5 minutes. Status values: `EXPIRED` (not published within 24 hours), `ERROR`, `FINISHED`, `IN_PROGRESS`, `PUBLISHED`. Error messages include `FAILED_DOWNLOADING_VIDEO`, `FAILED_PROCESSING_AUDIO`, `FAILED_PROCESSING_VIDEO`, `INVALID_ASPEC_RATIO`, `INVALID_BIT_RATE`, `INVALID_DURATION`, `INVALID_FRAME_RATE`, `INVALID_AUDIO_CHANNELS`, `INVALID_AUDIO_CHANNEL_LAYOUT`, `UNKNOWN`. <https://developers.facebook.com/documentation/threads/troubleshooting>

`auto_publish_text=true` skips step 2 for text posts only. <https://developers.facebook.com/documentation/threads/reference/publishing>

### `POST /{threads-user-id}/threads` parameters

| Parameter | Notes | Source |
|---|---|---|
| `media_type` | required: `TEXT`, `IMAGE`, `VIDEO`, `CAROUSEL` | [publishing ref](https://developers.facebook.com/documentation/threads/reference/publishing) |
| `text` | required for TEXT; max 500 characters, emojis count as UTF-8 bytes | [posts](https://developers.facebook.com/documentation/threads/posts) |
| `image_url` / `video_url` | required for IMAGE / VIDEO; must be on a public server, Threads fetches it | [posts](https://developers.facebook.com/documentation/threads/posts) |
| `is_carousel_item` | boolean, default false | [posts](https://developers.facebook.com/documentation/threads/posts) |
| `children` | CAROUSEL only; 2 to 20 container ids | [posts](https://developers.facebook.com/documentation/threads/posts) |
| `reply_to_id` | makes the post a reply (see Replies) | [create replies](https://developers.facebook.com/documentation/threads/retrieve-and-manage-replies/create-replies) |
| `reply_control` | `everyone`, `accounts_you_follow`, `mentioned_only`, `parent_post_author_only`, `followers_only` | [reply management](https://developers.facebook.com/documentation/threads/reply-management) |
| `enable_reply_approvals` | boolean; replies stay hidden until approved; not on ghost posts | [reply management](https://developers.facebook.com/documentation/threads/reply-management) |
| `quote_post_id` | id of the post to quote; supported media types not stated (example uses IMAGE) | [quote posts](https://developers.facebook.com/documentation/threads/posts/quote-posts) |
| `topic_tag` | 1 to 50 characters; no `.` or `&`; one tag per post. Legacy in-text `#tag` still parsed (first valid tag only; `#1` is not a tag) | [posts](https://developers.facebook.com/documentation/threads/posts) |
| `link_attachment` | TEXT only; public URL; if omitted the first link in `text` becomes the preview card. Max 5 unique links per post; more fail with `THREADS_API__LINK_LIMIT_EXCEEDED` (since 2025-12-22) | [posts](https://developers.facebook.com/documentation/threads/posts) |
| `gif_attachment` | `{gif_id, provider}`; TEXT only; GIPHY is the only provider | [posts](https://developers.facebook.com/documentation/threads/posts) |
| `poll_attachment` | `{option_a, option_b[, option_c, option_d]}`; 2 to 4 options, 1 to 25 characters each; text-only posts; no duration parameter documented | [polls](https://developers.facebook.com/documentation/threads/create-posts/polls) |
| `alt_text` | image/video/carousel only, not text posts; max 1,000 characters. How to set it per carousel child is not documented | [accessibility](https://developers.facebook.com/documentation/threads/posts/accessibility), [publishing ref](https://developers.facebook.com/documentation/threads/reference/publishing) |
| `location_id` | from `GET /location_search`; needs `threads_location_tagging` | [location tagging](https://developers.facebook.com/documentation/threads/create-posts/location-tagging) |
| `allowlisted_country_codes` | ISO 3166-1 alpha-2 list; geo-gates the post. Only if `GET /me?fields=is_eligible_for_geo_gating` is true, else `THREADS_API__FEATURE_NOT_AVAILABLE` | [geo-gating](https://developers.facebook.com/documentation/threads/posts/geo-gating) |
| `text_entities` | list of `{entity_type: SPOILER, offset, length}`; max 10 per post | [spoilers](https://developers.facebook.com/documentation/threads/create-posts/spoilers) |
| `is_spoiler_media` | boolean; IMAGE/VIDEO/CAROUSEL; on a carousel marks all children | [spoilers](https://developers.facebook.com/documentation/threads/create-posts/spoilers) |
| `text_attachment` | `{plaintext (max 10,000 chars), link_attachment_url?, text_with_styling_info?}`; text-only posts; not with a poll; styles bold/italic/highlight/underline/strikethrough, non-overlapping ranges | [text attachments](https://developers.facebook.com/documentation/threads/create-posts/text-attachments) |
| `is_ghost_post` | text-only post auto-archived after 24 hours; cannot be a reply; only spoilers supported on it | [ghost posts](https://developers.facebook.com/documentation/threads/create-posts/ghost-posts) |
| `crossreshare_to_ig`, `crossreshare_to_ig_dark_mode` | share as an Instagram Story on the linked IG account; needs `threads_share_to_instagram`; response carries `crossreshare_to_ig_status` `SUCCESS`/`FAILED`; the Threads post still publishes if the share fails | [share to IG stories](https://developers.facebook.com/documentation/threads/create-posts/share-to-ig-stories) |
| `auto_publish_text` | TEXT only; publishes on container creation | [publishing ref](https://developers.facebook.com/documentation/threads/reference/publishing) |

Reposts are a separate call: `POST /{threads-media-id}/repost` returns a repost id; the repost shows as `media_type=REPOST_FACADE` with `reposted_post`. No undo endpoint is documented. <https://developers.facebook.com/documentation/threads/posts/reposts>

### Media requirements

All media is pulled from a URL; there is no upload endpoint. "The media must be hosted on a publicly accessible server at the time of the attempt." <https://developers.facebook.com/documentation/threads/get-started>

Images: JPEG or PNG; max 8 MB; aspect ratio up to 10:1; width 320 to 1440 px (scaled); sRGB. Video: MOV or MP4, moov atom at front, no edit lists; H.264 or HEVC, progressive, closed GOP, 4:2:0; 23 to 60 fps; max width 1920 px; aspect 0.01:1 to 10:1 (9:16 recommended); VBR up to 100 Mbps; AAC 48 kHz, mono or stereo, 128 kbps; duration up to 300 s; max 1 GB. <https://developers.facebook.com/documentation/threads/overview>

### Publishing quotas

Per profile, rolling 24 h: 250 posts (a carousel counts as one), 1,000 replies, 100 deletes, 500 location searches. Read usage with `GET /{threads-user-id}/threads_publishing_limit?fields=quota_usage,config,reply_quota_usage,reply_config,delete_quota_usage,delete_config,location_search_quota_usage,location_search_config`; each config has `quota_total` and `quota_duration` (86400). Docs say to enforce the post limit client-side for scheduled posts. <https://developers.facebook.com/documentation/threads/overview>, <https://developers.facebook.com/documentation/threads/troubleshooting>

## Reading

Reference: <https://developers.facebook.com/documentation/threads/reference/media-retrieval>, <https://developers.facebook.com/documentation/threads/reference/user>.

- `GET /{threads-user-id}/threads`: the app-scoped user's own posts. `since`/`until` (Unix or `strtotime()` string, `since >= 1688540400`), `limit` default 25 max 100, cursors `before`/`after` (mutually exclusive). Only the authenticated user's posts can be listed. <https://developers.facebook.com/documentation/threads/reference/user>
- `GET /{threads-media-id}`: one post. Without advanced access only posts by the app's Threads testers are retrievable. <https://developers.facebook.com/documentation/threads/retrieve-and-discover-posts/retrieve-posts>
- Fields: `id`, `media_product_type` (`THREADS`), `media_type`, `media_url`, `permalink`, `owner` (own top-level posts only), `username`, `text`, `topic_tag`, `timestamp` (ISO 8601), `shortcode`, `thumbnail_url` (video), `children` (carousel), `is_quote_post`, `quoted_post`, `reposted_post`, `alt_text`, `link_attachment_url`, `gif_url`, `poll_attachment` (`option_*`, `option_*_votes_percentage`, `total_votes`, `expiration_timestamp`), `is_spoiler_media`, `text_entities`, `text_attachment`, `location_id`, `location`, `allowlisted_country_codes`, `ghost_post_status` (`ACTIVE`/`ARCHIVED`), `ghost_post_expiration_timestamp`, `is_verified`, `profile_picture_url`, `has_replies`, `is_reply`, `is_reply_owned_by_me`, `root_post`, `replied_to`, `hide_status`, `reply_audience`. `permalink` is omitted for copyright-flagged media. <https://developers.facebook.com/documentation/threads/retrieve-and-discover-posts/retrieve-posts>, <https://developers.facebook.com/documentation/threads/reference/media-retrieval>
- `media_type` values: `TEXT_POST`, `IMAGE`, `VIDEO`, `CAROUSEL_ALBUM`, `AUDIO`, `REPOST_FACADE`. GIF and poll posts return `TEXT_POST`. <https://developers.facebook.com/documentation/threads/retrieve-and-discover-posts/retrieve-posts>
- `GET /{threads-user-id}/ghost_posts`: the user's ghost posts, same paging as `/threads`. <https://developers.facebook.com/documentation/threads/reference/user>
- `GET /{threads-user-id}/mentions` (`threads_manage_mentions`): public posts tagging the user; `since`/`until`/`limit`/cursors as above. Without advanced access only mentions made by the app's testers are returned; private authors are never returned. <https://developers.facebook.com/documentation/threads/threads-mentions>
- `GET /keyword_search` (`threads_keyword_search`): `q`, `search_type` `TOP`/`RECENT`, `search_mode` `KEYWORD`/`TAG`, `media_type` `TEXT`/`IMAGE`/`VIDEO`, `since`/`until`, `limit` default 25 max 100, `author_username`. Without approval it searches only the authenticated user's own posts. 2,200 queries per user per rolling 24 h across all apps; empty results do not count. `GET /me?fields=recently_searched_keywords` lists recent queries. <https://developers.facebook.com/documentation/threads/keyword-search>
- `GET /profile_lookup?username=` and `GET /profile_posts?username=` (`threads_profile_discovery`): public profiles with at least 100 followers; 1,000 requests per user per rolling 24 h. With standard access only `@meta`, `@threads`, `@instagram`, `@facebook` can be looked up. Lookup fields: `username`, `name`, `profile_picture_url`, `biography`, `follower_count`, `likes_count`, `quotes_count`, `reposts_count`, `views_count`, `is_verified` (counts cover the last 7 days). <https://developers.facebook.com/documentation/threads/threads-profiles>, <https://developers.facebook.com/documentation/threads/retrieve-and-discover-posts/retrieve-posts>

## Replies

Reference: <https://developers.facebook.com/documentation/threads/reference/reply-management>. Guides: <https://developers.facebook.com/documentation/threads/retrieve-and-manage-replies/replies-and-conversations>, <https://developers.facebook.com/documentation/threads/retrieve-and-manage-replies/create-replies>, <https://developers.facebook.com/documentation/threads/reply-management>.

- `GET /{threads-media-id}/replies`: top-level replies only. `GET /{threads-media-id}/conversation`: flattened list at any depth, intended for root posts. Both take `reverse` (default `true`, reverse chronological) and `before`/`after`. `has_replies` on a reply signals deeper levels. No `limit` is documented on these two. Scopes: `threads_read_replies` for GETs. <https://developers.facebook.com/documentation/threads/retrieve-and-manage-replies/replies-and-conversations>, <https://developers.facebook.com/documentation/threads/get-started>
- `GET /{threads-user-id}/replies`: replies the user wrote; paging as `/threads`. <https://developers.facebook.com/documentation/threads/retrieve-and-manage-replies/retrieve-replies>
- Reply-only fields: `root_post`, `replied_to`, `is_reply_owned_by_me`, `hide_status` (`NOT_HUSHED`, `UNHUSHED`, `HIDDEN`, `COVERED`, `BLOCKED`, `RESTRICTED`), `reply_audience` (`EVERYONE`, `ACCOUNTS_YOU_FOLLOW`, `MENTIONED_ONLY`, `PARENT_POST_AUTHOR_ONLY`, `FOLLOWERS_ONLY`; only on posts and replies you own). `username`/`permalink` resolve only for public users and yourself. <https://developers.facebook.com/documentation/threads/retrieve-and-manage-replies/replies-and-conversations>
- Create a reply: `POST /{threads-user-id}/threads` with `reply_to_id` (supported media types not stated), then publish. Scopes: `threads_content_publish` plus `threads_manage_replies`. You must own the root post, or hold `threads_keyword_search` / `threads_manage_mentions` to reply to others' public posts. <https://developers.facebook.com/documentation/threads/retrieve-and-manage-replies/create-replies>
- Hide/unhide: `POST /{threads-reply-id}/manage_reply` with `hide=true|false` (`threads_manage_replies`). Hiding a top-level reply hides its nested replies; nested replies cannot be targeted alone. <https://developers.facebook.com/documentation/threads/reply-management>
- Reply approvals (added 2026-02-13): `GET /{threads-media-id}/pending_replies` (`approval_status` `pending`/`ignored`, field `reply_approval_status`), `POST /{threads-reply-id}/manage_pending_reply` with `approve=true|false`; ignored replies can be approved later. <https://developers.facebook.com/documentation/threads/reply-management>, <https://developers.facebook.com/documentation/threads/changelog>

## Insights

Reference: <https://developers.facebook.com/documentation/threads/reference/insights>. Guide: <https://developers.facebook.com/documentation/threads/insights>. Scope: `threads_manage_insights`.

- `GET /{threads-media-id}/insights?metric=` with `views`, `likes`, `replies`, `reposts`, `quotes`, `shares`. `replies` on a root post counts all replies, on a reply only direct ones. `REPOST_FACADE` media return an empty array. `views` and `shares` are marked "in development".
- `GET /{threads-user-id}/threads_insights?metric=` with `views` (daily time series), `likes`, `replies` (top-level only), `reposts`, `quotes` (totals), `clicks` (per link: `link_total_values` with `link_url`), `followers_count`, `follower_demographics` (one `breakdown`: `country`, `city`, `age`, `gender`; needs at least 100 followers). `since`/`until` go together; default is yesterday through today; not supported by `followers_count` or `follower_demographics`. Earliest accepted timestamp is `1712991600` (2024-04-13); user insights not guaranteed before 2024-06-01.

## Profile

`GET /me` or `GET /{threads-user-id}?fields=id,username,name,threads_profile_picture_url,threads_biography,is_verified,is_eligible_for_geo_gating,recently_searched_keywords`. Only the app-scoped user's own profile. <https://developers.facebook.com/documentation/threads/threads-profiles>, <https://developers.facebook.com/documentation/threads/reference/user>

## Delete

`DELETE /{threads-media-id}` (`threads_delete`): own posts only; 100 per day per account; returns `{success, deleted_id}`. Added 2025-03-06. <https://developers.facebook.com/documentation/threads/posts/delete-posts>

## Locations

`GET /location_search` with `query` or `latitude`+`longitude` (the guide calls the parameter `q`, the reference `query`), fields `id,name,address,city,country,latitude,longitude,postal_code`; not paginated; 500 per 24 h. Without `threads_location_tagging` approval it only searches "Menlo Park". `GET /{location-id}` returns the same fields. <https://developers.facebook.com/documentation/threads/create-posts/location-tagging>, <https://developers.facebook.com/documentation/threads/reference/location-search>

## Rate limits

Per app-user pair, rolling 24 h: calls = 4800 × impressions (minimum impressions 10, so at least 48,000 calls); CPU `total_cputime` = 720000 × impressions; `total_time` = 2880000 × impressions. Plus the publishing quotas above. <https://developers.facebook.com/documentation/threads/overview>

## Not in the API

No polls duration setting, no scheduled publishing, no undo-repost, no editing, no likes, no follows, no DMs, no media upload. Webhooks (replies, mentions, publish, delete) exist but require Live mode (or Advanced Access for tech providers), so a development-mode app receives none. <https://developers.facebook.com/documentation/threads/webhooks>

## Access model

### App and use case

- The Threads API needs a Meta app with the **Access Threads API** use case. Such an app receives *two* app ids and secrets; Threads calls use the "Threads app ID" and "Threads app secret" shown under the use case's Settings. <https://developers.facebook.com/documentation/threads/get-started>, <https://developers.facebook.com/documentation/development/create-an-app/threads-use-case>
- Use cases can be combined when compatible; the docs' own example is adding "Access Threads API" to an app with "Manage everything on your Page". Facebook Login (consumer) is incompatible with that combination. Use cases can be added to an existing app but never removed. <https://developers.facebook.com/documentation/development/create-an-app>
- Settings to fill: Client OAuth redirect URIs, Deauthorize callback URL, Data Deletion Requests URL. <https://developers.facebook.com/documentation/development/create-an-app/threads-use-case>
- The use case lists `threads_basic` (required) and optional `threads_content_publish`, `threads_delete`, `threads_keyword_search`, `threads_location_tagging`, `threads_manage_insights`, `threads_manage_mentions`, `threads_manage_replies`, `threads_profile_discovery`, `threads_read_replies`. `threads_share_to_instagram` is in the permissions reference but not in that list. <https://developers.facebook.com/documentation/development/create-an-app/threads-use-case>, <https://developers.facebook.com/docs/permissions>

### Permissions

| Scope | Grants | Source |
|---|---|---|
| `threads_basic` | profile and own posts; required everywhere | [get started](https://developers.facebook.com/documentation/threads/get-started) |
| `threads_content_publish` | publishing, reposts, quotes, replies (with manage_replies) | [create posts](https://developers.facebook.com/documentation/threads/create-posts) |
| `threads_read_replies` | GET replies/conversation | [get started](https://developers.facebook.com/documentation/threads/get-started) |
| `threads_manage_replies` | create replies, hide/unhide, reply_control, approvals | [permissions](https://developers.facebook.com/docs/permissions) |
| `threads_manage_insights` | media and user insights | [insights](https://developers.facebook.com/documentation/threads/insights) |
| `threads_delete` | DELETE posts | [delete](https://developers.facebook.com/documentation/threads/posts/delete-posts) |
| `threads_keyword_search` | keyword/tag search, reply to results | [keyword search](https://developers.facebook.com/documentation/threads/keyword-search) |
| `threads_manage_mentions` | mentions, reply to them | [mentions](https://developers.facebook.com/documentation/threads/threads-mentions) |
| `threads_location_tagging` | location search and tagging | [location tagging](https://developers.facebook.com/documentation/threads/create-posts/location-tagging) |
| `threads_profile_discovery` | profile_lookup, profile_posts | [profiles](https://developers.facebook.com/documentation/threads/threads-profiles) |
| `threads_share_to_instagram` | crossreshare_to_ig | [share to IG](https://developers.facebook.com/documentation/threads/create-posts/share-to-ig-stories) |

Every Threads permission depends on `threads_basic` and is "strictly prohibited" in consumer apps. App Review screencasts must "demonstrate the complete Threads OAuth login process", confirming Threads has its own login, not Facebook Login. <https://developers.facebook.com/docs/permissions>

### Development mode and testers

- An app in Development mode can only request permissions from people with a role on the app; new apps start there. <https://developers.facebook.com/docs/development/build-and-test/app-modes>
- For Threads the role is **Threads Tester**: App Dashboard > App roles > Roles > Add People > Threads Tester (the use case page offers "Add or Remove Threads Test Users"). The invitee must accept under **Website permissions** at <https://www.threads.com/settings/account> after signing in on web or mobile. Until accepted, token generation fails. <https://developers.facebook.com/documentation/threads/get-started>, <https://developers.facebook.com/documentation/development/create-an-app/threads-use-case>
- Testers can grant permissions at any time; non-role users only after App Review approves each permission and the app is published. Without advanced access, publishing, reading posts, mentions, search and discovery are limited to the app's testers (or, for search/discovery, to own posts and four Meta accounts). <https://developers.facebook.com/documentation/threads/get-started>, <https://developers.facebook.com/documentation/threads/retrieve-and-discover-posts/retrieve-posts>
- The Graph API Explorer can generate Threads tokens for testing. <https://developers.facebook.com/documentation/threads/create-posts>

### OAuth endpoints

Source: <https://developers.facebook.com/documentation/threads/get-started/get-access-tokens-and-permissions>.

- Authorization window: `https://threads.com/oauth/authorize?client_id=<THREADS_APP_ID>&redirect_uri=<URI>&response_type=code&scope=<comma or space separated>&state=<optional>`. On Android open it in a webview or browser, not the native app.
- Redirect carries `?code=...` with `#_` appended, which must be stripped. The code is valid for 1 hour and single-use. Denial returns `error=access_denied&error_reason=user_denied`.
- `redirect_uri` must exactly match one of the valid OAuth redirect URIs in the app settings (the dashboard may add a trailing slash) and must be repeated in the exchange. Whether `http://localhost` is allowed is not stated.
- Code exchange: `POST https://graph.threads.com/oauth/access_token` with `client_id`, `client_secret`, `code`, `grant_type=authorization_code`, `redirect_uri`; returns `access_token` (short-lived), `token_type` (`bearer`, since 2026-08-12) and `user_id` (the Threads user id).

### Token lifecycle

Source: <https://developers.facebook.com/documentation/threads/get-started/long-lived-tokens>.

- Short-lived token: 1 hour. Exchange: `GET https://graph.threads.com/access_token?grant_type=th_exchange_token&client_secret=<SECRET>&access_token=<SHORT>` while unexpired; an expired short-lived token cannot be exchanged.
- Long-lived token: 60 days. Refresh: `GET https://graph.threads.com/refresh_access_token?grant_type=th_refresh_token&access_token=<LONG>`; allowed only if the token is at least 24 hours old, unexpired, and `threads_basic` was granted. A refreshed token lasts 60 days from the refresh; an expired one cannot be refreshed. Both responses return `access_token`, `token_type`, `expires_in` (seconds, ~5,183,944).
- Permission grants: 90 days, extended by refreshing. The Get Started page says private-profile grants cannot be extended; the long-lived-tokens page says "long-lived tokens for private Threads profiles can now be refreshed". The newer statement is likely current, but the docs conflict. <https://developers.facebook.com/documentation/threads/get-started>
- Exchange and refresh need the app secret, so Meta says to run them server-side only. For a local CLI holding the user's own secret this is moot but worth a note in the user-facing docs.
- `GET /debug_token?input_token=<T>&access_token=<tester user token or app token>` returns `type`, `application`, `data_access_expires_at`, `expires_at`, `is_valid`, `issued_at`, `scopes`, `user_id`; both tokens must belong to the same app. App access tokens come from `GET https://graph.threads.com/oauth/access_token?client_id=&client_secret=&grant_type=client_credentials` and look like `TH|<APP_ID>|<APP_SECRET>`; they work for oEmbed and debug, not for user data. <https://developers.facebook.com/documentation/threads/troubleshooting/debug-access-token>, <https://developers.facebook.com/documentation/threads/get-started/app-access-tokens>

### Can a Facebook Login or system-user token act on Threads?

No, as far as the docs go. Every Threads endpoint is documented against a "Threads Graph API user access token" obtained from the Threads authorization window on `threads.com`, exchanged at `graph.threads.com`, scoped with `threads_*` permissions that the permissions reference ties to "the complete Threads OAuth login process". No Threads page mentions Facebook Login, Facebook Login for Business, Business Login for Instagram, Business Manager system users or Page tokens, and the Threads hosts are separate from `graph.facebook.com`. The one Threads permission requestable through Facebook Login, `threads_business_basic`, only returns the Threads account id linked to a Business-Portfolio Instagram account for creating Threads *ads* via the Marketing API; it grants no Threads API access. <https://developers.facebook.com/documentation/threads/get-started>, <https://developers.facebook.com/docs/permissions>, <https://developers.facebook.com/documentation/threads/changelog>

Consequence for meta-kit: the Threads login is a third, independent OAuth flow with its own client id/secret pair (even inside the same Meta app), its own token store and its own 60-day refresh schedule. The headless "paste a system-user token" route does not exist for Threads; the closest substitute is pasting a long-lived Threads user token obtained elsewhere (for example from the Graph API Explorer).

## Open points

- Whether `http://localhost:<port>` redirect URIs are accepted for Threads OAuth is undocumented; the ytk-style loopback flow needs a live check against the Language Ranch app.
- Alt text per carousel child is undocumented.
- The private-profile refresh rule is contradictory between two pages (see Token lifecycle).
- `limit` on `/replies` and `/conversation` is not documented; `/threads`, `/replies` (user), `/mentions`, `/profile_posts` and `/keyword_search` cap at 100.
