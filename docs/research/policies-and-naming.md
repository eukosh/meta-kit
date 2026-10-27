# Meta platform policies that constrain the tool and its name

Researched 2026-10-27 for issue #8. Primary sources only: developers.facebook.com (Platform Terms and Developer Policies, both "Last updated February 3, 2026"), the App Dashboard and access-level docs, Meta's Brand Resource Center (meta.com/brand), and Meta's Ads CLI docs plus the installed `meta-ads` 1.2.0 package. Quotes are verbatim. Where a source is silent, it says so.

## Verdicts in one screen

| Question | Answer |
|---|---|
| Who is bound by the Platform Terms? | The user. Each user creates the App and is its "Developer" ("the person or entity that creates or operates an App"). meta-kit is not an App and has no app ID. |
| What must the user's app have? | A public privacy policy URL that explains processing and how to request deletion, and a data-deletion callback URL or instructions URL. ToS URL and category are needed only to go Live. |
| What must the tool do? | Protect tokens and app secrets, never transmit them anywhere but Meta, keep no copy of Platform Data longer than needed, act only on the user's explicit instruction. |
| `meta-kit` | Not safe. "Meta" is a listed trademark and the rules forbid combining any Meta mark with generic terms or using one as part of a product, company, username or domain name. Rename. |
| `mtk` | Safe. No Meta mark. Fits the Ads CLI, whose command is `meta`. |
| `ig`, `fb`, `threads` as subcommands | Low risk as command namespaces; no Meta text addresses command names. "IG" is a listed Meta trademark and "FB" is explicitly banned from app names. Offer `instagram`, `facebook`/`page`, `threads` as the canonical spellings with `ig`, `fb`, `th` as aliases. |
| Long-term development mode | Permitted. No time limit is stated. Standard Access is auto-granted and "is all your app needs" when the app serves accounts you own or manage. App Review, Business Verification and Data Use Checkup are not required. |
| Scraping | Only official endpoints, respect limits, no bulk backup of other people's content, no automated access outside the API. |
| Ads CLI credentials | `ACCESS_TOKEN` env var, a `.env` in the working directory, and (undocumented) a `credentials` file in the XDG config dir `meta`. meta-kit must not read or write any of these. |

## 1. Who the rules bind

