# MCP servers with large tool surfaces

Researched 2026-10-29 against primary sources: the MCP specification (current revision 2026-07-28), its SEPs and working-group pages, Anthropic, OpenAI, VS Code, Cursor, Windsurf (now Devin docs), Codex, Gemini CLI and FastMCP documentation, and the source code or official docs of the GitHub, Azure, Stripe, Supabase, Notion, Linear, Sentry, AWS and Cloudflare servers. Third-party write-ups were used only to find primary pages. Where only GitHub issues exist (elicitation in Claude Desktop and Codex), that is said.

Question: social-kit's natural surface is about 110 `@operation` functions (Instagram ~44, Facebook ~45, Threads ~22; ~58 tier 1). What do current clients, the spec and large official servers say about exposing that through MCP, and what should social-kit do?

## Bottom line

1. **Clients now do discovery themselves.** Claude Code, Codex, the Claude apps and Cursor defer MCP tool definitions by default and load them on demand. VS Code still has a hard cap of 128 tools per request and Windsurf of 100 in total, both counted across all servers.
2. **Annotations, output schemas and approval rules are per tool.** Nothing in the spec is per argument. A tool that mixes reads and writes loses read-only auto-approval in VS Code and Codex, and loses name-based allow rules in Claude Code. GitHub's maintainer names this cost directly.
3. **Large servers converged on tools split by safety class.** GitHub went to `<noun>_read` / `<noun>_write` with a `method` parameter. Stripe went to `search`, `details`, `read` and `write`. Azure's consolidated mode groups only commands with identical annotations. Server-side discovery meta-tools are on the way out: GitHub removed its dynamic toolsets in May 2026, and the 2026-07-28 spec forbids tool lists that change as a side effect of a call.
4. **Elicitation is not a reliable confirmation channel yet.** It moved to multi-round-trip results in 2026-07-28, Claude Desktop does not render it, and Claude Code serves it only in interactive sessions. Servers that guard money or deletes keep a token re-call fallback: Stripe, Supabase and Notion all do.

Recommendation for social-kit, in order:

1. Platform + noun tools split by safety class: `<noun>_read`, `<noun>_write`, plus one guarded `<platform>_delete`, each with a `method` enum. Roughly 25-30 tools.
2. Platform × safety class with an operation enum, the Stripe shape. Roughly 9-12 tools.
3. The status quo, one tool per operation, behind `--platform` and `--read-only` filters.

Not recommended: server-side search/describe/run meta-tools, and server-side code mode. Details below.

## 1. Client limits and behaviour today

