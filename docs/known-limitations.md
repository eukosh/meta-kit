# Known limitations

What skit can't do, and why. Most of it is missing from Meta's APIs; the rest sits behind App Review, which a bring-your-own-app user in development mode doesn't have.

## All platforms

- **Bursts get accounts suspended.** Meta's integrity checks treat posts made through the API like any other. A young account publishing many near-identical posts in a few hours can be locked pending appeal (it happened to us on Threads). Space publishes out and vary the text.

## Threads

Not in the API:

- **Scheduling.** No scheduled publish time. Run `skit th post create` from an outside scheduler (`at`, cron, launchd, or your agent's scheduled tasks).
- **Editing** a post or reply after publishing. Delete and republish instead.
- **Likes**, and **follower or following lists**.
- **Following.** `skit th profile follow @user` only opens Threads' follow page; you click Follow yourself.
- **DMs.**
- **Text styling in the main text.** Bold, italic, highlight, underline and strikethrough work only in a post's long text; the main text takes spoilers only.

Unreachable without App Review:

- **Location tagging.** In development mode, location search returns only places around Menlo Park, whatever you search for.
- **Sharing to Instagram Stories.** The Threads use case doesn't offer the permission.
- **Search** covers only your own posts.
- **Profile discovery** (`profile get @user`, `post list @user`) reaches only @threads, @meta, @instagram and @facebook.
- **Mentions** (`mention list`) shows only mentions made by the app's Threads Testers, per Meta's docs.
- **Other people's posts** can't be read by id. Replies to your own posts are not affected: everyone's replies show.

Other:

- **Hiding replies** works only on top-level replies to your posts, not nested ones or your own.
- **Geo-gating** (`--countries`) works only for accounts Meta marks eligible.
