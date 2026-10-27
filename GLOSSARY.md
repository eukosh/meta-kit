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