| Client | Tool-count limit | Native deferral / search | `list_changed` | Uses annotations for approval |
|---|---|---|---|---|
| Claude Code | No fixed cap; "the practical limit is your context window budget" ([mcp docs](https://code.claude.com/docs/en/mcp)) | Tool search on by default for Opus/Sonnet 4+ and Haiku 4.5+; only names and server instructions load at start; `ENABLE_TOOL_SEARCH=auto` loads upfront under 10% of context ([mcp docs](https://code.claude.com/docs/en/mcp)) | Refetches in interactive sessions; `-p`/Agent SDK refresh tools only; on 2026-07-28 servers via a held `subscriptions/listen` stream ([mcp docs](https://code.claude.com/docs/en/mcp)) | `readOnlyHint` lets read-only calls run in parallel; `idempotentHint`/`readOnlyHint` allow retry after a dropped connection; `_meta["anthropic/requiresUserInteraction"]` forces a full prompt ([mcp docs](https://code.claude.com/docs/en/mcp)). Permission rules match tool names (`mcp__srv__*`, `mcp__github__get_*`), not MCP arguments; settings skip `mcp__` rules with parentheses ([permissions](https://code.claude.com/docs/en/permissions)) |
| Claude apps (claude.ai, Desktop, Cowork, mobile) | None documented | Tool access mode "Auto" (default) / "Always available" / "On demand"; On demand suggested for 10+ connectors or 30+ tools ([help](https://support.claude.com/en/articles/13730515-manage-claude-s-tool-access)) | Not documented | Admins set Always allow / Needs approval / Blocked per tool or per category, "categorized by type (for example, read-only tools, write/delete tools)" ([help](https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities)); the article does not say annotations drive the categories |
| VS Code (Copilot) | **128 tools per request**, across all servers and built-ins ([tools FAQ](https://code.visualstudio.com/docs/agents/run/tools)) | "Virtual tools" (`github.copilot.chat.virtualTools.threshold`) group tools behind `activate_*` stubs past the threshold, capped at 128 ([vscode#294055](https://github.com/microsoft/vscode/issues/294055)) | Supported ("dynamic tool discovery", [MCP dev guide](https://code.visualstudio.com/api/extension-guides/ai/mcp)) | "The confirmation dialog will be shown for all tools that are not marked with the `readOnlyHint` annotation" ([MCP dev guide](https://code.visualstudio.com/api/extension-guides/ai/mcp)) |
| Cursor | No documented cap; forum reports of a 40-tool warning in versions before 2.3 are anecdotal | Since 2026-01-06 the agent sees only tool names; descriptions sit in files it reads on demand (−46.9% tokens in runs that used an MCP tool) ([blog](https://cursor.com/blog/dynamic-context-discovery)) | Not documented | Asks before every MCP tool by default; allowlists per tool ([docs](https://cursor.com/docs/context/mcp)); annotations not mentioned |
| Windsurf / Devin Desktop | **"a limit of 100 total tools"** ([docs](https://docs.devin.ai/desktop/cascade/mcp)) | None documented; `disabledTools` per server | Not documented | Not documented |
| Codex | None documented | Since 0.142.2 (merged 2026-06-22) every MCP tool is deferred behind `tool_search` when the model supports it; before that only at ≥100 tools ([openai/codex#29486](https://github.com/openai/codex/pull/29486)). Client-side `features.code_mode` also exists ([config reference](https://developers.openai.com/codex/config-reference)) | Not documented | `default_tools_approval_mode = writes` "prompts for tools that aren't marked read-only"; per-tool overrides ([Codex MCP docs](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)) |
| Gemini CLI | None documented | None; `includeTools` / `excludeTools` per server ([docs](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md)) | Not documented | Confirmation unless the server or `server.tool` is trusted; annotations not used ([docs](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md)) |

Model APIs underneath:

- **Anthropic tool search tool** (GA): up to 10,000 deferred tools; 5 results per search by default; searches names, descriptions, argument names and argument descriptions. Keep the "3–5 most frequently used tools non-deferred". "Claude's ability to pick the right tool degrades once you exceed 30–50 available tools." ([docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool))
- **OpenAI tool search** (Responses API, gpt-5.4+): `defer_loading` on functions or whole MCP servers. Models "have primarily been trained to search" namespaces and MCP servers. "Aim to keep each namespace to fewer than 10 functions" ([docs](https://developers.openai.com/api/docs/guides/tools-tool-search)). The function-calling guide says to "aim for fewer than 20 functions available at the start of a turn", calling it "a soft suggestion" ([docs](https://developers.openai.com/api/docs/guides/function-calling)).

What Claude Code's tool search means for a server author:

- Server instructions matter more under tool search. Claude Code cuts instructions and upfront tool descriptions at **4,096 characters** and deferred tool descriptions at **16,384** ([mcp docs](https://code.claude.com/docs/en/mcp)).
- A server can pin a tool upfront with `_meta["anthropic/alwaysLoad"]` ([mcp docs](https://code.claude.com/docs/en/mcp)).
- Text results over 50,000 characters are saved to a file unless the tool declares `_meta["anthropic/maxResultSizeChars"]` ([mcp docs](https://code.claude.com/docs/en/mcp)).

## 2. Accuracy: many tools vs. consolidated tools

Measured evidence on the number of tools in context:

- Anthropic's internal MCP evaluations with tool search: Opus 4 from 49% to 74%, Opus 4.5 from 79.5% to 88.1%. A 58-tool, five-server setup costs about 55K tokens upfront ([advanced tool use, 2025-11-24](https://www.anthropic.com/engineering/advanced-tool-use)).
- RAG-MCP: retrieving tools before the call took selection accuracy from 13.62% to 43.13% and cut prompt tokens by over 50% ([arXiv 2505.03275](https://arxiv.org/abs/2505.03275)).
- Consolidation saves tokens. GitHub's Projects toolset collapsed into `projects_list` / `projects_get` / `projects_write` and saved "about 23,000 tokens (50%)" ([changelog 2026-01-28](https://github.blog/changelog/2026-01-28-github-mcp-server-new-projects-tools-oauth-scope-filtering-and-new-features/)). Cloudflare's two-tool code-mode server uses about 1,000 tokens for an API that would take 1.17M tokens as one tool per endpoint ([blog, 2026-02-20](https://blog.cloudflare.com/code-mode-mcp/)).

**No primary source measures accuracy for one-tool-per-operation against consolidated `action`/`method` tools on the same task set.**

- GitHub's consolidation changelog makes qualitative claims only ([2025-10-29](https://github.blog/changelog/2025-10-29-github-mcp-server-now-comes-with-server-instructions-better-tools-and-more/)).
- One 2026 preprint calls a free-form `do_anything(action, params)` tool an anti-pattern where "tool selection accuracy collapses", but it reports no measurement ([arXiv 2606.30317](https://arxiv.org/abs/2606.30317)).
- Anthropic's guidance favours fewer, workflow-shaped tools and namespacing by service and resource. It reports that prefix-vs-suffix naming had measurable, model-dependent effects ([writing tools for agents, 2025-09-11](https://www.anthropic.com/engineering/writing-tools-for-agents)).
- `input_examples` raised complex-parameter accuracy from 72% to 90% in Anthropic's testing ([advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use)). This field exists only in the Anthropic API; MCP has no examples field.

## 3. Patterns used by large official servers

| Server | Shape | Annotations | Output schema | Confirmation / approval |
|---|---|---|---|---|
| GitHub (`github-mcp-server`) | 97 tools in the README, grouped into toolsets (default: context, repos, issues, pull_requests, users). Consolidated `issue_read` (methods `get`, `get_comments`, `get_labels`, `get_sub_issues`), `issue_write`, `pull_request_read`, `projects_list/get/write`, `actions_list/get/run_trigger` ([changelog](https://github.blog/changelog/2025-10-29-github-mcp-server-now-comes-with-server-instructions-better-tools-and-more/), [README](https://github.com/github/github-mcp-server)). `--toolsets`, `--tools`, `--read-only`, `/x/{toolset}/readonly` URLs ([remote-server.md](https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md)). Dynamic toolsets (`enable_toolset` and similar meta-tools) **removed 2026-05-20** because discovery is moving "up to the client and model API level" ([#275](https://github.com/github/github-mcp-server/issues/275), [PR #2512](https://github.com/github/github-mcp-server/pull/2512)) | Reads and writes are kept in separate tools. Maintainer: combining them means annotations "have to say the tools are not ReadOnly", forcing users to pick between auto-approving writes and manually approving reads ([#275 comment](https://github.com/github/github-mcp-server/issues/275)) | On 2026-07-28 connections, consolidated tools return structured objects with a `method` discriminant and method-specific typed fields ([README](https://github.com/github/github-mcp-server)) | Repository deletion keeps "its existing confirmation flow" ([README](https://github.com/github/github-mcp-server)) |
| Azure MCP | Four modes. `namespace` (default): one tool per service, a "hierarchical MCP command router" with `intent`, `command`, `parameters` and `learn=true` discovery. `consolidated`: 174 curated tools covering 448 commands. `single`: one `azure` tool. `all`: ~800+ tools ([TROUBLESHOOTING](https://github.com/microsoft/mcp/blob/main/servers/Azure.Mcp.Server/TROUBLESHOOTING.md), [consolidated-tools.json](https://github.com/microsoft/mcp/blob/main/servers/Azure.Mcp.Server/src/Resources/consolidated-tools.json)) | Consolidated tools group only commands with "exact matching toolMetadata" ([new-command.md](https://github.com/microsoft/mcp/blob/main/servers/Azure.Mcp.Server/docs/new-command.md)): 81 read-only, 63 destructive, 30 non-destructive writes. Namespace tools carry group-level hints ([NamespaceToolLoader.cs](https://github.com/microsoft/mcp/blob/main/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/ToolLoading/NamespaceToolLoader.cs)) | Aggregate output schema in namespace mode | Per command: a destructive or secret command triggers elicitation. If the client lacks elicitation, the call is **rejected** unless `--dangerously-disable-elicitation` is set ([BaseToolLoader.cs](https://github.com/microsoft/mcp/blob/main/core/Microsoft.Mcp.Core/src/Areas/Server/Commands/ToolLoading/BaseToolLoader.cs)) |
| Stripe | `stripe_api_search`, `stripe_api_details`, `stripe_api_read` (GET), `stripe_api_write` (POST/PATCH/PUT/DELETE), plus about 12 product tools ([docs](https://docs.stripe.com/mcp)) | Split by HTTP safety class | Not documented | Some `stripe_api_write` actions (refunds, outbound payments) need a human to approve at a URL. The agent then retries with an approval token; approvals expire after 24 hours ([docs](https://docs.stripe.com/mcp)) |
| Supabase | Per-operation tools in "feature groups", plus `read_only` and `project_ref` scoping via URL parameters ([README](https://github.com/supabase-community/supabase-mcp), [supabase.com/mcp](https://supabase.com/mcp)) | Not documented | Typed input and output schemas exported via `createToolSchemas()` | Cost confirmation for `create_project` / `create_branch` uses a form elicitation when the client supports it. Otherwise it falls back to `get_cost` → `confirm_cost` → `confirm_cost_id`. Supabase warns that hooks can auto-answer elicitations, so this is "a guardrail rather than proof that a person approved" ([supabase.com/mcp](https://supabase.com/mcp)) |
| Notion | 68 tools, mostly one per operation; a few multi-mode tools (`notion-fetch`, `notion-update-page`, `notion-query-data-sources`) ([docs](https://developers.notion.com/docs/mcp-supported-tools)) | Deletes marked `destructiveHint: true` | Not documented | `notion-delete-pages` / `notion-delete-databases` require `user_confirmed: true` ([docs](https://developers.notion.com/docs/mcp-supported-tools)) |
| Linear | Per-operation tools; `/mcp/readonly` endpoint "only ever exposes read tools", or a read-only OAuth scope ([docs](https://linear.app/docs/mcp)) | Not documented | Not documented | Not documented |
| Sentry | Per-operation tools grouped into "skills" (`?skills=inspect,triage`, `--disable-skills`); several search tools run an embedded LLM to translate natural language into Sentry query syntax ([README](https://github.com/getsentry/sentry-mcp)) | Not checked | Not checked | Not checked |
| AWS API server | Two tools, `call_aws` and `suggest_aws_commands`, over the whole CLI ([README](https://github.com/awslabs/mcp/blob/main/src/aws-api-mcp-server/README.md)) | Collapsed into one tool, so the client cannot separate reads | No | `READ_OPERATIONS_ONLY`, `REQUIRE_MUTATION_CONSENT` (elicitation for every non-read operation), and a policy file with `denyList` / `elicitList` ([README](https://github.com/awslabs/mcp/blob/main/src/aws-api-mcp-server/README.md)) |
| Cloudflare | Server-side code mode: `search()` and `execute()` run JavaScript in a V8 isolate against the OpenAPI spec, about 1,000 tokens for 2,500+ endpoints ([blog](https://blog.cloudflare.com/code-mode-mcp/)); original client-side code mode post ([2025-09-26](https://blog.cloudflare.com/code-mode)) | One `execute` tool for everything | No | Permissions come from OAuth scopes only. Neither post describes a confirmation step for writes |

Framework support (FastMCP, the stack social-kit will use):

- Since 3.0, `enable()` / `disable()` by name or tag ([visibility](https://gofastmcp.com/servers/visibility.md)).
- Since 3.1, `RegexSearchTransform`: `list_tools` returns only `search_tools` and a `call_tool` proxy, with `always_visible` pins ([tool search](https://gofastmcp.com/servers/transforms/tool-search.md)).
- An experimental `CodeMode` transform (`search`, `get_schema`, `execute`; default `max_tool_calls` 50 per `execute`) ([code mode](https://gofastmcp.com/servers/transforms/code-mode.md)).
- Both transforms route every call through one proxy tool, so the client sees one name and one set of annotations.

## 4. Spec facts relevant to consolidation

- **Annotations are per tool only.** `ToolAnnotations` has `title`, `readOnlyHint`, `destructiveHint` (default `true`, meaningful when not read-only), `idempotentHint` and `openWorldHint`. All are hints, and clients "MUST consider tool annotations to be untrusted unless they come from trusted servers" ([schema](https://modelcontextprotocol.io/specification/2026-07-28/schema), [tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)). Nothing is per argument or per enum value. The default matters: a write tool that omits `destructiveHint: false` counts as destructive.
- **`outputSchema` is per tool.** Since 2026-07-28 it may use any JSON Schema 2020-12 keyword, and `structuredContent` may be any JSON value ([SEP-2106](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2106), [changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)). A consolidated tool can declare a discriminated union, as GitHub does.
- **Tool lists must be stable per connection.** `tools/list` "MAY change over time … but MUST NOT vary per-connection or as a side effect of other requests on the connection"; it may vary by authorization ([tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), [SEP-2567](https://modelcontextprotocol.io/seps/2567-sessionless-mcp)). An `enable_toolset` tool that makes more tools appear is no longer permitted. Startup flags are fine. Servers SHOULD return tools in deterministic order, and list results carry `ttlMs` / `cacheScope` ([SEP-2549](https://modelcontextprotocol.io/seps/2549-TTL-for-list-results)).
- **Input validation errors are tool execution errors** (`isError: true`), which clients SHOULD pass to the model for self-correction ([tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), [SEP-1303](https://modelcontextprotocol.io/seps/1303-input-validation-errors-as-tool-execution-errors)). This is what makes "return the operation's schema on a bad call" work.
- **Tool names**: 1–128 characters, case-sensitive ([SEP-986](https://modelcontextprotocol.io/seps/986-specify-format-for-tool-names)).
- **No groups, namespaces, hierarchy or search in the protocol.**
  - SEP-1300 (groups and tags) was rejected and moved into a working group ([#1300](https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1300)).
  - SEP-993 (namespaces) was superseded by SEP-1300.
  - SEP-1821 (`tools/list` query), SEP-1881 (scope-filtered discovery) and SEP-1576 (token bloat) were closed in June 2026 without adoption.
  - The 2026 roadmap lists "progressive discovery" as a Core Primitives WG deliverable: "an experimental server-side discovery mechanism" ([roadmap](https://modelcontextprotocol.io/development/roadmap)). The Primitive Grouping IG became the Progressive Disclosure WG on 2026-10-13, co-led by GitHub's MCP maintainer, and aims at reference extensions, not a spec change yet ([charter](https://modelcontextprotocol.io/community/working-groups/progressive-disclosure), [PR #3376](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/3376)).
  - SEP-2793 (graded tool risk metadata such as `riskLevel` and `reversibility`) is an open draft without a sponsor ([PR #2793](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2793)).
- **The spec puts discovery and code mode on the client.** The official Client Best Practices page describes host-side progressive discovery and host-side code mode built from each tool's `outputSchema`. It requires that sandbox-originated calls get "the same human-in-the-loop confirmation policy" as direct calls ([client best practices](https://modelcontextprotocol.io/docs/2026-07-28/develop/clients/client-best-practices)). It also recommends a single stable `call_tool({name, args})` meta-tool, or appending after the cache breakpoint, to keep prompt caches warm.

## 5. Destructive-action confirmation in consolidated designs

How elicitation works now:

- In 2026-07-28, server-initiated `elicitation/create` became a Multi Round-Trip Request: the tool returns `resultType: "input_required"` and the client retries with `inputResponses` ([SEP-2322](https://modelcontextprotocol.io/seps/2322-MRTR), [changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).
- FastMCP supports `ctx.elicit()` on older connections and `InputRequiredResult` on 2026-07-28 connections. Neither works on the other era ([FastMCP elicitation](https://gofastmcp.com/servers/elicitation.md)). youtube-kit's ADR 0002 records the earlier FastMCP 4.1 refusal.

Client support:

- **Claude Code**: form and URL modes in interactive sessions only; in `-p` and Agent SDK runs it cancels the request; `Elicitation` hooks can auto-answer ([mcp docs](https://code.claude.com/docs/en/mcp)).
- **VS Code**: supported since 1.102 ([Azure troubleshooting](https://github.com/microsoft/mcp/blob/main/servers/Azure.Mcp.Server/TROUBLESHOOTING.md), [VS Code dev guide](https://code.visualstudio.com/api/extension-guides/ai/mcp)).
- **Cursor**: supported ([docs](https://cursor.com/docs/context/mcp)).
- **Claude Desktop**: no first-party statement. Open issues report no dialog for local stdio servers and dropped MRTR requests in Cowork ([claude-code#96043](https://github.com/anthropics/claude-code/issues/96043), [claude-ai-mcp#1046](https://github.com/anthropics/claude-ai-mcp/issues/1046), [claude-code#41110](https://github.com/anthropics/claude-code/issues/41110)).
- **Codex**: a run of issues about auto-declined or hanging elicitations ([codex#13405](https://github.com/openai/codex/issues/13405), [#45621](https://github.com/openai/codex/issues/45621), [#39149](https://github.com/openai/codex/issues/39149)).

Patterns in use:

- **Elicitation or nothing** (Azure): rejects destructive calls on clients without elicitation, so they would fail on Claude Desktop.
- **Elicitation with a token fallback** (Supabase), or a **token re-call only** (Stripe approval URL plus token; Notion `user_confirmed: true`; youtube-kit `confirm=<id>`). This works on every client. The binding to the target is what stops an agent from reusing one approval on another target.
- **Annotation-based approval in the client.** This only works if the destructive operation has its own tool. A per-noun tool that mixes `update` and `delete` must carry `destructiveHint: true` for every call.
- **Per-call approval inside code mode** is required by the MCP client guide. A server-side `execute` tool cannot give the client anything per call to approve.

## 6. What this means for social-kit

### Constraints that decide it

- **Caps.** 110 tools exceed Windsurf's 100 on their own and leave VS Code 18 slots for everything else. Even a single platform (~45) is a third of VS Code's budget.
- **Native search.** Claude Code, Codex, Cursor and the Claude apps defer tools, so upfront cost there is small at any count. Search works on names, descriptions and argument names, and Claude Code gives deferred tools 16,384 characters of description, so keyword-rich names and descriptions pay off.
- **Approval.** VS Code skips confirmation for `readOnlyHint` tools, Codex `writes` mode prompts only for non-read-only tools, and Claude Code allow rules match tool-name globs. Reads therefore need tools of their own. Destructive operations need tools of their own to carry `destructiveHint` without making every edit look destructive.
- **Typed output.** Clients that build code mode or types from `outputSchema` work best with precise per-tool output. A consolidated tool keeps this only with a `method`-discriminated union.
- **Live-write risk.** A burst of test posts already got @language_ranch suspended on Threads. Server-side code mode turns one approved `execute` into up to 50 writes (FastMCP's default cap), which is the wrong default for publishing.

### Ranked recommendation

**1. Platform + noun, split by safety class (recommended, about 25-30 tools).** This is the GitHub/Azure shape adapted to the existing `ig_post_create` naming.

- Shape:
  - `ig_post_read` with `method` values `list`, `get`, `insights` and so on.
  - `ig_post_write` with `create`, `update`, `publish`, …
  - One guarded `ig_delete` per platform, taking `kind`, `id` and `confirm`, with `destructiveHint: true` and the youtube-kit confirm protocol.
- Indicative per-platform set:
  - Instagram: account, post, comment, message, explore (hashtags, discovery, mentions) × read/write, plus delete. About 10.
  - Facebook: about 10-11.
  - Threads: about 6-7.
  - The exact nouns should be cut from the tiered surface list.
- Pros: under every cap even beside other servers, and inside Anthropic's 30–50 comfort band. Annotations stay exact, so VS Code and Codex auto-approve reads, Claude Code users can allow `mcp__skit__*_read`, and the Claude apps' read/write categories line up. Each tool covers 3-8 methods, so parameters can stay flat and named (GitHub's "required for method X" style). A `method`-discriminated `outputSchema` keeps typed results.
- Cons: still dozens of tools in Gemini CLI and Windsurf. Method-specific parameters are not enforced by the schema, so validation errors must return the method's own parameter list (supported by SEP-1303 semantics). The model needs one extra decision (`method`). The CLI surface stays per operation, so adapters map `skit ig post list` to `ig_post_read(method="list")`.
- Add-ons:
  - `--platform` filtering at startup, since most users run one platform. Toolsets by platform are what GitHub, Supabase and Sentry ship.
  - `--read-only`, as GitHub, Supabase, Linear, Azure and AWS all ship.
  - Pin 3-5 tier-1 tools with `anthropic/alwaysLoad`.
  - Write server instructions under 4,096 characters that name the platforms and nouns, for search-based clients.

**2. Platform × safety class (about 9-12 tools).** `ig_read`, `ig_write`, `ig_delete` plus an `ig_describe` (or `skit_describe`), each taking an `operation` enum and an `args` object. This is Stripe's `stripe_api_read` / `stripe_api_write` / `search` / `details`.

- Pros: smallest surface that keeps class-level annotations and approval globs, and it fits every client.
- Cons:
  - 15-25 operations per tool force an untyped `args` object, or a very large `oneOf` whose support across clients and models is not verified here.
  - `outputSchema` degrades to a generic shape.
  - Signatures in the description risk Claude Code's 4,096-character cut whenever the tool is not deferred.
  - Most calls need a describe round trip or an error round trip first.
- Pick this if the hard target is about 10 tools.

**3. Status quo, one tool per operation, with `--platform` / `--tier` / `--read-only` filters.** This is the best shape for clients with native search and code mode: exact annotations, exact `outputSchema`, most searchable. It is Notion's and Supabase's choice. But the default set breaks Windsurf, crowds VS Code and loads everything in Gemini CLI. It is only acceptable if a default such as tier 1 on one platform stays well under ~40.

**Not recommended**

- **Server-side search/describe/run (~3 tools).** GitHub built and removed exactly this. Client tool search finds nothing to search when only three meta-tools exist. A single `run` must be marked destructive, so every read prompts. `enable_toolset`-style list mutation now violates the spec. FastMCP's `RegexSearchTransform` has the same single-proxy approval problem.
- **Server-side code mode.** It needs a sandbox in a local Python CLI (FastMCP's `CodeMode` is experimental), collapses per-call approval into one `execute`, and multiplies live writes. social-kit's workloads are small reads and deliberate single writes, not large intermediate data. Clients that want code mode (Codex, Anthropic programmatic tool calling, MCP hosts per the client guide) build it from well-typed tools, which option 1 or 3 provides.

### Contradictions with the options on the table

- **"One tool per platform+noun with an `action` param (~30)"** only keeps approval granularity if reads, writes and deletes are split. Splitting by safety class is what lands at ~25-30. A single mixed per-noun tool is the design GitHub's maintainer warned against.
- **"Discovery/meta-tools"** and **dynamic toolsets via `tools/list_changed`**:
  - The 2026-07-28 spec forbids lists that change as a side effect of a call.
  - GitHub removed its dynamic toolsets on 2026-05-20.
  - The protocol has no search primitive; SEP-1821 and SEP-1300 were not adopted.
  - Discovery now belongs to clients: Claude Code and Codex defer by default, the Claude apps' Auto mode searches, Cursor uses files, VS Code uses virtual tools.
- **Code mode** is framed by the MCP docs as a host feature. A server helps it most by shipping granular, typed tools, which pushes away from heavy consolidation.
- **"Full schema returned on validation error"** is sound and spec-backed (tool execution errors). The weak part is the untyped `args` object, not the error path.
- **Elicitation-based delete confirmation** is still not dependable: there is no Claude Desktop support, Claude Code serves it only in interactive sessions, and the transport moved to MRTR. Keep `confirm=<id>` as the primary path. Elicitation could later be added as a bonus where supported, the Supabase pattern, without changing the contract.

## Not verified / open

- No controlled measurement of consolidated vs. per-operation tools exists in primary sources. If it matters, run social-kit's own eval (Anthropic's writing-tools post describes the method).
- How well JSON Schema `oneOf`/discriminators in `inputSchema` work across clients and models was not tested.
- Whether the Claude apps' read-only and write/delete categories come from `readOnlyHint` / `destructiveHint` is not stated by Anthropic.
- Cursor's current tool cap is undocumented. The 40-tool figure is forum lore.
- Gemini CLI and Windsurf behaviour on `list_changed` and elicitation is undocumented.
