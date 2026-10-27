# Facebook Pages API surface and permissions

Research for issue #3. Researched 2026-10-27 against developers.facebook.com (Graph API v26.0 reference, Pages API guides, Video API, Messenger Platform, permissions and features references, changelogs). Primary sources only; each claim cites the page that owns it. Where pages conflict or are silent, this says so.

Scope assumption from the map: every user brings their own Meta app in development mode (business type, Facebook Login for Business), so only people with a role on the app or on the business that claimed it can grant permissions. No App Review, no Business Verification.

## 1. What a bring-your-own-app user can reach without App Review

- Development mode: "Apps in Development mode can only request permissions from role users", and only permissions at Standard or Advanced access. Data created by the app "can only be seen by role users". ([App modes](https://developers.facebook.com/docs/development/build-and-test/app-modes))
- Business, Consumer and Gaming apps "are automatically approved for Standard Access on all permissions and features available for their app type"; Standard Access permissions can only be requested by app users who have a role on the app; Advanced Access needs App Review and (since 1 Feb 2023) a verified business. ([Access levels](https://developers.facebook.com/docs/graph-api/overview/access-levels))
- Pages API overview says the same: "In Development Mode, an app can request any Permission from any app User who has a Role on the app"; Business apps have no app modes, and permissions must be Advanced for users without a role on the app or in a claiming Business. ([Pages API overview](https://developers.facebook.com/docs/pages-api/overview))
- Features (not permissions) follow the same rule: for apps not approved in App Review "the feature is only active for app users who have a role on the app" or in a business portfolio that has claimed the app. The stated exceptions are Page Public Content Access and Page Public Metadata Access; the page does not say how those behave unapproved. ([Features reference](https://developers.facebook.com/docs/features-reference))
- App roles: Administrator, Developer, Tester, Analytics User. "Developers can grant the app any permission while it is in development." Testers can test login permissions. Up to 500 admins; most unlinked apps up to 50 testers; apps linked to a verified business up to 500 testers plus analytics users combined. If the app is connected to a business portfolio, roles are managed in Business Manager. ([App roles](https://developers.facebook.com/docs/development/build-and-test/app-roles))
- Messenger: App Review for `pages_messaging` is "Not required if you only send and receive messages for your own Facebook Page"; "Standard Access (default) limits data to users with a Role on your app or Page". ([Messenger Platform overview](https://developers.facebook.com/docs/messenger-platform/overview))

Net: every pages_* permission and `read_insights`, `publish_video`, `business_management` is grantable by app-role users in development mode. The practical limit is who can interact with the Page through the app, not which endpoints exist. Expect public-data features (PPCA, PPMA) to be unavailable: the docs are silent on their unapproved behaviour, and they are not needed for Pages the user manages.

## 2. Tasks (what the token holder must be able to do on the Page)

Page-level tasks gate most endpoints; the token's user must hold the task. ([Pages API overview](https://developers.facebook.com/docs/pages-api/overview))

| Task | Covers |
|---|---|
| MANAGE | assign and manage Page tasks (full admin) |
| CREATE_CONTENT | publish content as the Page |
| MODERATE | respond to and delete comments; with IG connected also IG publishing, DMs |
| MESSAGING | send messages as the Page |
| ADVERTISE | ads and unpublished Page posts |
| ANALYZE | Page Insights |
| MANAGE_LEADS, VIEW_MONETIZATION_INSIGHTS | leads, monetisation |

"A person with Admin access in the UI can perform all tasks on that Page." `GET /{user-id}/accounts` returns each Page's `tasks` list. ([Pages API getting started](https://developers.facebook.com/docs/pages-api/getting-started))

## 3. Endpoint groups

Permission abbreviations: PSL `pages_show_list`, PRE `pages_read_engagement`, PRUC `pages_read_user_content`, PMP `pages_manage_posts`, PME `pages_manage_engagement`, PMM `pages_manage_metadata`, PMsg `pages_messaging`, RI `read_insights`, PV `publish_video`, BM `business_management`. Permission dependencies: PMP needs PRE+PSL; PME needs PRUC+PSL; PRE, PRUC, PMM, PMsg need PSL (PMsg also PMM); RI needs PRE+PSL. ([Permissions reference](https://developers.facebook.com/docs/permissions))

### 3.1 Posts (feed)

| Operation | Endpoint | Permissions | Task | Token |
|---|---|---|---|---|
| List posts | `GET /{page-id}/feed` | PRE, PRUC | CREATE_CONTENT, MANAGE or MODERATE | Page token (user info is absent without it) |
| Create | `POST /{page-id}/feed` | PMP, PRE, PSL | CREATE_CONTENT | Page token |
| Read one | `GET /{post-id}` | PRE and/or PRUC (error 283) | — | Page token |
| Update | `POST /{post-id}` | PMP (guide); reference does not name it | — | Page token |
| Delete | `DELETE /{post-id}` | see conflict below | — | Page token |
| Scheduled list | `GET /{page-id}/scheduled_posts` | PRE/PRUC/PMM/PMA (error 283) | — | Page token, no parameters |

Sources: [Page/feed reference](https://developers.facebook.com/docs/graph-api/reference/page/feed/), [Page Post reference](https://developers.facebook.com/docs/graph-api/reference/page-post/), [Page/scheduled_posts](https://developers.facebook.com/docs/graph-api/reference/page/scheduled_posts/), [Pages API posts guide](https://developers.facebook.com/docs/pages-api/posts).

Constraints:
- `link` or `message` required. Create parameters include `message`, `link`, `published` (default true), `scheduled_publish_time`, `backdated_time`, `child_attachments` (2 to 5 links; up to 10 with `multi_share_optimized`), `call_to_action`, `place`, `tags` (needs `place`), `targeting`, `feed_targeting`, `object_attachment`. Page mentions as `@[page-id]` in `message`. ([Page/feed](https://developers.facebook.com/docs/graph-api/reference/page/feed/))
- Multi-photo post: upload each photo with `published=false` (and `temporary=true` if the post is scheduled), then `POST /feed` with `attached_media[n]={"media_fbid":"<id>"}`. ([Page/photos](https://developers.facebook.com/docs/graph-api/reference/page/photos/))
- Scheduling window conflict: the feed reference says `scheduled_publish_time` must be "between 10 minutes and 75 days" after the request; the Pages API posts guide says "between 10 minutes and 30 days". Treat 30 days as the safe bound and verify live. Accepted formats: UNIX seconds, ISO 8601, or a PHP `strtotime()` string. ([Page/feed](https://developers.facebook.com/docs/graph-api/reference/page/feed/), [posts guide](https://developers.facebook.com/docs/pages-api/posts))
- Unpublished posts: `/feed` returns published and unpublished posts; use `is_published` to distinguish. `GET /feed` `limit` max 100; "about 600 ranked published posts are returned per year"; `/feed` does not return Reels (use `video_reels`). Expired posts are no longer readable. ([Page/feed](https://developers.facebook.com/docs/graph-api/reference/page/feed/), [Page Post](https://developers.facebook.com/docs/graph-api/reference/page-post/))
- Update: "An app can update a post only if that app created it." Once promoted, editing needs access to the ad account. ([posts guide](https://developers.facebook.com/docs/pages-api/posts), [Page/feed](https://developers.facebook.com/docs/graph-api/reference/page/feed/))
- Delete conflict: the Page Post reference says "Only select developers can perform this operation using the API"; the Pages API posts guide documents `DELETE /{post-id}` returning `success: true` with no restriction. Verify against Language Ranch before promising deletes. ([Page Post](https://developers.facebook.com/docs/graph-api/reference/page-post/), [posts guide](https://developers.facebook.com/docs/pages-api/posts))
- Custom link posts (own `picture`/`thumbnail`, `name`, `description`) require the Page to own the linked domain; check `ownership_permissions{can_customize_link_posts}` on the URL node. ([Page/feed](https://developers.facebook.com/docs/graph-api/reference/page/feed/))
- The guide lists `pages_read_user_engagement` as a required permission; no such permission exists in the permissions reference. Read it as `pages_read_user_content`. ([posts guide](https://developers.facebook.com/docs/pages-api/posts), [Permissions](https://developers.facebook.com/docs/permissions))

### 3.2 Photos

`POST /{page-id}/photos` — PRE, PMP, PSL; CREATE_CONTENT; Page token. `GET /{page-id}/photos` — PRE, PSL; MODERATE; `type` = `profile` (default), `tagged`, `uploaded`. ([Page/photos](https://developers.facebook.com/docs/graph-api/reference/page/photos/))

- Source: `url` (public URL) or a multipart file (`source` by convention). Formats JPEG, BMP, PNG, GIF, TIFF; max 4 MB; PNG should stay under 1 MB. Location metadata is stripped.
- Parameters: `caption` (`message`/`name` deprecated), `published`, `scheduled_publish_time` (Pages only, not with `temporary`), `temporary`, `unpublished_content_type` (`SCHEDULED`, `DRAFT`, `PUBLISHED`), `no_story`, `alt_text_custom`, `place`, `targeting`, `feed_targeting`, `backdated_time`.
- Unpublished photos (`published=false`) are kept about 24 hours and then deleted if not used.
- Response: `id` (photo) and `post_id`.

### 3.3 Videos (file upload and Resumable Upload API)

`POST /{page-id}/videos` — PMP, PRE, PSL; CREATE_CONTENT; Page token. Unpublished videos for ads: `pages_manage_ads`, PSL, ADVERTISE. `GET /{page-id}/videos` is marked as not performable on the reference page; video post lists require a Page admin. ([Page/videos](https://developers.facebook.com/docs/graph-api/reference/page/videos/), [Page/feed](https://developers.facebook.com/docs/graph-api/reference/page/feed/))

Upload routes:
1. Resumable Upload API (current documented path). `POST /{app-id}/uploads` with `file_name`, `file_length`, `file_type` (`video/mp4`, `image/jpeg`, `image/jpg`, `image/png`, `application/pdf`) returns `upload:<session-id>`; `POST /upload:<session-id>` with headers `Authorization: OAuth <user-token>` and `file_offset: 0` and the binary body returns handle `h`; `GET /upload:<session-id>` returns `file_offset` to resume. Then `POST /{page-id}/videos` with `fbuploader_video_file_chunk=<h>`, `title`, `description` and a Page token. The upload step is documented with a user access token; the docs do not state session lifetime or a size limit. ([Resumable Upload API](https://developers.facebook.com/docs/graph-api/guides/upload), [Video API publishing](https://developers.facebook.com/docs/video-api/guides/publishing))
2. Legacy parameters still on the reference: `source` (multipart), `file_url`, and chunked `upload_phase` start/transfer/finish with `upload_session_id`, `start_offset`, `video_file_chunk`; `file_url` cannot be combined with `upload_phase`. The Video API overview says `graph-video.facebook.com` "has been deprecated" and all requests go to `graph.facebook.com`. ([Page/videos](https://developers.facebook.com/docs/graph-api/reference/page/videos/), [Video API overview](https://developers.facebook.com/docs/video-api/overview/))

Limits: the Page videos reference gives none. The only official numbers are on the (deprecated) Event videos reference: non-resumable (multipart or URL) "cannot exceed 1 GB in size and 20 minutes"; resumable "up to 1.75GB and 45 minutes"; a long container list (mp4, mov, mkv, avi, ...). Treat as indicative only. ([Event/videos](https://developers.facebook.com/docs/graph-api/reference/event/videos/))

Scheduling: `published` default true; `scheduled_publish_time` "between 10 mins and 6 months"; `unpublished_content_type` `SCHEDULED`, `SCHEDULED_RECURRING`, `DRAFT`, `ADS_POST`; "Non-published videos cannot be backdated". Other parameters: `title`, `description`, `thumb`, `content_category`, `embeddable`, `no_story`, `secret`, `targeting`. ([Page/videos](https://developers.facebook.com/docs/graph-api/reference/page/videos/))

Status: `GET /{video-id}?fields=status` gives `video_status` plus `uploading_phase`, `processing_phase`, `publishing_phase`. ([Reels guide](https://developers.facebook.com/docs/video-api/guides/reels-publishing)) Video node reading needs a Page or User token; `source` is only returned to an admin of the owning Page. ([Video reference](https://developers.facebook.com/docs/graph-api/reference/video/))

`publish_video` conflict: the Pages API guides list it as required for video publishing; the permissions reference scopes it to live video; the Video, Reels and Stories guides do not list it. Request it anyway; it costs nothing for app-role users. ([manage-pages](https://developers.facebook.com/docs/pages-api/manage-pages), [Permissions](https://developers.facebook.com/docs/permissions))

### 3.4 Reels

`POST /{page-id}/video_reels` — PSL, PRE, PMP; CREATE_CONTENT; Page token. ([Reels publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing))

- Three steps: `upload_phase=start` returns `video_id` and `upload_url`; upload to `rupload.facebook.com/video-upload/{video-id}` with `Authorization: OAuth`, `offset`, `file_size` headers and the binary body, or a `file_url` header (host must allow Facebook's external hit user agent; fbcdn URLs rejected); then `upload_phase=finish` with `video_state` `DRAFT`, `SCHEDULED` or `PUBLISHED`, `description`, `title`, `place`, `is_ai_generated`.
- `scheduled_publish_time` must be more than 10 minutes ahead and within 29 days (`video_state=SCHEDULED`).
- Specs: mp4, 9:16, 1080x1920 recommended (min 540x960), 24 to 60 fps, 3 to 90 seconds (60 if also a story), H.264/H.265, AAC 48 kHz stereo 128 kbps+.
- Limits: "Reels API is limited to 30 API-published posts within a 24-hour moving period"; 10 collaborator invitations per Page per 24 hours; Page publishing is public only.
- Read: `GET /{page-id}/video_reels` with `since`/`until`.

### 3.5 Stories

`POST /{page-id}/photo_stories` (`photo_id` of a photo uploaded with `published=false`) and `POST /{page-id}/video_stories` (start, upload via rupload with `file_url` or `offset`+`file_size`, finish; optional `is_ai_generated`). `GET /{page-id}/stories` returns `post_id`, `status` (PUBLISHED or ARCHIVED), `creation_time`, `media_type`, `media_id`, `url`; archived stories appear only if the Page's story archive is on. Permissions PMP, PRE, PSL; CREATE_CONTENT; `business_management` as well when using a business system user. Photos up to 10 MB; video specs as Reels but max 60 seconds. "A photo or video uploaded for a story can not have been used in a previously published post." ([Page Stories API](https://developers.facebook.com/docs/page-stories-api))

### 3.6 Comments and replies

| Operation | Endpoint | Permissions | Task |
|---|---|---|---|
| Read comments / replies | `GET /{object-id}/comments` | same as reading the parent (PRE, PRUC) | MODERATE to receive comment `id`s |
| Create comment or reply | `POST /{object-id}/comments` | PME | MODERATE |
| Edit / hide | `POST /{comment-id}` (`message`, `is_hidden`) | PME (permissions ref) | — |
| Delete | `DELETE /{comment-id}` | PRUC lets the app "delete user comments" (permissions ref) | — |
| Private reply | `POST /{object-id}/private_replies` | reference lists only legacy `read_page_mailboxes` | — |

- Read parameters: `filter` `toplevel` (default) or `stream`; `summary=true` adds `order` and `total_count`; `order` `chronological` or `reverse_chronological`. With a user access token `/comments` returns empty data on Album, Photo, Post and Video nodes. Comment `id` is no longer returned to PPCA apps; the requester must hold MODERATE. ([Object/comments](https://developers.facebook.com/docs/graph-api/reference/v26.0/object/comments))
- Create parameters: `message`, `attachment_id`, `attachment_url`, `attachment_share_url`, or multipart `source`; at least one required. `@[page-id]` mentions require review (Page Mentioning feature). Replies are comments on a comment (`comments` edge of the Comment node); `can_comment` says whether replies are allowed. ([Object/comments](https://developers.facebook.com/docs/graph-api/reference/v26.0/object/comments), [Comment reference](https://developers.facebook.com/docs/graph-api/reference/comment/))
- Comment node fields on the reference: `id`, `can_comment`, `can_reply_privately`, `comment_count`, `is_private`, `like_count`, `parent`, `private_reply_conversation`, `user_likes`; `is_hidden` is update-only and "Only applicable to Page comments". Error 80001 is the Page rate limit. ([Comment reference](https://developers.facebook.com/docs/graph-api/reference/comment/))
- Private replies: one reply per comment or post; allowed "for only a limited time" (usually several months); the page says the feature "was removed after Graph API v3.2" yet still documents v26.0 calls. The Messenger Send API also accepts a post or comment ID as `recipient`, which is the supported route today. Verify live. ([Private replies](https://developers.facebook.com/docs/graph-api/reference/v26.0/object/private_replies), [Send messages](https://developers.facebook.com/docs/messenger-platform/send-messages))
- Blocking commenters: `GET/POST/DELETE /{page-id}/blocked` with `user`, `asid` or `psid`; Page token; error 3801 block limit, 3802 re-block too soon. ([Page/blocked](https://developers.facebook.com/docs/graph-api/reference/page/blocked/))

### 3.7 Reactions and likes

- `GET /{object-id}/reactions` with `type` in NONE, LIKE, LOVE, WOW, HAHA, SORRY, ANGRY (CARE not listed) and `summary` (`total_count`, `viewer_reaction`). Page-management apps need PSL. "A user or Page can only query their own reactions"; other users' reactions are withheld for privacy, so expect counts, not names. Create, update, delete: "not supported". The like count includes "Care". ([Object/reactions](https://developers.facebook.com/docs/graph-api/reference/v26.0/object/reactions))
- `GET /{object-id}/likes` with `summary=true` for an approximate `total_count`; for Page post likes "only aggregated counts are available". `POST /{object-id}/likes` as the Page: PME, CREATE_CONTENT. `DELETE /{object-id}/likes`: PME, MODERATE; a Page can only remove its own like; ratings cannot be liked. ([Object/likes](https://developers.facebook.com/docs/graph-api/reference/v26.0/object/likes))

### 3.8 Page insights and post insights

`GET /{page-id}/insights` and `GET /{post-id}/insights` with `metric` (required; otherwise error 3001), `period` (`day`, `week`, `days_28`, `month`, `lifetime`, `total_over_range`), `since`/`until` or `date_preset`, `breakdown`, `show_description_from_api_doc`. Permissions RI, PRE; task ANALYZE; Page token. ([Insights reference](https://developers.facebook.com/docs/graph-api/reference/insights/), [Post/insights](https://developers.facebook.com/docs/graph-api/reference/post/insights/))

Limits: "Page Insights data is only available on Pages with 100 or more likes"; most metrics update every 24 hours; "Only the last two years of insights data is available"; "Only 90 days of insights can be viewed at one time" with `since`/`until`; demographic metrics need data for 100+ people. ([Insights reference](https://developers.facebook.com/docs/graph-api/reference/insights/))

Deprecations (all versions, invalid-metric error):
- 14 Mar 2024: `page_engaged_users`, `page_consumptions`, `page_content_activity*`, `page_views_*` breakdowns, `page_positive_feedback*`, `post_activity`, `post_activity_unique`, many click and check-in breakdowns.
- 15 Jun 2025: `page_impressions_unique` (use `page_total_media_view_unique`), `post_impressions_unique` (use `post_total_media_view_unique`), all `page_posts_impressions*`, other `*_unique` impression variants.
- 15 Nov 2025: `page_fans` (use `page_follows`), `page_fans_city`/`_country` (use `page_follows_city`/`_country`), `page_fan_adds`, `page_fan_removes`, `page_impressions` (use `page_media_view`), `page_impressions_paid` (use `page_media_view` with `is_from_ads`), `post_impressions` (use `post_media_view`), `post_impressions_paid`/`_fan`/`_organic` (use `post_media_view` with `is_from_ads` / `is_from_followers`), `*_viral`, `*_nonviral`.
- "By June 15, 2026, a number of the Page Insights metrics will be deprecated for all API versions"; the v25.0 changelog says the remaining reach/impression metrics (page, post, video `total_video_impressions*`, story `PAGE_STORY_IMPRESSIONS*`) go when v26.0 ships.
([Deprecated metrics](https://developers.facebook.com/documentation/pages-api/platforminsights/page/deprecated-metrics), [Blog 15 Aug 2025](https://developers.facebook.com/blog/post/2025/08/15/page-insights-api-updates/), [Changelog v25.0](https://developers.facebook.com/docs/graph-api/changelog/version25.0), [Insights reference](https://developers.facebook.com/docs/graph-api/reference/insights/))

Still-listed Page metrics worth building on: `page_media_view` (breakdowns `is_from_ads`, `is_from_followers`), `page_total_media_view_unique`, `page_post_engagements`, `page_follows`, `page_daily_follows`, `page_daily_unfollows_unique`, `page_views_total`, `page_actions_post_reactions_total`, `page_total_actions`, `page_video_views`. Post metrics: `post_media_view`, `post_total_media_view_unique`, `post_clicks`, `post_reactions_by_type_total`, `post_video_views`, `post_activity_by_action_type`. The reference still lists some metrics the deprecation page says are gone (`page_impressions`, `post_impressions`); trust the deprecation page and verify live. ([Insights reference](https://developers.facebook.com/docs/graph-api/reference/insights/), [Deprecated metrics](https://developers.facebook.com/documentation/pages-api/platforminsights/page/deprecated-metrics))

### 3.9 Messenger conversations and sending

Read (pull-style, as the map wants):
- `GET /{page-id}/conversations` — PMM, PRE, PMsg; MESSAGING; Page token; `platform` MESSENGER or INSTAGRAM, `user_id`, `folder` (values undocumented); "Time-based pagination is not available". ([Page/conversations](https://developers.facebook.com/docs/graph-api/reference/page/conversations/))
- Conversation node: `id`, `participants` (`id`, `name`, `email`), `updated_time`, `is_owner`, `messages` edge; POST not supported, use the Send API. ([Conversation](https://developers.facebook.com/docs/graph-api/reference/conversation/))
- Message node: `id`, `created_time`, `from`, `to`, `message`, `attachments`, `shares`, `tags`, `is_unsupported`; PMsg + PMM; MODERATE or MESSAGING; "you can only retrieve data for the last 20 messages in the conversation" (the Conversation page states this under its Instagram limitation; the Message page states it generally). ([Message](https://developers.facebook.com/docs/graph-api/reference/message/), [Conversation](https://developers.facebook.com/docs/graph-api/reference/conversation/))

Send: `POST /{page-id}/messages` (or `/me/messages`) with `recipient` (PSID, user_ref, or a post/comment ID), `messaging_type` (RESPONSE, UPDATE, MESSAGE_TAG), `message` (text or `attachment`; up to 30 images at once). Page token, `pages_messaging`. Standard messaging window: "For most user actions, it lasts 24 hours"; up to 7 days after a Click-to-Messenger ad. Message tags: "Effective April 27th, 2026, all API requests containing the Message Tags CONFIRMED_EVENT_UPDATE, ACCOUNT_UPDATE, and POST_PURCHASE_UPDATE will receive error code 100"; only HUMAN_AGENT remains (7-day window, Human Agent feature, App Review for non-role users). Text length and attachment size limits live on the Send API reference, which did not render for this research. ([Send messages](https://developers.facebook.com/docs/messenger-platform/send-messages), [Features reference](https://developers.facebook.com/docs/features-reference), [Messenger overview](https://developers.facebook.com/docs/messenger-platform/overview))

Setup: the app needs the Messenger use case and a Page linked to it; permissions PMsg, PMM, PSL, PRE, BM via Facebook Login for Business; the token user needs MESSAGING and MODERATE; webhooks are only required for push delivery ("Without them, you would have to poll"). No App Review when messaging only your own Page. ([Messenger overview](https://developers.facebook.com/docs/messenger-platform/overview))

### 3.10 Page profile and settings

- Read: `GET /{page-id}?fields=...` (`about`, `bio`, `location`, `hours`, `emails`, `website`, `phone`, `category_list`, `followers_count`, `instagram_business_account`, ...). Needs MANAGE with a Page token, or a user token plus PPCA. Published Pages: PRE, PRUC, PSL. `instagram_business_account` needs a user token of someone with Page tasks. ([manage-pages](https://developers.facebook.com/docs/pages-api/manage-pages), [Page reference](https://developers.facebook.com/docs/graph-api/reference/page/))
- Update: `POST /{page-id}` with `about`, `description`, `phone`, `emails`, `website`, `hours`, `location`, `category_list`, `is_published`, `cover` (needs EDIT_PROFILE-level access plus BM), and many more; MANAGE; error 283 names PRE/PRUC/PMA/PMM. The reference does not name the exact permission; the permissions reference puts "update Page settings" under PMM. ([Page reference](https://developers.facebook.com/docs/graph-api/reference/page/), [Permissions](https://developers.facebook.com/docs/permissions))
- Profile picture: `GET /{page-id}/picture` (`type`, `width`, `height`, `redirect=0` for JSON); `POST /{page-id}/picture` with `picture` URL or `photo` ID plus crop values; MANAGE, PRE, PSL. ([Page/picture](https://developers.facebook.com/docs/graph-api/reference/page/picture/))
- Settings: `GET /{page-id}/settings` returns `setting`/`value` pairs; `POST /{page-id}/settings` with `option={"USERS_CAN_MESSAGE":"true"}`, one setting per call. Settings include USERS_CAN_POST, USERS_CAN_MESSAGE, USERS_CAN_POST_PHOTOS, USERS_CAN_TAG_PHOTOS, REVIEW_POSTS_BY_OTHER, SHOW_RECENT_POSTS_BY_OTHERS, PROFANITY_FILTER (Off/Medium/Strong), PAGE_MODERATION_BLACKLIST, AGE_RESTRICTIONS, COUNTRY_RESTRICTIONS, IS_PUBLISHED, APPEARS_IN_RELATED_PAGES. Page token; MANAGE. ([Page/settings](https://developers.facebook.com/docs/graph-api/reference/page/settings/), [manage-pages](https://developers.facebook.com/docs/pages-api/manage-pages))
- v26.0: `current_location`, `genre`, `network`, `parking`, `start_info` fields and the `auto_publish_page_info_updates` setting are deprecated for New Pages Experience Pages (all versions about 90 days after v26.0 launch). ([Changelog v26.0](https://developers.facebook.com/docs/graph-api/changelog/version26.0))

### 3.11 Page roles

- `GET /{page-id}/roles` returns User nodes with `tasks` (MANAGE, CREATE_CONTENT, MODERATE, ADVERTISE, ANALYZE) and `is_active`; "This edge only returns people who do not belong to a business". Create, update, delete not supported. MANAGE. ([Page/roles](https://developers.facebook.com/docs/graph-api/reference/page/roles/), [manage-pages](https://developers.facebook.com/docs/pages-api/manage-pages))
- Business users: `GET /{page-id}/assigned_users?business=...`; `POST /{page-id}/assigned_users` with `user` (business or system user ID) and `tasks`; removing via DELETE is "only available to select developers". ([Page reference](https://developers.facebook.com/docs/graph-api/reference/page/))

Net: roles are read-only for a regular app; assignment happens in Business Manager.

### 3.12 Ratings and reviews

`GET /{page-id}/ratings` — PRUC; CREATE_CONTENT, MANAGE or MODERATE; Page token; no parameters; returns Recommendation nodes (`created_time`, `recommendation_type` positive/negative, `review_text`, `reviewer`). Create, update, delete not supported; replying is not documented. Parent Page tokens cannot read child Page ratings. ([Page/ratings](https://developers.facebook.com/docs/graph-api/reference/page/ratings/), [manage-pages](https://developers.facebook.com/docs/pages-api/manage-pages))

Deprecation: "Page recommendations have been deprecated for v22.0 and future versions"; reading returns error 12; ratings webhooks stopped. The v26.0 reference page still describes the edge. Expect it to fail on any current version; verify live before exposing it. ([Changelog v22.0](https://developers.facebook.com/docs/graph-api/changelog/version22.0))

### 3.13 Events

Not available. The Page node reference lists no `events` edge; `/docs/graph-api/reference/page/events/` returns 404; the Event node says "Access to Events on Users and Pages is only available to Facebook Marketing Partners" and create, update, delete are not performable. Since 4 Apr 2018 the Events API requires App Review and most event edges were removed. Leave events out of v1. ([Page reference](https://developers.facebook.com/docs/graph-api/reference/page/), [Event reference](https://developers.facebook.com/docs/graph-api/reference/event/), [Changelog 4 Apr 2018](https://developers.facebook.com/docs/graph-api/changelog/non-versioned-changes/apr-4-2018))

### 3.14 Other edges seen on the Page node

`albums`, `live_videos`, `tagged`, `visitor_posts`, `published_posts`, `posts`, `likes`, `locations`, `subscribed_apps`, `leadgen_forms`, `call_to_actions`, `messenger_profile`, `custom_labels`, `commerce_orders` (sunset for v26.0+, removed everywhere 27 Oct 2026). Live Video API needs PMP, PRUC, PSL plus the Live Video API feature. ([Page reference](https://developers.facebook.com/docs/graph-api/reference/page/), [Features reference](https://developers.facebook.com/docs/features-reference), [Changelog v26.0](https://developers.facebook.com/docs/graph-api/changelog/version26.0))

## 4. User token vs Page access token vs system-user token

| | User access token | Page access token | System user token (Business Manager) |
|---|---|---|---|
| Obtained by | Facebook Login (for Business, user-token config) | `GET /{user-id}/accounts` or `GET /{page-id}?fields=access_token` with a user token | Business settings > System users > Generate token, or `POST /{system-user-id}/access_tokens`; or Login for Business "business integration system user" config |
| Lifetime | short-lived "about one to two hours"; long-lived "about 60 days" via `fb_exchange_token` | "Long-lived Page access token do not have an expiration date" when derived from a long-lived user token; `/accounts` with a short-lived user token yields a short-lived Page token | "never expires" by default, or 60 days with `set_token_expires_in_60_days=true`; BISU tokens from Login for Business "Defaults to never expire" |
| Tied to | the person | "unique to each Page, admin, and app combination" | the business portfolio and the app the business installed |
| Can call Page endpoints | only public-data reads (PPCA/PPMA) and `/accounts`; "Users requesting Page access through permissions must be able to perform the MODERATE task"; `/comments` returns empty data with a user token | yes; "A Page access token is required for fields that may include User information" | yes, directly: Pages BUC rate limit is defined for "Page access token or System User token"; needs `business_management` and the Page assigned to the system user with tasks |
| Extra requirements | none beyond permissions and Page tasks | the user must hold the task the endpoint needs | the app and system user must belong to the same business; Standard Access allows 1 system user + 1 admin system user, Advanced Access 10 + 1 |

Sources: [Access tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens), [Long-lived tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived), [Login for Business](https://developers.facebook.com/docs/facebook-login/facebook-login-for-business), [System user tokens](https://developers.facebook.com/docs/marketing-api/system-users/install-apps-and-generate-tokens), [System users overview](https://developers.facebook.com/docs/marketing-api/system-users/overview), [Page reference](https://developers.facebook.com/docs/graph-api/reference/page/), [Rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting), [manage-pages](https://developers.facebook.com/docs/pages-api/manage-pages).

Notes:
- The page-roles model is "tasks": a user token's holder must hold the task; the derived Page token inherits exactly those tasks. `/accounts` lists them. ([Pages API getting started](https://developers.facebook.com/docs/pages-api/getting-started))
- Facebook Login for Business: "To serve businesses that you do not own or manage, your app must be approved for Advanced Access"; the app "must be a business type app or an app with a use case that supports Facebook Login for Business"; BISU tokens require the client to have a business portfolio and logins only from web surfaces; a login that is partially declined grants nothing. ([Login for Business](https://developers.facebook.com/docs/facebook-login/facebook-login-for-business))
- System-user scopes include every pages_* permission used above (`pages_manage_posts`, `pages_read_engagement`, `pages_read_user_content`, `pages_manage_engagement`, `pages_manage_metadata`, `pages_messaging`, `pages_show_list`, `pages_manage_ads`, `pages_manage_cta`). ([System user tokens](https://developers.facebook.com/docs/marketing-api/system-users/install-apps-and-generate-tokens))
- Page docs never document a `/accounts` step for system users; the rate-limit and manage-pages pages treat the system user token as directly usable on Page endpoints (with `business_management`). If a Page endpoint rejects a system user token, fall back to `GET /{page-id}?fields=access_token` (undocumented for system users; verify live).
- Unused permissions: "If an app doesn't use a permission for 90 days, the app user must regrant it." ([Permissions](https://developers.facebook.com/docs/permissions))

## 5. Rate limits

- Pages with a Page token or system user token (Business Use Case limit): "Calls within 24 hours = 4800 * Number of Engaged Users"; error code 80001; header `X-Business-Use-Case-Usage` with `call_count`, `total_cputime`, `total_time`, `estimated_time_to_regain_access` per Page ID. The page describes the window inconsistently (24 hours vs rolling hour). ([Rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting))
- Pages with a user or app token: platform limits apply. App token: "Calls within one hour = 200 * Number of Users"; user token: per user across apps, number unpublished; header `X-App-Usage`; errors 4 (app), 17 (user), 32 (Page request limit for a user/app key), 613 (custom limit). ([Rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting))
- Messenger: "Calls within 24 hours = 200 * Number of Active Users" (people the business can message); error 80006. ([Rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting))
- Reels: 30 API-published reels per Page per rolling 24 hours; 10 collaborator invites per 24 hours. ([Reels publishing](https://developers.facebook.com/docs/video-api/guides/reels-publishing))
- Insights: no separate limit; subject to the Pages BUC limit and error 80001. ([Insights reference](https://developers.facebook.com/docs/graph-api/reference/insights/))
- Development mode: no separate formula is published for Pages. The Pages API overview says call counts are visible in the App Dashboard. ([Pages API overview](https://developers.facebook.com/docs/pages-api/overview))
- Practical note: for a single-Page bring-your-own app "engaged users" is tiny, so the BUC budget is small; treat 80001 as the limit to surface in `--help` and errors.

## 6. Summary for the map

- Everything a Page admin can do through the Pages API is reachable by an app-role user in development mode; no endpoint group is gated behind App Review for the user's own Page. Public-content features (PPCA, PPMA, Page Mentioning, Human Agent) are the exceptions and are not needed for own-Page work.
- Tier 1 candidates: feed posts (create/list/update, scheduled and unpublished, multi-photo), photos (URL or file, 4 MB), videos (Resumable Upload API handle), reels (3-step rupload, 30/day), stories, comments and replies (read, create, hide, delete), reactions (counts), Page and post insights (post-Nov-2025 metric names), conversations (list, read last 20 messages) and Send API replies within 24 hours, Page details and settings.
- Tier 2 or drop: ratings (deprecated v22.0+, verify), roles (read-only), blocked users, profile picture, Live Video.
- Not available: events (FMP only), reactions as the Page (only likes), creating or removing Page roles, message tags other than HUMAN_AGENT after 27 Apr 2026.
- Open conflicts to verify against Language Ranch: post delete ("select developers" vs guide), scheduling window (30 vs 75 days), private replies (legacy page vs Send API), system user token on Page endpoints, `publish_video` necessity.
