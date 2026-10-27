# Instagram API surface, permissions and the Instagram Login gap

Resolves issue #2. Researched 2026-10-27 against developers.facebook.com only (Instagram Platform docs, Graph API docs, permissions reference, Instagram Platform changelog). Docs cite Graph API `v26.0`. Where pages conflict or say nothing, section 7 says so; nothing below is inferred from third parties.

## 1. The three setups, not two

Meta's overview documents three setups ([overview](https://developers.facebook.com/docs/instagram-platform/overview)):

| | Instagram API with Facebook Login | Instagram API with Instagram Login | Instagram API with Unified Login |
|---|---|---|---|
| Login flow | Facebook Login for Business | Business Login for Instagram | Facebook Login for Business (Instagram or Facebook credentials) |
| Facebook Page | Required; user must be able to perform admin-equivalent tasks on it | Not required | Not required |
| Business portfolio | Depends on the Facebook Login for Business configuration | Not required | Required |
| Token | Facebook User or Page access token | Instagram User access token | Business Integration System User access token |
| Host | `graph.facebook.com` | `graph.instagram.com` | `graph.facebook.com` |
| Permission family | `instagram_*` plus Page permissions | `instagram_business_*` | `instagram_*` |
| App ID used at auth | Meta app ID | Instagram app ID (from "API setup with Instagram login") | Meta app ID |