Platform Terms §12: "'App' means any technical integration with Platform or to which we have assigned an App identification number." "'Developer' means the person or entity that creates or operates an App." Every meta-kit user creates their own app, so the user is the Developer and the one who accepted the Terms; meta-kit is software they run inside their own app. [Platform Terms](https://developers.facebook.com/terms/)

The "Tech Provider" role ("a Developer of an App whose primary purpose is to enable Users thereof to access and use Platform or Platform Data", §12.s, with §5.b duties: act only "on behalf of and at the direction of your Client", keep client data separate, keep a client list) applies to operators of a hosted app that other businesses log in to. It does not apply to meta-kit as planned, since nothing is hosted and the tool holds no one else's data. It would apply if the project ever ran a shared app or a hosted media relay. [Platform Terms §5.b, §12](https://developers.facebook.com/terms/)

Developer Policies §5 (Messenger Platform and Instagram Messaging) applies the same idea to anyone acting for an entity: "Ensure you have the authority to act as an agent for the entity to which you're providing a service, and that your use of our Platform is strictly for the benefit of that entity." [Developer Policies](https://developers.facebook.com/devpolicy/)

## 2. What the user's app must have

### Privacy policy

Platform Terms §4.a: "You will provide, maintain, and comply with a privacy policy that is available through an active, publicly available, easily accessible (including by our crawlers), and non-geoblocked URL. This URL must also be disclosed in the privacy policy field in the settings of your App Dashboard."

§4.b: "Your privacy policy must clearly explain what data you are Processing, how you are Processing it, the purposes for which you are Processing it, and how Users may request deletion of that data. The right to request deletion must be available to all Users who can access your App."

§4.c: "You may only Process Platform Data as clearly described in your privacy policy". [Platform Terms](https://developers.facebook.com/terms/)

The Terms attach this to every App; they do not exempt development mode. The dashboard enforces less: the Basic Settings doc says the Terms of Service URL and Category fields are each "required to switch your app to Live mode", and describes the Privacy Policy URL only as the link "to your app's privacy policy that applies to your app users". Whether a dev-mode app can be used without the field filled is not stated. [Basic Settings](https://developers.facebook.com/docs/development/create-an-app/app-dashboard/basic-settings)

The Terms' exceptions page (§3.e) exempts only Messenger communication content, lead data and shops data from §3.a-d; §4 "and all other applicable terms and policies still apply". [Platform Terms exceptions](https://developers.facebook.com/terms/3e/)

What this means for meta-kit: the guided setup should tell the user to publish a privacy policy page and paste its URL. The tool can ship a template (as ytk's PRIVACY.md did) stating that the app is used by its owner only, that data stays on the owner's machine, and how to delete it. The Terms require the policy to exist and to describe the actual processing; they do not prescribe a format.

### Data deletion

"Apps that access user data must provide a way for users to request that their data be deleted." "all apps must inform users in their privacy policy how to request deletion of their data." Either a callback URL or an instructions URL must be set in the App Dashboard; the callback "must use the secure HTTPS protocol", must start deleting the user's data and return JSON `{ url: '<url>', confirmation_code: '<code>' }` pointing to a human-readable status. "Failure to comply with these requirements may result in your callback being removed or your app being disabled." The doc does not say whether development-mode apps must fill the field. [Data Deletion Callback](https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback)

Platform Terms §3.d.i: "Update or delete Platform Data promptly after receiving a request from us or the User to do so", and delete when the data is no longer needed, when you stop operating the App, or "When a User requests their Platform Data be deleted or no longer has an account with you". [Platform Terms](https://developers.facebook.com/terms/)

For a single-owner app the instructions URL is the practical choice: a page saying "run `mtk auth logout` and delete the config directory". The same page can be the privacy policy.

### Other dashboard fields

App secret: "It is extremely important that an App Secret be stored securely and not be included in any code that could be accessed by anyone other than a developer of the app." [Basic Settings](https://developers.facebook.com/docs/development/create-an-app/app-dashboard/basic-settings)

App cap: "You are permitted to have a developer or administrator role on a maximum of 15 apps that are not already connected to a Meta Verified Business Account." [Create an Instagram app](https://developers.facebook.com/documentation/instagram-platform/create-an-instagram-app)

## 3. What the policies require of the tool

### Token and secret handling

Platform Terms §6.a.iv: "You must protect and not transfer, share, or solicit Meta user IDs, access tokens, or app secrets, but you may share with a Service Provider who helps you build, run, or operate your App."

§6.a.i: safeguards that "Meet or exceed industry standards given the sensitivity of the Platform Data" and "Are designed to prevent any unauthorized ... Processing ... of Platform Data". §6.a.iii: "you must not separately request or collect a Meta user's login credentials". §12.l counts access tokens as Platform Data. [Platform Terms](https://developers.facebook.com/terms/)

Consequences: tokens and app secrets stay on the user's machine, in a file only the user can read, and travel only to graph.facebook.com / graph.instagram.com / graph.threads.net. No telemetry, no third-party relay. `mtk auth status` should mask tokens (the Ads CLI does: "Shows a masked version of the stored token"). The tool must never ask for a Facebook password; OAuth in the browser or a pasted system-user token are the only routes.

### Acting for the user

Developer Policies 1.7: "Obtain consent from people before publishing content or taking any other action on their behalf." 2.2: "Respect the way Meta Products look and function, and the limits we've placed on product functionality." 2.7: "Don't participate in any program that promotes or facilitates the purchase, sale, or exchange of 'Likes', 'Shares', 'Followers', 'Comments', 'Accounts', 'Pages', 'Profiles', 'Groups'". 11.5: "Don't create or claim a Page on behalf of people without their consent." Messaging 5.6.2.d: "Don't prefill any content in messages unless (a) it was created by the person using your App". [Developer Policies](https://developers.facebook.com/devpolicy/)

The MCP route is the one to watch: an agent publishing or replying is an action "on their behalf". The map's rule that the skill shows content and gets a yes is the consent step 1.7 asks for.

### Instagram-specific

Developer Policies 6: "Comply with any requirements or restrictions imposed on usage of Instagram user photos and videos ('User Content') by their respective owners. ... Don't use the Instagram Platform to simply display User Content, import or backup content, or manage Instagram relationships, without our prior permission." [Developer Policies](https://developers.facebook.com/devpolicy/)

This rules out an "export my whole feed to disk" feature as a headline and any follow/unfollow tooling. Reading one's own media list and comments for daily work is what the endpoints are for; a bulk archive command is where the line sits. The policy does not define "backup"; treat it as a tier-2 decision with this clause attached.

### Data handling

Platform Terms §3.a.viii forbids "Processing Platform Data for purposes other than the applicable permitted purposes set forth in Meta's Developer Docs"; §3.a.iv "Selling, licensing, or purchasing Platform Data"; §3.a.v building profiles without consent; §3.d.i deleting data that is no longer needed. [Platform Terms](https://developers.facebook.com/terms/)

So: no persistent cache of insights or comments beyond what a command needs, or if one is added, a `mtk cache clear` and a line in the privacy template.

### Does meta-kit itself need a privacy policy?

Not under Meta's terms: the project is not an App and processes nothing. A short PRIVACY.md in the repo still helps users write theirs and documents the local-only design. Recommendation, not a requirement.

## 4. Naming

### The rules, verbatim

Developer Policies 1.3: "Follow our Meta Advertising Standards for your App name, icons, and description." 2.4: "If you want to use our logos or brand, follow the guidelines in the Meta Brand Resource and Permissions Center and the Logos and Trademarks requirements." 2.5: "Be honest about your relationship with Meta when talking to the press or users." [Developer Policies](https://developers.facebook.com/devpolicy/)

Logos and Trademarks (developer docs, English last updated 4 May 2021): "You may accurately indicate that your application is integrated with the Facebook Platform. However, you may not use our brands in your name in an unauthorized way." Do: "Accurately describe how your app works with Facebook, such as 'Log in with Facebook'". Don't: "Use our brands in a way that implies partnership, sponsorship, or endorsement by us", "Combine any part of our brands with your name, marks, or generic terms", "Use names or logos that imitate or could be confused with our brands". Examples: "Do not use names that include 'Facebook' or 'FB': 'Facebook Friend Smash' or 'FB Friend Smash' 'Friend Smash for Facebook' or 'Friend Smash for FB'". "Do not use 'F', 'Book', or 'Face' in your name if it could be perceived as a reference to Facebook". [Logos and Trademarks](https://developers.facebook.com/docs/app-review/resources/logos)

Meta company brand (updated June 2026), Legal: "Meta's trademarks are owned by Meta and may only be used as provided in these guidelines or with Meta's permission." "You may not use or register, or otherwise claim rights in any Meta trademark, including as or as part of any trademark, service mark, company name, trade name, username or domain registration." "You should not use or claim rights in any trademark in a way that is confusingly similar to or dilutive of Meta's trademarks, including as, or as any part of, a trademark." "All usage of the Meta logo requires approval." The page gives no "for Meta" descriptive allowance. [Meta brand](https://www.meta.com/brand/resources/meta/company-brand/)

Instagram brand: "If you offer an app, website or a product or service that uses the Instagram APIs or is otherwise compatible with or related to Instagram, you may only use Instagram to say that your app is 'for Instagram' or that the name of your campaign is 'on Instagram' in a descriptive manner." "Don't modify, abbreviate or translate the word Instagram". "Don't combine 'Insta' or 'gram' with your own brand." "Don't combine any part of the Instagram brand with a company name, other trademarks, or generic terms." The page never mentions "IG". [Instagram brand](https://www.meta.com/brand/resources/instagram/instagram-brand/)

Facebook brand (updated December 2024), FAQ: "You may not use any Facebook trademarks, or anything similar" in your trademark, domain name, username or other account name. Same Legal paragraph as above. The page does not address "FB" or "for Facebook" phrasing. [Facebook brand](https://www.meta.com/brand/resources/facebook/logo/)

Threads brand: logo and lock-up rules only; nothing on third-party names, "for Threads", or abbreviations. No Legal section. [Threads brand](https://www.meta.com/brand/resources/threads/)

Trademark glossary ("The absence of a product or service name or logo from this list does not mean that we have waived our rights"): listed marks include **Face**, **Facebook**, **Gram**, **IG**, **Insta**, **Instagram**, **Meta**, **Meta Platforms**, **Meta Open Source**, **Threads**, **Reels**, **Stories**. "FB" is not listed; "Graph API" is not listed. [Our trademarks](https://www.meta.com/brand/resources/facebookcompany/our-trademarks/)

### Verdicts

**`meta-kit`** (package, plugin, MCP server, repo). "Meta" is a listed trademark (Company Name, Platform, Service). `meta-kit` is exactly "Combine any part of our brands with your name, marks, or generic terms", and the Legal paragraph forbids a Meta mark "as or as part of any trademark, service mark, company name, trade name, username or domain registration", which covers a PyPI name, a GitHub repo and a domain. Unlike Instagram, the Meta page offers no descriptive "for Meta" carve-out. "meta" is also an ordinary English word and Meta cannot stop generic use, but the project's meaning is Meta-the-company, so the generic defence is thin. Also, Meta's own CLI command is `meta`. Verdict: rename.

**`mtk`**. Contains no Meta mark and resembles none. Safe as command and as project name.

**`ig`**. "IG" is in Meta's trademark glossary. No Meta text covers CLI subcommands or MCP tool prefixes, which are neither product names nor registrations. The Instagram page's "Don't ... abbreviate ... the word Instagram" is written for brand references in marketing copy. Verdict: acceptable as a namespace, not as any part of the product name. Lower-exposure option: canonical `instagram`, alias `ig` (and MCP tools `instagram_post_create` or keep `ig_` since tool names are internal identifiers).

**`fb`**. "FB" is explicitly banned from app names, icons and logos; the glossary does not list it. Same subcommand reasoning as `ig`. Since the namespace covers Facebook Pages only, `page`/`pages` or `facebook` avoids the question entirely. Verdict: `facebook` canonical, `fb` alias, or `page`.

**`threads`**. A listed mark, but a subcommand named after the platform it addresses is plain descriptive use, and the Threads brand page has no naming rule. Alias `th` is fine. Verdict: keep.

**Descriptions and taglines**. "CLI and MCP server for Instagram, Facebook Pages and Threads" is the allowed descriptive form ("for Instagram", "Log in with Facebook"). Avoid "Meta CLI", "the Meta toolkit", logos, and anything implying partnership. Developer Policies 2.5 adds: be honest that the project is independent.

**Alternatives for the project name**. Any name that contains none of Meta, Insta, gram, IG, FB, Face, Book, Threads, Reels, Stories. Options that keep the `mtk` command: make `mtk` the project name too ("mtk: CLI and MCP server for Instagram, Facebook Pages and Threads"); or a neutral word plus kit, as youtube-kit's sibling, e.g. `socialkit`/`social-kit`, `pagekit`, `graphkit` ("Graph API" is not a listed mark, but it is Meta's product name; moderate). Check PyPI and GitHub availability before choosing.

## 5. What long-term development-mode use permits

App modes: "All newly created apps start out in Development mode." "Apps in Development mode can only request permissions from role users". "Apps in Development mode cannot be searched for by the public." "You should only switch the app to Live mode after you have completed app development and have completed App Review." No time limit on Development mode is stated. [App Modes](https://developers.facebook.com/docs/development/build-and-test/app-modes)

Access levels: "Permissions with Standard Access can only be requested from app users who have a role on the requesting app." "Standard Access is intended for apps that will only be used by people who have roles on them". "All Business, Consumer, and Gaming apps are automatically approved for Standard Access for all permissions and features." "Business Verification is required to get Advanced Access." "Advanced Access must be approved on an individual permission and feature basis through the App Review process." [Access Levels](https://developers.facebook.com/docs/graph-api/overview/access-levels)

Instagram Platform overview: "If your app only serves your Instagram professional account or an account you manage, Standard Access is all your app needs." "Advanced Access is the access level required if your app serves Instagram professional accounts that you don't own or manage and can be used by app users who do not have a role on your app or a role on a business portfolio that has claimed your app." Caveat on the same page: "Because of the limited scope of Standard Access, some features might not work properly until your app has been granted Advanced Access." [Instagram Platform overview](https://developers.facebook.com/documentation/instagram-platform/overview)

App Review: "If your app will only be used by app users who have a role on the app itself, App Review is not required." Required "If your app will be used by anyone without a Role on the app or a role in a Business that has claimed the app". [App Review](https://developers.facebook.com/docs/app-review)

Data Use Checkup: "Data Use Checkup is not required for developers whose apps have Standard Access." Not required in Development mode; required before going Live or with Advanced Access. [Data Use Checkup](https://developers.facebook.com/docs/development/maintaining-data-access/data-use-checkup)

Roles: "Testers can grant the app any permission while it is in development." "Apps can have up to 500 administrators." Most unlinked apps "can have up to 50 testers"; apps linked to a verified business, "up to 500". [App Roles](https://developers.facebook.com/docs/development/build-and-test/app-roles)

Threads: testers are invited under App roles > Roles ("selecting Threads Tester") and "Invitations can be accepted by the Threads user in the Website permissions section under Account Settings". Without a role, "each permission must first be approved through the App Review process, and your app must be published." [Threads get started](https://developers.facebook.com/docs/threads/get-started)

Instagram with Instagram Login: the app must be a Business type; test accounts are added under App Roles > Roles or Instagram > API Setup, and "This account must be public." [Create an Instagram app](https://developers.facebook.com/documentation/instagram-platform/create-an-instagram-app)

Net: a user who owns the Page, Instagram account and Threads profile, or holds a role in the business that claimed the app, can run meta-kit indefinitely in Development mode with Standard Access. The Platform Terms (privacy policy, deletion, security) still apply. The App Review path belongs in the "not yet specified" list, as the map already has it.

## 6. Rate limits and automated access

Meta Terms of Service 3.2 (effective 1 January 2025): "You may not access or collect data from our Products using automated means (without our prior permission)" and you may not "circumvent, bypass, or override any technological measures" that control access. The Graph API is the permitted means; nothing else is. [Meta Terms of Service](https://www.facebook.com/terms.php)

Developer Policies 3.6: "We may take enforcement action on Apps that adversely affect the stability of Meta's servers or other Apps on Platform." [Developer Policies](https://developers.facebook.com/devpolicy/)

Graph API rate limits: app token `200 * Number of Users` calls per rolling hour; Pages with Page or system-user tokens `4800 * Number of Engaged Users` per 24 h; Instagram Platform `4800 * Number of Impressions` per 24 h per app-user pair; Instagram messaging per-second limits (Conversations API 2/s). Headers `X-App-Usage` (call_count, total_time, total_cputime as percentages) and `X-Business-Use-Case-Usage` (includes `estimated_time_to_regain_access` in minutes). Error codes 4 (app), 17 (user), 32 (Page), 613 (custom), 80001 (Page BUC), 80002 (Instagram BUC). Guidance: stop calling once throttled (continuing extends the wait), spread requests, use field filters, batch IDs. [Rate Limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting)

Instagram publishing: "Instagram accounts are limited to 100 API-published posts within a 24-hour moving period." Check with `GET /<IG_ID>/content_publishing_limit`. The carousel section of the same page says "Accounts are limited to 50 published posts within a 24-hour period"; the page does not reconcile the two. Media "must be hosted on a publicly accessible server at the time of the attempt." [Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing)

Threads: "Threads profiles are limited to 250 API-published posts within a 24-hour moving period", 1,000 replies, 100 deletions, 500 location searches; app calls `4800 * Number of Impressions` with a floor of 10; check with `GET /{threads-user-id}/threads_publishing_limit`; "Enforce the publishing rate limit in your app" when scheduling. [Threads overview](https://developers.facebook.com/docs/threads/overview)

For the CLI: read the usage headers and expose them (`mtk quota`), map codes 4/17/32/613/8000x to a distinct exit code with the regain-access time, never auto-retry a throttled call, and keep bulk reads paginated with field selection. Hashtag search and business discovery count against platform limits, so a read-everything mode is the thing to avoid.

## 7. How Meta's Ads CLI stores credentials

Documented: the command is `meta` (`brew install facebook/fb/meta-ads`, PyPI `meta-ads`, Python 3.12+; "installs the `meta` command"). It "requires a system user access token" from Business Suite. Variables: `ACCESS_TOKEN` (required), `AD_ACCOUNT_ID` (required for most commands), `BUSINESS_ID`, `APP_ID`, `APP_SECRET` (optional, "used by some login and app-scoped flows"). Storage: "Create a `.env` file in the directory where you run Ads CLI" or `export ACCESS_TOKEN=...`. Precedence: command-line flags, then environment variables, then the project `.env`; "Shell environment variables take precedence over `.env` file values." `meta auth status` "Shows a masked version of the stored token." No `login`/`logout` is documented, nor file permissions or a keychain. [Configuration](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/setup/configuration), [Get started](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/setup/get-started), [Command reference](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/command-reference), [PyPI meta-ads](https://pypi.org/project/meta-ads/)

Undocumented, from the installed `meta-ads` 1.2.0 (`src/meta/config.py`, shipped compiled; docstrings and string constants): precedence has a fourth tier, "4. User-level config"; `get_config_dir` returns "the XDG-compliant config directory for meta" (constants `XDG_CONFIG_HOME`, `.config`); `get_credentials_path` returns "the path to the credentials file" (constant `credentials`); `get_access_token` reads "from env or credentials file"; `get_auth_port` reads "the local OAuth callback port from env, default 8787". So the user-level location is `$XDG_CONFIG_HOME/meta/credentials`, by default `~/.config/meta/credentials`, and a browser-login flow exists in the code even though the docs show only status. The license is proprietary, so this is observation of behaviour, not source.

For meta-kit: never touch `~/.config/meta/`, never read a bare `ACCESS_TOKEN`, `APP_ID` or `APP_SECRET` from the environment or from a `.env` in the working directory (an Ads CLI user's project would be silently consumed, and a system-user token scoped for ads would land in the wrong tool). Use a tool-specific directory (`$XDG_CONFIG_HOME/<name>/`) with mode 0600 files, and prefixed variables (`MTK_ACCESS_TOKEN` style) if env override is wanted.

## 8. Silences and conflicts

- No Meta text covers CLI subcommand or MCP tool naming; the verdicts on `ig`/`fb` extend trademark rules written for product names.
- The Meta brand page allows no descriptive "for Meta" use; Instagram's does for "for Instagram". Treat Meta as the stricter case.
- "FB" is banned in the developer Logos doc but absent from the trademark glossary; the glossary says absence waives nothing.
- Whether a development-mode app can run without a privacy policy URL or deletion URL is not stated anywhere; the Terms require both regardless of mode.
- Instagram's publishing limit is given as 100 and as 50 on the same page.
- The Ads CLI's user-level credentials file and OAuth port are in the binary, not the docs; the docs may lag or the feature may be unreleased.
- The developer docs' Logos page predates the Meta rename (2021) and still says "Facebook Platform".

## Sources

- Platform Terms: https://developers.facebook.com/terms/ and exceptions https://developers.facebook.com/terms/3e/
- Developer Policies: https://developers.facebook.com/devpolicy/
- Meta Terms of Service: https://www.facebook.com/terms.php
- Data Deletion Callback: https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback
- Basic Settings: https://developers.facebook.com/docs/development/create-an-app/app-dashboard/basic-settings
- App Modes: https://developers.facebook.com/docs/development/build-and-test/app-modes
- App Roles: https://developers.facebook.com/docs/development/build-and-test/app-roles
- Access Levels: https://developers.facebook.com/docs/graph-api/overview/access-levels
- App Review: https://developers.facebook.com/docs/app-review
- Data Use Checkup: https://developers.facebook.com/docs/development/maintaining-data-access/data-use-checkup
- Rate Limiting: https://developers.facebook.com/docs/graph-api/overview/rate-limiting
- Instagram Platform overview: https://developers.facebook.com/documentation/instagram-platform/overview
- Create an Instagram app: https://developers.facebook.com/documentation/instagram-platform/create-an-instagram-app
- Instagram Content Publishing: https://developers.facebook.com/docs/instagram-platform/content-publishing
- Threads overview and get started: https://developers.facebook.com/docs/threads/overview, https://developers.facebook.com/docs/threads/get-started
- Logos and Trademarks: https://developers.facebook.com/docs/app-review/resources/logos
- Meta brand: https://www.meta.com/brand/resources/meta/company-brand/
- Facebook brand: https://www.meta.com/brand/resources/facebook/logo/
- Instagram brand: https://www.meta.com/brand/resources/instagram/instagram-brand/
- Threads brand: https://www.meta.com/brand/resources/threads/
- Meta trademark glossary: https://www.meta.com/brand/resources/facebookcompany/our-trademarks/
- Ads CLI: overview https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/ads-cli-overview, configuration, get started, command reference (linked above); PyPI https://pypi.org/project/meta-ads/; installed package meta-ads 1.2.0 via Homebrew `facebook/fb/meta-ads`
