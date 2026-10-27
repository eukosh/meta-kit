# Pull-style messaging for Instagram and Messenger (no webhook receiver)

Researched 2026-10-27 against developers.facebook.com only. Ticket: [#7](https://github.com/eukosh/meta-kit/issues/7).

## Short answer

Yes. Listing conversations, reading messages and attachments, and replying are plain Graph API calls that need no webhook subscription. No doc makes a webhook subscription a precondition for the Conversations API or the Send API; webhooks are described as a way to "avoid rate limits that would occur if you were querying the Messenger Platform endpoints to track changes" ([IG webhooks](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/webhooks.md)) and as "avoiding the need to poll the Meta social graph" ([Messenger overview](https://developers.facebook.com/docs/messenger-platform/overview)).

Three things limit a polling tool: only the 20 most recent messages per thread are readable, there is no documented unread/seen signal on a thread, and under Standard Access (development mode) the API only interacts with people who hold a role on the app. The human-agent 7-day window is a reviewed feature.

## Two Instagram paths, one Messenger path

| | Host | Asset node | Permissions | Token |
|---|---|---|---|---|
| Messenger (Page) | `graph.facebook.com` | `/{page-id}` | `pages_messaging`, `pages_manage_metadata`, `pages_read_engagement` (+ `pages_show_list`, `business_management`) | Page access token from a user with the `MESSAGING` or `MODERATE` Page task |
| Instagram via Facebook Login | `graph.facebook.com` | `/{page-id}` of the linked Page, `platform=instagram` | `instagram_basic`, `instagram_manage_messages`, `pages_manage_metadata` (+ `pages_show_list`, `business_management`) | Page access token from a user with the `MESSAGING` task |
| Instagram via Instagram Login | `graph.instagram.com` | `/{ig-id}` or `/me` | `instagram_business_basic`, `instagram_business_manage_messages` | Instagram User access token |

Sources: [Conversations API (Messenger Platform)](https://developers.facebook.com/documentation/business-messaging/messenger-platform/conversations.md), [Page /conversations reference](https://developers.facebook.com/docs/graph-api/reference/page/conversations/), [Conversations API (Instagram Login)](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/conversations-api.md), [Messenger overview](https://developers.facebook.com/documentation/business-messaging/messenger-platform/overview.md). The Messenger overview states `business_management` "is a dependency for `pages_messaging`, `pages_show_list`, and `instagram_manage_messages`". The Facebook Login path is what the map's v1 uses; the Instagram Login path exposes the same conversation shape on a different host and is noted for the "with Instagram Login" ticket.

## Listing and reading by polling

### Endpoints (same shape on both hosts)

- `GET /{page-id}/conversations?platform=instagram|messenger` lists threads: `id`, `updated_time`. Add `user_id=<IGSID or PSID>` to find the thread with one person. `is_owner` (bool) is returned only when Conversation Routing is enabled. "Time-based pagination is not available for the conversations endpoint"; cursor paging via `paging`. ([Conversations API](https://developers.facebook.com/documentation/business-messaging/messenger-platform/conversations.md), [reference](https://developers.facebook.com/docs/graph-api/reference/page/conversations/))
- `GET /{conversation-id}?fields=messages,participants` lists message `id` + `created_time`; `participants` carry `username` for Instagram, `email`/`name` for Pages. ([Conversation reference](https://developers.facebook.com/docs/graph-api/reference/conversation/))
- `GET /{message-id}?fields=id,created_time,from,to,message,attachments,shares,story,reactions,reply_to,tags,is_unsupported`. Defaults are `id` and `created_time`; fields with no data are omitted. ([Message reference](https://developers.facebook.com/docs/graph-api/reference/message/))

### Message fields

`message` (text, empty if none), `attachments` (`id`, `name`, `file_url`, `image_data`/`video_data` with `url`, `preview_url`, `width`, `height`, `render_as_sticker`, `generic_template`), `shares` (`post`, `reel`, `ig_post`, `ig_reel`; sub-fields must be requested explicitly), `story` (mentions and replies, `link` + `id`), `reactions` (`reaction` emoji + `users`), `reply_to` (`mid`, `is_self_reply`), `tags` (Pages: `inbox`, `read`, `source:chat`), `is_unsupported` (only when true). ([Message reference](https://developers.facebook.com/docs/graph-api/reference/message/), [Conversations API](https://developers.facebook.com/documentation/business-messaging/messenger-platform/conversations.md))

### Hard limits on reading

- "You can only get details about the 20 most recent messages in the conversation"; older IDs return a "message was deleted" error. ([Conversations API](https://developers.facebook.com/documentation/business-messaging/messenger-platform/conversations.md), [Conversation reference](https://developers.facebook.com/docs/graph-api/reference/conversation/)) Polling cannot backfill history, and a thread that received more than 20 messages between two polls loses the older ones.
- "Conversations that are within the Requests folder that have not been active for 30 days will not be returned in API calls." (same source)
- Shares: "Only the image or video URL for a share will be included in the data returned". (same source)
- Accounts linked by "private keys, such as an email or phone number" are not retrievable until Advanced Access is granted. (same source)
- Instagram: "Inbox folders are not supported" and "Group messaging is not supported". ([IG overview](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview.md), [IG Login messaging](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/messaging-api.md))
- The Instagram overview lists "Content Delivery Network (CDN) URL handling" as a requirement but states no expiry rule; treat attachment URLs as short-lived and download promptly. ([IG overview](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview.md))

### Unread state

No `unread_count`, seen or delivered field is documented on the current Conversation or Message reference (the v2.0 `Thread` object had `unread`/`unseen`; the current `UnifiedThread` reference page is not published). Read receipts exist only as webhooks (`messaging_seen` for Instagram, `message_reads` for Messenger). Instagram's own inbox does not mark API-read messages as read: "Only after a reply is sent will a message be considered Read" ([IG overview](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview.md)). The Pages `tags` field exposes `read` on a Page message ([Message reference](https://developers.facebook.com/docs/graph-api/reference/message/)). A polling tool can only derive "new since last poll" from `updated_time`/`created_time` and `from.id` not being the own asset.

## Sending by polling (Send API)

`POST /{page-id}/messages` (or `/me/messages`) with `recipient: {id: <PSID|IGSID>}`, `messaging_type` and `message`. Response: `recipient_id`, `message_id`. ([Messenger send](https://developers.facebook.com/documentation/business-messaging/messenger-platform/send-messages), [IG send](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/send-message.md), [Page /messages reference](https://developers.facebook.com/docs/graph-api/reference/page/messages/))

- `messaging_type`: `RESPONSE`, `UPDATE`, `MESSAGE_TAG`, `UTILITY`. `tag` enum: `ACCOUNT_UPDATE`, `CONFIRMED_EVENT_UPDATE`, `CUSTOMER_FEEDBACK`, `HUMAN_AGENT`, `POST_PURCHASE_UPDATE`. "Only `HUMAN_AGENT` is available for Instagram Messaging." `notification_type`: `REGULAR`, `SILENT_PUSH`, `NO_PUSH`. `reply_to: {mid}` replies to a specific message. ([Page /messages reference](https://developers.facebook.com/docs/graph-api/reference/page/messages/))
- `sender_action`: `MARK_SEEN`, `TYPING_ON`, `TYPING_OFF`, `REACT`, `UNREACT` (reference). Instagram's sender-actions page lists `typing_on`, `typing_off`, `mark_seen`; reactions are on the IG send page as `sender_action: react|unreact` with `payload: {message_id, reaction}`. Sender-action requests must contain only `sender_action` and `recipient`. ([IG sender actions](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/sender-actions.md), [IG send](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/send-message.md))
- Instagram content: text (the page says both "1,000 bytes or less" and "less than 1,000 characters"; the docs conflict), image png/jpeg 8 MB (up to ten per message), audio aac/m4a/wav/mp4 25 MB, video mp4/ogg/avi/mov/webm 25 MB, file pdf 25 MB, sticker `like_heart`, `MEDIA_SHARE` of a post the business owns, templates. Media by `url` or by `attachment_id` from the Attachment Upload API. ([IG send](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/send-message.md))
- Messenger content: text, audio, files, GIFs, images, videos, stickers, buttons, templates, menus; attachments by `payload.url` (optionally `is_reusable`) or the Attachment Upload API; up to 30 images in one `attachments` array. The current page gives no numeric text or size limit. ([Messenger send](https://developers.facebook.com/documentation/business-messaging/messenger-platform/send-messages))
- "A person must initiate the conversation." ([Messenger overview](https://developers.facebook.com/documentation/business-messaging/messenger-platform/overview.md)) Recipient IDs must be PSID/IGSID; "User IDs from Facebook Login integrations are app-scoped and will not work". ([Messenger send](https://developers.facebook.com/documentation/business-messaging/messenger-platform/send-messages))
- Private replies open a DM from a comment: `POST /{page-id}/messages` with `recipient: {comment_id}`; one message per commenter, within 7 days of the comment; needs `instagram_manage_comments` + `pages_messaging`, and the IG page lists the Human Agent feature and Advanced Access as requirements. Comment IDs come from the feed/comments endpoints, so no webhook is needed. ([IG private replies](https://developers.facebook.com/docs/messenger-platform/instagram/features/private-replies))
- Moderation: `POST /{page-id}/moderate_conversations` with `user_ids` + `actions` (`block_user`, `unblock_user`, `move_to_spam`), up to 10 IDs and 2 actions per call; needs `instagram_manage_messages`, `instagram_basic`, `business_management`; Advanced Access for people without a role. ([Moderate Conversations](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/moderate-conversations.md))

## The 24-hour window and tags

- "For most user actions, it lasts 24 hours." Opened by the user messaging the Page/account, clicking a CTA, reacting to a message, clicking an m.me/ig.me link with `ref`, or messaging after a Click-to-Messenger/Click-to-Direct ad (then "up to 7 days"). Promotional content is allowed inside the window. ([Policy](https://developers.facebook.com/documentation/business-messaging/messenger-platform/policy.md))
- `RESPONSE` and `UPDATE` must be inside the window; `MESSAGE_TAG` is outside it, non-promotional, and must carry a `tag`. ([Page /messages reference](https://developers.facebook.com/docs/graph-api/reference/page/messages/))
- `HUMAN_AGENT`: "message from a human agent, sendable within 7 days of the customer's last message" (reference); the policy page calls it "a separate 7-day period". Changelog, 2 June 2021: developers must "apply for the Human Agent tag permission via the App dashboard". For Instagram, the own-business App Review guide says to request it only with a custom inbox where agents need more than 24 hours, and to explain why. On the Instagram Login app type, "If you have requested the instagram_business_manage_messages permission, the Human Agent feature is added automatically" to the review submission. The docs do not say whether a Standard Access app can use `HUMAN_AGENT` toward app-role holders before review. ([Messenger changelog](https://developers.facebook.com/docs/messenger-platform/changelog/), [IG App Review, own business](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/app-review/apps-for-your-own-business.md), [Create an Instagram app](https://developers.facebook.com/documentation/development/create-an-app/other-app-types/instagram-apis.md))
- "Effective April 27, 2026" requests with `CONFIRMED_EVENT_UPDATE`, `ACCOUNT_UPDATE`, `POST_PURCHASE_UPDATE` return error 100; Meta points to Utility Templates and the Marketing Messages API instead. ([Messenger send](https://developers.facebook.com/documentation/business-messaging/messenger-platform/send-messages), [changelog](https://developers.facebook.com/docs/messenger-platform/changelog/))
- Not on Instagram: one-time notifications, news messaging, sponsored messages, and "Some message tags are available only for Messenger Platform". ([Policy](https://developers.facebook.com/documentation/business-messaging/messenger-platform/policy.md))
- Responsiveness rules (answer any input within 30 seconds) apply to bots "submitted for approval via the App Dashboard" as automated experiences, not to human-operated inboxes. (same source)

## Permissions, access levels and a development-mode app

- Standard Access "is the default access level for all apps", "intended for apps that will only be used by people who have roles on them"; Advanced Access "requires App Review and Business Verification" and is needed when the app "serves Instagram professional accounts that you don't own or manage". ([Instagram Platform overview](https://developers.facebook.com/docs/instagram-platform/overview/), [Access levels](https://developers.facebook.com/docs/graph-api/overview/access-levels))
- Messenger: Standard Access "limits data to users with a Role on your app or Page"; App Review is "Not required if you only send and receive messages for your own Facebook Page". ([Messenger overview](https://developers.facebook.com/documentation/business-messaging/messenger-platform/overview.md))
- Instagram: "Apps with Standard Access can only interact with people who have a role on the app" and "Apps with Standard Access can only send messages to people that have a role on the app". The Conversations API adds "Advanced Access is required to access conversations between your business and people who do not have a role" on the app, Instagram account, Page or business. ([IG overview](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview.md), [IG send](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/send-message.md), [Conversations API](https://developers.facebook.com/documentation/business-messaging/messenger-platform/conversations.md))
- Consequence for the bring-your-own-app model: a development-mode app can read and answer DMs on the owner's own Page and Instagram account, but the people on the other end must also hold a role on the app (or, for Messenger, on the Page). Strangers are reachable only after App Review grants Advanced Access for `pages_messaging` / `instagram_manage_messages`. Whether the Conversations API hides, errors on, or returns stranger threads under Standard Access is not stated; verify live against Language Ranch.
- Testers on Instagram "must have a role on your app, grant access to all the required permissions" and have a role on the Instagram professional account. ([IG overview](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview.md))
- Conflict to flag: the Instagram Conversations API docs say "Your app must be owned by a verified business" without qualification, while the access-levels page ties Business Verification to Advanced Access and the Instagram-app guide says verification is needed "before you can publish your app". Whether an unverified development-mode app can call `/conversations?platform=instagram` is unclear; verify live. ([Conversations API](https://developers.facebook.com/documentation/business-messaging/messenger-platform/conversations.md), [Access levels](https://developers.facebook.com/docs/graph-api/overview/access-levels), [Create an Instagram app](https://developers.facebook.com/documentation/development/create-an-app/other-app-types/instagram-apis.md))
- Permission descriptions: `instagram_manage_messages` "allows business users to read and respond to Instagram Direct messages" (deps `instagram_basic`, `pages_read_engagement`, `pages_show_list`); `pages_messaging` "allows your app to manage and access Page conversations and calling in Messenger" (deps `pages_manage_metadata`, `pages_show_list`); `instagram_business_manage_messages` "allows an app to access messages on an Instagram professional account" (dep `instagram_business_basic`). App Review is "For apps that needs access to data that you do not own or manage". ([Permissions reference](https://developers.facebook.com/docs/permissions/))
- Page access tokens derived from a long-lived user token "have no expiration date"; from a short-lived one, 1 hour. ([IG get started](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/get-started))
- The Instagram overview lists "The Human Agent feature" and an "escalation path to a human agent" as requirements for apps using the Instagram Messaging APIs. A human-operated CLI is the escalation path by construction, but the feature itself is granted in review. ([IG overview](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview.md))

## Instagram inbox settings that must be on

"Instagram professional accounts will need to enable the connected tools toggle under message controls settings": Instagram Settings > Messages and story replies > Message controls > Connected Tools > "Allow Access to Messages". ([IG get started](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/get-started)) The account must be professional (business or creator) with a linked Facebook Page on the Facebook Login path. A Page can have messaging disabled; the Send API then returns error 10904 "The page has messages disabled in the settings". ([Page /messages reference](https://developers.facebook.com/docs/graph-api/reference/page/messages/))

Inbox behaviour worth telling users: non-follower messages land in Requests and are not marked Seen until accepted; a reply sent through a third-party app moves the thread to General; API reads never mark a thread Read. ([IG overview](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview.md))

## Rate limits

From [Messenger rate limiting](https://developers.facebook.com/documentation/business-messaging/messenger-platform/overview/rate-limiting.md) and [Graph API rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting):

| Call | Messenger (per Page) | Instagram (per professional account) |
|---|---|---|
| Conversations API | 2/s | 2/s |
| Send API: text, links, reactions, stickers | 300/s | 300/s (changelog 8 Oct 2024: up from 100) |
| Send API: audio, video | 10/s | 10/s |
| Private replies | 750/h (post and reel comments) | 100/s live comments; 750/h post and reel comments |
| App-wide Messenger API | 200 x engaged users per rolling 24 h | not stated |

The Graph API page still shows 100/s for Instagram text sends; the Messenger page and changelog are newer. Error codes: 4 (app-level), 17 (user-level), 32 (Pages), 613 (rate limit exceeded), 80006 (Messenger BUC, "Too many Messenger API calls to the Page"), 80002 (Instagram BUC). Headers `X-App-Usage` and `X-Business-Use-Case-Usage` (with `estimated_time_to_regain_access`) report consumption; once the limit is reached, stop calling. The Conversations API at 2 calls/s per asset is the binding limit for an inbox sync loop: one call per thread listing page, one per conversation, one per message detail.

## What strictly needs webhooks

Only events that are not persisted on the message or conversation object:

- Read receipts and delivery: `messaging_seen` (Instagram), `message_reads`, `message_deliveries` (Messenger). ([Messenger webhooks](https://developers.facebook.com/docs/messenger-platform/webhooks/))
- Button and icebreaker clicks (`messaging_postbacks`), opt-ins (`messaging_optins`, Messenger only), ad and ig.me/m.me referrals (`messaging_referrals`), message edits (`message_edits`, Messenger only), handover/routing events (`messaging_handovers`, `standby`), policy enforcement notices, deletion notices (Instagram: "Delete messages when you receive a webhooks notification to do so"). ([Messenger webhooks](https://developers.facebook.com/docs/messenger-platform/webhooks/), [IG webhooks](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/webhooks.md), [IG overview](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview.md))
- Real-time latency, and history beyond the 20-message cap.
- Webhooks themselves need a published app ("Your app must be published, regardless of app review status, to receive webhooks") and a public HTTPS receiver that answers within 5 s, which is the daemon the map rules out. ([IG webhooks](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/webhooks.md), [Messenger webhooks](https://developers.facebook.com/docs/messenger-platform/webhooks/))

Reactions, replies, story mentions and replies, shares (URL only), attachments and the unsupported-content flag are all readable by polling through the Message fields above.

## Open points to verify live (Language Ranch)

1. Does `/{page-id}/conversations?platform=instagram` work for a development-mode app whose business is not verified?
2. Under Standard Access, does the list include threads with people who hold no app role (hidden, error, or returned)?
3. Is `HUMAN_AGENT` accepted before the feature is approved when the recipient holds an app role?
4. Attachment URL lifetime on `attachments.image_data.url` / `file_url`.

## Sources

- https://developers.facebook.com/documentation/business-messaging/messenger-platform/conversations.md
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/conversations-api.md
- https://developers.facebook.com/docs/graph-api/reference/page/conversations/
- https://developers.facebook.com/docs/graph-api/reference/conversation/
- https://developers.facebook.com/docs/graph-api/reference/message/
- https://developers.facebook.com/docs/graph-api/reference/page/messages/
- https://developers.facebook.com/documentation/business-messaging/messenger-platform/send-messages
- https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/send-message.md
- https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/sender-actions.md
- https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/moderate-conversations.md
- https://developers.facebook.com/docs/messenger-platform/instagram/features/private-replies
- https://developers.facebook.com/documentation/business-messaging/messenger-platform/policy.md
- https://developers.facebook.com/docs/messenger-platform/changelog/
- https://developers.facebook.com/documentation/business-messaging/messenger-platform/overview.md
- https://developers.facebook.com/documentation/business-messaging/messenger-platform/overview/rate-limiting.md
- https://developers.facebook.com/docs/graph-api/overview/rate-limiting
- https://developers.facebook.com/docs/graph-api/overview/access-levels
- https://developers.facebook.com/docs/instagram-platform/overview/
- https://developers.facebook.com/documentation/business-messaging/instagram-messaging/overview.md
- https://developers.facebook.com/documentation/business-messaging/instagram-messaging/get-started
- https://developers.facebook.com/documentation/business-messaging/instagram-messaging/app-review/apps-for-your-own-business.md
- https://developers.facebook.com/documentation/business-messaging/instagram-messaging/webhooks.md
- https://developers.facebook.com/docs/messenger-platform/webhooks/
- https://developers.facebook.com/documentation/development/create-an-app/other-app-types/instagram-apis.md
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/messaging-api.md
- https://developers.facebook.com/docs/permissions/