Meta positions Unified Login as the recommended choice for new integrations and Facebook Login for "existing Page-linked integrations" ([overview](https://developers.facebook.com/docs/instagram-platform/overview)). The App Review page states "Your app can either use Facebook Login or Instagram Login but not both" ([app-review](https://developers.facebook.com/docs/instagram-platform/app-review)). The "with Instagram Login" product page says this setup "does not require a Facebook Page" and "cannot access ads or tagging" ([instagram-api-with-instagram-login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login)).

## 2. Development-mode baseline (what a bring-your-own app can do)

- An app in Development mode "can only request permissions from role users, and only permissions with standard or advanced access levels"; features likewise are active only for role users ([app-modes](https://developers.facebook.com/docs/development/build-and-test/app-modes)).
- Standard Access "is the default access level for all apps"; Advanced Access "requires App Review and Business Verification" ([overview](https://developers.facebook.com/docs/instagram-platform/overview)). Business, Consumer and Gaming apps are automatically approved for standard access to all permissions and features available to their app type; Advanced Access is approved per permission through App Review, and since 2023-02-01 requires a verified business ([access-levels](https://developers.facebook.com/docs/graph-api/overview/access-levels)).
- The Instagram App Review page: for "My app is only for a business I own or manage" with Standard Access, App Review is not required under Instagram Login or Facebook Login ([app-review](https://developers.facebook.com/docs/instagram-platform/app-review)).
- Every Instagram Platform guide repeats the same rule: Standard Access suffices "if your app serves Instagram professional accounts you own or manage and have added to your app in the App Dashboard" (e.g. [comment-moderation](https://developers.facebook.com/docs/instagram-platform/comment-moderation), [insights](https://developers.facebook.com/docs/instagram-platform/insights), [conversations-api](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/conversations-api)).
- App roles: Administrator, Developer, Tester, Analytics User. Apps not linked to a verified business can have up to 50 testers; up to 500 administrators ([app-roles](https://developers.facebook.com/docs/development/build-and-test/app-roles)). A developer may hold a developer/admin role on at most 15 apps not connected to a Meta Verified Business Account ([create-an-instagram-app](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app)).
- Instagram Login path testers: the dashboard adds Instagram accounts for testing; the account "must be public"; accounts are managed under App Roles > Roles or Instagram > API Setup with Instagram login ([create-an-instagram-app](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app)). For messaging, "Your app testers must have a role on your app, grant your app access to all the required permissions, and have a role on the Instagram professional account that owns the app" ([messaging-api](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api)).
- Facebook Login path messaging in Standard Access "can only send messages to people that have a role on the app" ([send-message](https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message)).
- Two features are explicitly gated behind App Review regardless of ownership: Hashtag Search needs the "Instagram Public Content Access" feature plus `instagram_basic` approval ([hashtag-search](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/hashtag-search)); product tagging needs `instagram_shopping_tag_products` and `catalog_management`, and "your app must be associated with a verified business" ([product-tagging](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/product-tagging)). Whether the feature's standard tier is usable by role users is not stated on either page.
- Data created in Development mode (test posts etc.) is visible only to role users until the app goes Live ([app-modes](https://developers.facebook.com/docs/development/build-and-test/app-modes)).

Net: for an app-role user who owns the professional account, every `instagram_*` / `instagram_business_*` permission below is grantable in development mode without App Review or Business Verification. The exceptions are the two App-Review-gated features (hashtag search, product tagging) and partnership/branded-content ads, which also need ad permissions.

## 3. Auth and tokens

**Facebook Login path.** Manual OAuth dialog at `https://www.facebook.com/dialog/oauth` with `display=page`, `extras={"setup":{"channel":"IG_API_ONBOARDING"}}`, `response_type=token`, `scope`; the redirect fragment carries `access_token` (short-lived), `expires_in`, `long_lived_token`, `data_access_expiration_time`. Then `GET /me/accounts?fields=id,name,access_token,instagram_business_account` to find the Page and its Instagram account ([business-login-for-instagram](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-login-for-instagram)). Short-lived User and Page tokens expire "in hours"; a long-lived User token "generally lasts about 60 days" (`GET oauth/access_token?grant_type=fb_exchange_token`, server-side); long-lived Page tokens "do not have an expiration date and only expire or are invalidated under certain conditions" ([get-long-lived](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived)). The Messenger Platform guide adds: a Page token obtained from a short-lived User token lives 1 hour; from a long-lived one it has no expiry ([get-started](https://developers.facebook.com/docs/messenger-platform/instagram/get-started)). The map's system-user escape hatch is the Unified Login token type (Business Integration System User).

**Instagram Login path.** Authorize at `https://www.instagram.com/oauth/authorize`; code valid 1 hour, single use; exchange at `POST https://api.instagram.com/oauth/access_token`; tokens from the business login flow "are short-lived and valid for 1 hour" ([get-started](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started)); long-lived via `GET https://graph.instagram.com/access_token?grant_type=ig_exchange_token`, "valid for 60 days"; refresh via `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token` only if the token is at least 24 hours old, unexpired, and the user granted `instagram_business_basic`; "Tokens that have not been refreshed in 60 days will expire and can no longer be refreshed" ([business-login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login)). The dashboard can also generate a 60-day token for a tester account ([get-started](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started)). OAuth parameters: `force_reauth` added 2025-06-14; `enable_fb_login` re-supported 2026-02-06, default `true` ([changelog](https://developers.facebook.com/docs/instagram-platform/changelog)). App Review notes "Web or mobile Web is the only platform that currently supports Instagram API with Instagram Login" ([app-review](https://developers.facebook.com/docs/instagram-platform/app-review)).

**Scopes.** Facebook Login: `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, `instagram_manage_insights`, `instagram_manage_messages`, `instagram_shopping_tag_products`, `instagram_manage_contents` (delete), `instagram_manage_engagement` (likes), `instagram_manage_upcoming_events`, `instagram_branded_content_*`, plus `pages_show_list`, `pages_read_engagement`, `pages_manage_metadata` (messaging), and `ads_management`/`ads_read`/`business_management` when the user's Page role came through Business Manager ([permissions](https://developers.facebook.com/docs/permissions), endpoint references below). Instagram Login: `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_comments`, `instagram_business_manage_messages`, `instagram_business_manage_insights`; the old `business_*` names were deprecated 2025-01-27 ([instagram-api-with-instagram-login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login), [create-an-instagram-app](https://developers.facebook.com/docs/instagram-platform/create-an-instagram-app)). `instagram_business_manage_insights` is absent from the permissions reference page but present in the dashboard defaults and every insights reference table.

## 4. Endpoint groups

Abbreviations: FBL = Facebook Login path (`graph.facebook.com`, Facebook User token unless noted), IGL = Instagram Login path (`graph.instagram.com`, Instagram User token). "Dev-mode" = usable by an app-role user without App Review, per section 2. FBL permission lists omit the recurring `ads_management`/`ads_read` add-on for Business-Manager-granted Page roles.

### 4.1 Profile

| Item | Detail |
|---|---|
| Endpoints | `GET /{ig-user-id}` and `GET /me` ([ig-user](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user), [me](https://developers.facebook.com/docs/instagram-platform/reference/me)) |
| Fields | `id`, `username`, `name`, `biography`, `website`, `profile_picture_url`, `followers_count`, `follows_count`, `media_count`, `has_profile_pic`, `is_published`, `legacy_instagram_user_id`, `shopping_product_tag_eligibility`, `alt_text`; IGL `/me` also `user_id`, `account_type` (`Business` or `Media_Creator`) ([get-started](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/get-started)) |
| FBL permissions | `instagram_basic`, `pages_read_engagement` |
| IGL permissions | `instagram_business_basic` |
| Dev-mode | Yes, both |
| Constraints | Read-only node. `collaborative_media_search` and `collaborative_media` edges are FBL-only. "Only a few fields will be available for accessing Page-backed Instagram accounts." |

### 4.2 Media and feed

| Item | Detail |
|---|---|
| Endpoints | `GET /{ig-user-id}/media`, `GET /{ig-media-id}`, `GET /{ig-media-id}/children`, `GET /{ig-user-id}/stories`, `GET /{ig-user-id}/live_media`, `POST /{ig-media-id}?comment_enabled=`, `DELETE /{ig-media-id}` ([ig-user/media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media), [ig-media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media), [stories](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/stories), [live_media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/live_media)) |
| Media fields | `id`, `caption`, `media_type` (`IMAGE`/`VIDEO`/`CAROUSEL_ALBUM`), `media_product_type` (`AD`/`FEED`/`STORY`/`REELS`), `media_url`, `permalink`, `thumbnail_url`, `timestamp`, `username`, `like_count`, `comments_count`, `is_comment_enabled`, `owner`, `shortcode`, `is_shared_to_feed`, `alt_text`, `view_count` (business discovery only), `legacy_instagram_media_id`, `boost_eligibility_info`, `boost_ads_list`, `copyright_check_information`, `is_ai_generated`, `media_audio_type`, `reposts_count`, `saved_count`, `shares_count`, `total_comments_count`, `total_like_count`, `total_views_count`. The reference marks `caption`, `media_product_type`, `boost_eligibility_info`, `collaborators`, `ordered_comments` as FBL-only. |
| FBL permissions | read: `instagram_basic`, `pages_read_engagement` (media list also accepts `pages_show_list`); update: plus `instagram_manage_comments`; delete: `instagram_basic`, `instagram_manage_contents` |
| IGL permissions | read: `instagram_business_basic`; update: plus `instagram_business_manage_comments`; delete: not available ("Facebook Login only, on graph.facebook.com") |
| Dev-mode | Yes |
| Constraints | `/media` returns at most "10K" most recent media and excludes stories; `since`/`until` time pagination. Stories "are only available for 24 hours", exclude Live and reshared stories. `live_media` returns only broadcasts in progress. `DELETE` covers non-ad posts, stories, reels and whole carousels, not carousel children; added 2025-12-03 ([changelog](https://developers.facebook.com/docs/instagram-platform/changelog)). `media_url` is omitted for video with copyrighted/licensed audio and for reels whose owner disabled downloads; requests still return 200, so treat it as optional (changelog 2026-07-30). Engagement counts (`like_count`, `comments_count`) exclude ad copies; `total_*` fields and `ordered_comments` are FBL-only ([insights](https://developers.facebook.com/docs/instagram-platform/insights)). Owners can hide likes/comments/views, which removes those fields. |

### 4.3 Publishing (images, videos, reels, carousels, stories)

Flow: `POST /{ig-user-id}/media` creates a container, poll `GET /{container-id}?fields=status_code` until `FINISHED`, then `POST /{ig-user-id}/media_publish?creation_id=`; `GET /{ig-user-id}/content_publishing_limit` reports quota ([content-publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing), [ig-container](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-container), [content_publishing_limit](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit)).

| Item | Detail |
|---|---|
| FBL permissions | `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`; user must hold `MANAGE` or `CREATE_CONTENT` on the Page; Page Publishing Authorization and Page 2FA, if required, must be complete ([media_publish](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media_publish)) |
| IGL permissions | `instagram_business_basic`, `instagram_business_content_publish` |
| Dev-mode | Yes, both |
| Media source | "Media must be on a publicly accessible server" (the API cURLs it); URLs should be US-ASCII. Resumable upload (`upload_type=resumable`, `rupload.facebook.com/ig-api-upload/...`, local file or `file_url`) is "available only for apps that have implemented Facebook Login for Business"; it supports `REELS`, `STORIES` and `VIDEO` (carousel items) and only a short parameter list ([resumable-uploads](https://developers.facebook.com/docs/instagram-platform/content-publishing/resumable-uploads)). The IGL "Upload Media" page listed in the index returns 404. |
| Container params | `image_url`/`video_url`, `media_type` (`REELS`, `STORIES`, `CAROUSEL`, `VIDEO` for carousel items), `caption`, `location_id`, `user_tags`, `product_tags`, `collaborators` (up to 3 usernames, not for stories), `cover_url`, `thumb_offset`, `share_to_feed`, `audio_name`, `audio_configuration`, `children`, `is_carousel_item`, `alt_text` (up to 1000 chars, image posts only), `trial_params` (reels only), `is_ai_generated`, `branded_content_sponsor_ids` (max 2) + `is_paid_partnership`, `poll_attachment`, `is_comment_prompt_used`. Branded content, polls and comment prompts are marked FBL-only ([ig-user/media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media)). |
| Caption | max 2200 characters, 30 hashtags, 20 @-tags; not on carousel children |
| Image | JPEG only ("MPO and JPS are not supported"); max 8 MB; aspect ratio 4:5 to 1.91:1; width 320 to 1440 px (scaled otherwise); sRGB |
| Reel | MOV or MP4, moov atom at front, no edit lists; H.264 or HEVC, progressive, closed GOP, 4:2:0; AAC 48 kHz max, 1-2 channels, 128 kbps; 23-60 fps; max width 1920; aspect 0.01:1 to 10:1 (9:16 recommended); VBR max 25 Mbps; 3 s to 15 min; max 300 MB; cover JPEG 8 MB. Reels cannot be carousel items. Published reels report `media_type=VIDEO`, so use `media_product_type`. |
| Story | image: JPEG, 8 MB, 9:16 recommended; video: same codec rules as reels, aspect 0.1:1 to 10:1, 3 to 60 s, max 100 MB. No stickers (link, poll, location); user mentions without a sticker are allowed; no `alt_text`; expires after 24 h. The FBL product page says "Stories are limited to business accounts" ([instagram-api-with-facebook-login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login)). |
| Carousel | `media_type=CAROUSEL` with `children` = comma-separated container IDs; the reference says "up to 20 total images, videos, or a mix"; all images cropped to the first item's aspect ratio (default 1:1); error 2207028 still reads "at least 2 photos/videos and no more than 10" ([error-codes](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/error-codes)). See section 7. |
| Trial reels | `trial_params` with `graduation_strategy` `MANUAL` or `SS_PERFORMANCE`, added 2025-12-03 |
| Containers | expire after 24 h; an account can create 400 containers per rolling 24 h; poll status "once per minute, for no more than 5 minutes"; `status_code` in `EXPIRED`, `ERROR`, `FINISHED`, `IN_PROGRESS`, `PUBLISHED`; `copyright_check_status` on video |
| Publish quota | enforced on `media_publish`; carousels count as one post; `content_publishing_limit` returns `quota_usage` and `config{quota_total, quota_duration}`, with `quota_total` "currently 50" and `quota_duration` 86400 s; error code 9 / subcode 2207042 when exhausted. The guide states both "100 API-published posts within a 24-hour moving period" and "50 published posts within a 24-hour period". See section 7. |
| Partial success | `media_publish` may return `config_issue` (`CAPTION_NOT_ATTACHED`, `USER_TAGGING_FAILURE`) or `caption_add_on_attachment_status`; the media ID is valid |
| Not supported | filters; shopping tags via the generic publish guide (see 4.9); hashtags on stories |

### 4.4 Comments and replies

| Item | Detail |
|---|---|
| Endpoints | `GET/POST /{ig-media-id}/comments`, `GET /{ig-media-id}/ordered_comments` (FBL-only), `GET /{ig-comment-id}`, `GET/POST /{ig-comment-id}/replies`, `POST /{ig-comment-id}?hide=`, `DELETE /{ig-comment-id}`, `POST /{ig-media-id}?comment_enabled=` ([comment-moderation](https://developers.facebook.com/docs/instagram-platform/comment-moderation), [ig-media/comments](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media/comments), [ig-comment](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-comment), [replies](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-comment/replies)) |
| Comment fields | `id`, `text`, `timestamp`, `from{id,username}`, `username`, `user` (only if app user authored it), `hidden`, `like_count`, `parent_id`, `media{id,media_product_type}`, `replies`, `legacy_instagram_comment_id` |
| FBL permissions | `instagram_basic`, `instagram_manage_comments`, `pages_read_engagement` (replies reference also lists `pages_show_list`); `ordered_comments` accepts `instagram_basic` or `ads_management`/`ads_read`/`pages_manage_metadata` |
| IGL permissions | `instagram_business_basic`, `instagram_business_manage_comments` |
| Dev-mode | Yes, both |
| Constraints | `/comments` returns top-level comments only, reverse chronological, max 50 per query, no timestamp filter; replies nest via field expansion. "You can only reply to top-level comments; replies to a reply will be added to the top-level comment." No replies to hidden comments or live-video comments. Hide needs the media owner's token; owner's own comments stay visible. Deletion: the reference says the token must come from the comment's creator in one place and "the owner of the object upon which the comment was made" in another. Comments on age-gated media and from restricted users are not returned. Boosted posts return comments from the post and its ad copy. The guide recommends webhooks "to prevent rate limiting"; no numeric comment-rate limit is published. |

### 4.5 Mentions and tags

| Item | Detail |
|---|---|
| Endpoints | `GET /{ig-user-id}?fields=mentioned_comment.comment_id(ID){...}`, `GET /{ig-user-id}?fields=mentioned_media.media_id(ID){...}`, `POST /{ig-user-id}/mentions` (`media_id`, optional `comment_id`, `message`), `GET /{ig-user-id}/tags` ([mentioned_comment](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/mentioned_comment), [mentioned_media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/mentioned_media), [mentions](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/mentions), [tags](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/tags)) |
| FBL permissions | `instagram_basic`, `instagram_manage_comments`, `pages_read_engagement` (+ `pages_show_list` for comment replies); tasks `MANAGE`, `CREATE_CONTENT` or `MODERATE` |
| IGL permissions | `instagram_business_basic`, `instagram_business_manage_comments`; the IGL guide documents `GET /tags` and `POST /mentions` and does not list `mentioned_comment`/`mentioned_media` ([IGL mentions](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/mentions), [FBL mentions](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/mentions)) |
| Dev-mode | Yes |
| Constraints | The documented workflow is webhook-driven: IDs come from `mentions` webhook payloads; there is no list endpoint for mentions, only lookups by ID. `tags` is a plain list with `media_type`, `posted_after`, `posted_before` filters (filters "rolling out gradually"); private media excluded. "Mentions on Stories are not supported"; "Commenting on photos in which you were tagged is not supported"; no webhooks for mentions on private accounts' media; `mentioned_comment` errors if comments are disabled on that media. Comments discovered via mentions cannot be read through the plain comment node. |

### 4.6 Hashtag search

| Item | Detail |
|---|---|
| Endpoints | `GET /ig_hashtag_search?user_id=&q=`, `GET /{ig-hashtag-id}`, `GET /{ig-hashtag-id}/top_media`, `GET /{ig-hashtag-id}/recent_media`, `GET /{ig-user-id}/recently_searched_hashtags` ([hashtag-search](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/hashtag-search), [ig-hashtag-search](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-hashtag-search)) |
| Permissions | `instagram_basic` plus the **Instagram Public Content Access** feature; "App Review is required". Token from a Facebook User approved for tasks on the connected Page. |
| Paths | FBL and Unified Login only; not IGL ([overview](https://developers.facebook.com/docs/instagram-platform/overview)) |
| Dev-mode | Not stated; the feature is listed as requiring App Review. Treat as unavailable until proven otherwise. |
| Constraints | 30 unique hashtags per rolling 7 days per account (reading `top_media`/`recent_media` counts; repeats within the window do not); no emoji; no story hashtags; sensitive hashtags return a generic error; cannot comment on discovered media; `media_url` may be omitted; Platform rate limiting, not BUC. |

### 4.7 Business discovery

| Item | Detail |
|---|---|
| Endpoint | `GET /{ig-user-id}?fields=business_discovery.username(NAME){followers_count,media_count,media{...}}` ([business_discovery](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery), [guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery)) |
| Permissions | `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement` (Facebook User token) |
| Paths | "Available for the Instagram API with Facebook Login" and Unified Login. Not listed among IGL's supported features, though the overview's "not supported by Instagram Login" list omits it. See section 7. |
| Dev-mode | Yes on FBL (no App Review mention on the page) |
| Constraints | Public fields of other professional accounts; age-gated accounts not returned; returned media cannot be fetched directly ("will fail due to insufficient permissions"); `view_count` includes paid and organic; cursor paging without `next`/`previous`; Platform rate limiting. |

### 4.8 Insights

| Item | Detail |
|---|---|
| Endpoints | `GET /{ig-user-id}/insights`, `GET /{ig-media-id}/insights` ([user insights](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/insights), [media insights](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media/insights), [insights guide](https://developers.facebook.com/docs/instagram-platform/insights)) |
| FBL permissions | `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement` |
| IGL permissions | `instagram_business_basic`, `instagram_business_manage_insights`; media and user insights available since 2025-01-21 ([changelog](https://developers.facebook.com/docs/instagram-platform/changelog)) |
| Dev-mode | Yes, both |
| Account metrics | `accounts_engaged`, `comments`, `engaged_audience_demographics`, `follower_demographics`, `follows_and_unfollows`, `likes`, `profile_links_taps`, `reach`, `replies`, `reposts`, `saves`, `shares`, `total_interactions`, `views`; `follower_count`, `online_followers` referenced in limitations. `period=day` except demographics (`lifetime` + `timeframe` in `this_month`, `this_week`; the `last_*`/`prev_month` values dropped from v20.0). `metric_type=total_value` or `time_series`. Breakdowns: `contact_button_type`, `follow_type` (`FOLLOWER`, `NON_FOLLOWER`, `UNKNOWN`), `media_product_type` (`AD`, `STORY`, `REEL`, `CAROUSEL_CONTAINER`, `POST`), `age`, `city`, `country`, `gender`. |
| Media metrics | FEED: `comments`, `facebook_views`, `follows`, `likes`, `profile_activity`, `profile_visits`, `reach`, `reposts`, `saved`, `shares`, `total_interactions`, `views` (+ `total_comments`, `total_likes`, `total_views` FBL-only). REELS: adds `crossposted_views`, `ig_reels_avg_watch_time`, `ig_reels_video_view_total_time`, `reels_skip_rate`. STORY: `facebook_views`, `follows`, `link_clicks` (FBL-only, 2026-06-22), `navigation`, `profile_activity`, `profile_visits`, `reach`, `replies`, `reposts`, `shares`, `total_interactions`, `views`. Breakdowns `action_type` (profile_activity) and `story_navigation_action_type` (navigation). |
| Deprecated | `impressions` (v22.0; all versions 2025-04-21; media created after 2024-07-02), `plays`, `clips_replays_count`, `ig_reels_aggregated_all_plays_count` replaced by `views` (2025-01-21); `video_views` removed v21.0 (2024-10-02); `profile_views`, `website_clicks`, `email_contacts`, `get_direction_clicks`, `phone_call_clicks`, `text_message_clicks` removed (2024-10-02); `audience_*` removed 2023-09-12 |
| Constraints | Some metrics need 100+ followers (`follower_count`, `online_followers`, `follows_and_unfollows`, `follower_demographics`); `online_followers` last 30 days only; demographics return top 45 values; data delayed up to 48 h; empty set, not 0, when unavailable; default lookback 24 h. Media: no insights for album children; story metrics live 24 h and error (code 10) under 5 viewers; story `replies` is 0 for EU/Japan viewers; media data "stored for up to 2 years" (media page) vs "User Metrics data is stored for up to 90 days" (guide). Insights webhooks and `story_insights` are FBL-only. |

### 4.9 Product tagging (shopping)

| Item | Detail |
|---|---|
| Endpoints | `GET /{ig-user-id}?fields=shopping_product_tag_eligibility`, `GET /{ig-user-id}/available_catalogs`, `GET /{ig-user-id}/catalog_product_search`, `product_tags` on `POST /media`, `GET/POST /{ig-media-id}/product_tags`, `GET/POST /{ig-user-id}/product_appeal` ([product-tagging](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/product-tagging)) |
| Permissions | `instagram_shopping_tag_products`, `catalog_management` (both App Review + verified business), plus the publishing set; user needs admin on the Business Manager owning the Shop |
| Paths | FBL and Unified only; IGL "cannot access ads or tagging" |
| Dev-mode | The page says App Review and a verified business are required; standard-tier use by role users is not stated. Out of reach for the stated user model. |
| Constraints | Approved Instagram Shop with a catalog; creator accounts, stories and Live unsupported; 25 tagged posts per 24 h; up to 20 tags per image/video, 20 per carousel (5 per slide), 30 per reel; no delete endpoint documented. |

### 4.10 Messaging (pull-style: conversations, read, reply)

| Item | FBL (Messenger Platform) | IGL |
|---|---|---|
| Host / object | `graph.facebook.com`, `/{page-id}/conversations?platform=instagram`, `/{page-id}/messages`, Page access token ([get-started](https://developers.facebook.com/docs/messenger-platform/instagram/get-started), [send-message](https://developers.facebook.com/docs/messenger-platform/instagram/features/send-message)) | `graph.instagram.com`, `/{ig-id}/conversations?platform=instagram` or `/me/conversations`, `/{ig-id}/messages`, Instagram User token ([conversations-api](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/conversations-api), [messaging-api](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api)) |
| Permissions | `instagram_basic`, `instagram_manage_messages`, `pages_manage_metadata` (granted at login); "instagram_manage_messages in the Page access token" | `instagram_business_basic`, `instagram_business_manage_messages` |
| Account setting | Instagram app: Settings > Messages and story replies > Message controls > Connected Tools > "Allow Access to Messages"; user must hold `MODERATE` on the Page | Not stated on the fetched IGL pages |
| Dev-mode | Standard Access "can only send messages to people that have a role on the app" | Testers need an app role and a role on the professional account that owns the app |
| Reading | `/{conversation-id}?fields=messages`, `/{message-id}?fields=id,created_time,from,to,message`; `user_id=<IGSID>` filter. "only get details about the 20 most recent messages in the conversation"; Requests-folder threads inactive 30 days are not returned; shares include only the media URL (IGL page; the Messenger Platform conversation page returned 404) | same |
| Sending | text/links UTF-8 <= 1000 bytes; up to 10 image attachments (png/jpeg, 8 MB, by URL or `attachment_id`); audio (aac/m4a/wav/mp4), video (mp4/ogg/avi/mov/webm), file (pdf) 25 MB each; `like_heart` sticker; `react`/`unreact`; `MEDIA_SHARE` of own posts; `reply_to{mid}`; generic/button templates, quick replies, persistent menu, sender actions (typing, mark_seen) | same feature list |
| Windows | 24 h standard; up to 7 days after a Click-to-Direct ad; separate 7-day `human_agent` tag window ([overview](https://developers.facebook.com/docs/instagram-platform/overview)) | same |
| Other limits | no group threads; inbox folders unsupported; API-handled threads move to the General folder; messages are not marked Read until the app replies; self-messaging allowed since 2025-11-10 | same |

Instagram Login's launch note says "the Messenger API is no longer used for Instagram messages" on that path ([changelog](https://developers.facebook.com/docs/instagram-platform/changelog) 2024-07-23).

### 4.11 Private replies (comment to DM)

`POST /{ig-id}/messages` with `recipient={"comment_id":...}`, `message={"text":...}`. FBL: `instagram_basic`, `instagram_manage_comments`, `pages_read_engagement`, Page access token; IGL: `instagram_business_basic`, `instagram_business_manage_comments`. One private reply per commenter, within 7 days of the comment (Live: during the broadcast only); follow-ups only after the recipient answers and within 24 h; comment must be on the app user's own post, reel, story, Live or ad ([private-replies](https://developers.facebook.com/docs/instagram-platform/private-replies)). Rate: 750 calls/hour/account for post and reel comments, 100 calls/second for Live ([overview](https://developers.facebook.com/docs/instagram-platform/overview)).

### 4.12 Welcome messages

Two distinct features:

- **Ice Breakers** (conversation starters): `GET/POST/DELETE /{ig-id}/messenger_profile` (IGL, `platform=instagram`, `instagram_business_basic` + `instagram_business_manage_messages`) or `/me/messenger_profile?platform=instagram` with a Page token (FBL). "A maximum of 4 questions"; per-locale `call_to_actions`; default locale required; "not available on desktop" ([IGL ice-breakers](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/ice-breakers), [FBL ice-breakers](https://developers.facebook.com/docs/messenger-platform/instagram/features/ice-breakers)). Dev-mode: yes.
- **Welcome Message Flows** (for Click-to-Instagram-Direct ads): `GET/POST/DELETE /{ig-id}/welcome_message_flows`, IGL, `instagram_business_basic` + `instagram_business_manage_messages`; `eligible_platforms=["instagram"]`, text + text quick replies; a flow used in an ad cannot be changed; without a linked Page it is only usable in Instagram Boost ads ([welcome-message-ads](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/welcome-message-ads)). Ads-adjacent; out of scope for the map.

### 4.13 Content moderation

Covered by 4.4 (hide/unhide, delete, disable comments per media), 4.2 (`DELETE /{ig-media-id}`, FBL-only, `instagram_manage_contents`) and the `comments` / `live_comments` webhook fields. No separate blocking, restricting or keyword-filter endpoints exist in the documented surface.

### 4.14 Other groups found while enumerating

- **Likes**: `POST`/`DELETE /{ig-user-id}/likes`, `instagram_manage_engagement`, since 2026-04-22; stories and private-account content excluded ([changelog](https://developers.facebook.com/docs/instagram-platform/changelog)). Reference page returned 404; path support unknown.
- **Collaboration**: `GET/POST /{ig-user-id}/collaboration_invites` (300 and 50 calls per user per 24 h), `GET /{ig-user-id}/collaborative_media`, `collaborative_media_search`; `instagram_basic`; FBL and Unified only; no stories ([collaboration](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/collaboration)).
- **Audio API**: `GET /ig_audio`, `GET /{ig-audio-id}`, `audio_configuration` on reel containers; `instagram_basic` + `instagram_content_publish`; "not supported on the Instagram API with Instagram Login" ([audio-api](https://developers.facebook.com/docs/instagram-platform/content-publishing/audio-api)).
- **Upcoming events**: `/{ig-user-id}/upcoming_events`, `instagram_manage_upcoming_events`, FBL/Unified, built for reminder ads ([upcoming-events](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/upcoming-events)).
- **Threads linkage**: `connected_threads_user`, `instagram_backed_threads_user` edges on IG User (reference index; not fetched).
- **Creator Marketplace, Copyright Detection, Partnership ads, oEmbed**: present in the index; ads or discovery features, not enumerated here.

## 5. Rate limits

- Most Instagram endpoints use Business Use Case limits per app + app-user pair: "Calls within 24 hours = 4800 * Number of Impressions" over a rolling 24-hour window; Business Discovery and Hashtag Search use Platform rate limits instead ([overview](https://developers.facebook.com/docs/instagram-platform/overview), [rate-limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting)). Platform limits are published only as the app-token formula "Calls within one hour = 200 * Number of Users"; the per-user-token figure is not stated.
- Headers: `X-App-Usage` (platform) and `X-Business-Use-Case-Usage` (BUC: `call_count`, `total_cputime`, `total_time`, `estimated_time_to_regain_access`). Errors: 4 (app), 17 (user), 32 (Page), 613 (custom), 80002 (Instagram BUC) ([rate-limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting)).
- Messaging, per professional account: Conversations API 2 calls/s; Send API 100 calls/s for text, links, reactions, stickers and 10 calls/s for audio or video; Private Replies 750/h (posts, reels) and 100/s (Live) ([overview](https://developers.facebook.com/docs/instagram-platform/overview)).
- Publishing: 50 (or 100, see section 7) posts per 24 h via `media_publish`; 400 containers per 24 h; 25 product-tagged posts per 24 h; hashtag search 30 unique per 7 days; collaboration invites 300 reads / 50 writes per 24 h.
- The Graph API doc does not define a development-mode rate tier for Instagram; only the Marketing API has `development_access`.

## 6. Capability gap: Facebook Login vs Instagram Login

| Capability | Facebook Login | Instagram Login | Source |
|---|---|---|---|
| Facebook Page required | Yes, with admin-equivalent tasks | No | [overview](https://developers.facebook.com/docs/instagram-platform/overview) |
| Business portfolio | Only via Facebook Login for Business config | No | overview |
| Token lifetime | User: hours, long-lived ~60 d; Page: no expiry when derived from a long-lived user token | Short 1 h; long-lived 60 d; refreshable after 24 h; dashboard token 60 d | [get-long-lived](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived), [business-login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login) |
| Headless token | Long-lived Page token / system user (Unified) | None documented beyond the 60-day dashboard token | same |
| Scope family | `instagram_*` + `pages_*` (+ ads perms for BM roles) | `instagram_business_*` (5 scopes) | [permissions](https://developers.facebook.com/docs/permissions) |
| Profile, media list, stories, container publish, comments, replies, hide, disable comments, private replies | Yes | Yes | section 4 |
| Account and media insights | Yes | Yes (since 2025-01-21); `total_*` media metrics, story `link_clicks`, insights webhooks are FBL-only | [media insights](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media/insights) |
| `ordered_comments` | Yes | No | [ig-media/comments](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media/comments) |
| `DELETE /{ig-media-id}` | Yes (`instagram_manage_contents`) | No | [ig-media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-media) |
| Resumable (local-file) video upload | Yes | No; URL only | [resumable-uploads](https://developers.facebook.com/docs/instagram-platform/content-publishing/resumable-uploads) |
| Collaborators on posts, collaboration invites, collaborative media | Yes | No | overview, [collaboration](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/collaboration) |
| Branded content / paid partnership label, polls, comment prompts on publish | Yes | No (marked FBL-only) | [ig-user/media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media) |
| Audio API | Yes | No | [audio-api](https://developers.facebook.com/docs/instagram-platform/content-publishing/audio-api) |
| Hashtag search | Yes (App Review feature) | No | overview |
| Business discovery | Yes | Not documented | section 4.7 |
| Product tagging | Yes (App Review + verified business) | No | overview |
| Mentions | `mentioned_comment`, `mentioned_media`, `tags`, `POST /mentions` | `tags`, `POST /mentions` documented | 4.5 |
| Messaging | Via Messenger Platform, Page token | Native on `graph.instagram.com` | 4.10 |
| Welcome Message Flows | Not documented | Yes | 4.12 |
| Upcoming events | Yes | No | 4.14 |
| Dev-mode tester model | Facebook users with app roles; Page role needed | Instagram accounts added as testers in the dashboard; "must be public" | section 2 |
| Platform restriction | None stated | "Web or mobile Web is the only platform" (App Review page) | [app-review](https://developers.facebook.com/docs/instagram-platform/app-review) |

## 7. Conflicts and silences in the docs

1. **Publish quota: 50 vs 100.** The content-publishing guide says "100 API-published posts within a 24-hour moving period" in its rate-limit section and "50 published posts within a 24-hour period" in its carousel section; `media_publish` and `content_publishing_limit` references say 50 and `quota_total` "currently 50". No changelog entry explains the change. Read `content_publishing_limit` at runtime rather than hard-coding.
2. **Carousel size: 20 vs 2-10.** The `/media` reference and guide say up to 20 children; error 2207028 still states 2-10; no changelog entry.
3. **Comment deletion rights.** The comment reference says the token must be the comment creator's and, in the same page, that only the media owner may delete.
4. **Insights retention.** Media insights: "stored for up to 2 years"; account insights guide: "User Metrics data is stored for up to 90 days".
5. **Business discovery on Instagram Login.** The overview's unsupported list for IGL names hashtag search, product tagging, partnership ads and collaborators only; the IGL product page's supported list omits business discovery and the reference says FBL only.
6. **Stories for creators.** The FBL product page says stories publishing is "limited to business accounts"; the 2019 changelog says creators cannot use publishing at all, which later entries superseded; no entry lifts the stories restriction explicitly.
7. **Silences.** No numeric per-user Platform rate limit; no comment-posting rate limit; no explicit statement whether the two App-Review-gated features (hashtag search, product tagging) work for role users in Standard Access; the IGL "Upload Media", Messenger-Platform Instagram overview/conversation pages and the `likes` reference returned 404 on the research date; IGL pages do not say whether the Instagram-app "Allow access to messages" setting applies.
8. **Permissions reference gaps.** `instagram_business_manage_insights`, `instagram_manage_contents`, `instagram_manage_engagement` and `instagram_manage_upcoming_events` are not on the permissions reference page; they appear only in endpoint references, the dashboard defaults and the changelog.

## 8. Implications for meta-kit (not decisions)

- Both paths cover the whole tier-1 surface (profile, feed, publish, comments, insights, inbox) for an app-role user in development mode. The Facebook Login path additionally gives media delete, ordered comments, resumable local-file upload, collaborators, audio, business discovery, hashtag search and a non-expiring Page token.
- Instagram Login buys freedom from the Page requirement and a simpler scope set, at the cost of those features and of a 60-day token that must be refreshed at least once every 60 days.
- Hashtag search and product tagging are App-Review-gated features; under the bring-your-own-app, no-App-Review model they should be treated as unreachable.
- Local media on the Instagram Login path has no API route other than a public URL; on Facebook Login, `rupload.facebook.com` accepts local files for reels, stories and carousel videos (not single images).
