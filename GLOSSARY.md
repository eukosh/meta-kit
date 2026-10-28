# social-kit

CLI and MCP server for Instagram, Facebook Pages and Threads, built on Meta's official APIs. One context: how a user holds access to their own accounts and acts on them.

## Language

### Access

**Login**:
One authorization Meta granted to the user's app: a token, who it is for, and what it was granted. The unit the tool stores; a user may hold several, on one platform or across platforms.
_Avoid_: account, credential, session, token (the token is one part of a login)

**App credentials**:
The ids and secrets of the user's own Meta developer app, including its Threads app id and secret. Every login is issued by them.
_Avoid_: client secrets, app keys

**Asset**:
A Facebook Page, Instagram professional account or Threads account that a login exposes. Every platform command acts on exactly one asset.
_Avoid_: account, profile, page (as the general term), channel

**Default asset**:
The asset a platform's commands act on when none is named with `--as`. One per platform.
_Avoid_: active asset, current account

### Platforms

**Platform**:
One of Instagram, Facebook (Pages) or Threads: the first word of every command and the key of every default.
_Avoid_: service, network, product

### Content

**Post**:
What an asset publishes to stay. On Instagram a photo, reel or carousel, on the grid or only in the Reels tab; on a Facebook Page text, a link, photos, a video or a reel; on Threads text, an image, a video or a carousel. Reels and carousels are kinds of post, not separate things.
_Avoid_: media (collides with media files), item, status, thread (for a single Threads post)

**Story**:
An item an Instagram account or Facebook Page publishes that disappears after 24 hours. Not a post: it has its own listing and its own short life.
_Avoid_: post (for stories)

### Instagram content

**Mention**:
An @username naming an asset in someone's caption, comment or story.
_Avoid_: tag (a different thing), shout-out

**Tag**:
A person marked on a post or story by its author. Distinct from a mention: a post can tag you without mentioning you.
_Avoid_: mention, photo mention

### Facebook

**Page**:
The Facebook asset: a public presence run by a business or brand, as opposed to a person's profile.
_Avoid_: profile (for a Page)

**Lead**:
One person's answers to a Page's lead form.
_Avoid_: contact, submission

### Threads

**Reply**:
A Threads post written in answer to another post or reply. A post in its own right, with media, replies and insights of its own; the Threads counterpart of a comment.
_Avoid_: comment (for Threads)

**Ghost post**:
A Threads text post that archives itself 24 hours after publishing. Still a post, not a story.
_Avoid_: story, disappearing post

**Topic**:
The single tag a Threads post may carry to join a topic's feed.
_Avoid_: hashtag, tag (a different thing)

**Quote**:
A Threads post that embeds another post under its own text.
_Avoid_: quote tweet, share

**Repost**:
Putting another post onto your own profile as-is, with nothing added. Undoing it removes the repost, not the post.
_Avoid_: share, retweet

**Long text**:
The attachment that carries up to 10,000 characters, optionally styled, under a Threads text post or reply.
_Avoid_: text attachment, article, note
