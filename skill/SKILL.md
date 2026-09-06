---
name: overleaf-mcp
description: Use the overleaf-mcp MCP server to work with an Overleaf project — read, search, and edit LaTeX documents, compile and check errors, manage citations, review/track changes, and inspect history. Use whenever a task involves an Overleaf project through the `project`/`file`/`compile`/`editing`/`config`/`citation`/`history`/`review`/`github`/`pandoc` MCP tools, or when the user mentions Overleaf, a `.tex`/`.bib` document living on Overleaf, or a project id that looks like a Mongo ObjectId in that context.
---

# Overleaf MCP bridge

This skill explains how to use the `overleaf-mcp` MCP server well — the concepts that don't fit
in any single tool's docstring, and the order operations usually need to happen in. Each tool's
own docstring (visible in your tool list) is the source of truth for its exact parameters and
behavior; this document is the map that ties them together.

## What this server is

`overleaf-mcp` is a bridge between an MCP client (you) and one Overleaf account, authenticated
once at server startup. It talks to Overleaf's internal web API — the same one the Overleaf web
editor uses — not a public REST API. Every tool call acts as that one account, synchronously,
against the live project state. There is no local cache: a `file_read_file` immediately after a
`file_overwrite_file` sees the new content, and two agents (or an agent and a human) editing the
same project concurrently will race exactly like two browser tabs would.

Tools are namespaced (`project_*`, `file_*`, `compile_*`, `editing_*`, `config_*`, `citation_*`,
`history_*`, and conditionally `review_*`, `github_*`, `pandoc_*`). The namespace prefix on a
tool's name tells you which of these concept groups it belongs to.

## Core concepts

**`project_id` is the anchor for almost everything.** Call `project_list_projects` first to
discover it — never guess or infer one from a URL or a past conversation, since projects can be
renamed, deleted, or inaccessible. Nearly every other tool takes `project_id` as its first
argument.

**Paths are always project-relative, never absolute.** `"chapters/intro.tex"`, not
`/chapters/intro.tex` or a full URL. The project root is `""` (empty string), not `"/"`. This
applies uniformly across `file_*`, `editing_*`, `config_*`, `citation_*`, and `history_*` tools.

**Only text documents are readable/writable as text.** `.tex`, `.bib`, and other plain-text files
work with `file_read_file`, `file_overwrite_file`, `file_patch_file`, etc. Binary files (images,
PDFs) are opaque to these tools — they can be listed (`file_list_files`) and linked
(`file_create_linked_file`) but not read or patched as text.

**Read before you write.** This is a live, multi-writer system, so a stale in-context copy of a
document is a real risk, not a hypothetical one:
- `file_patch_file` and `review_patch_file_tracked` require their `find` text to match **exactly
  once** in the document's *current* content. If it doesn't (because the doc changed, or your
  copy was never accurate), the call raises instead of guessing — re-read the document and adjust.
- `file_overwrite_file` and `review_overwrite_file_tracked` replace the whole document. Overleaf
  verifies the write landed as intended and raises if a concurrent edit interfered, rather than
  silently dropping either version — but by then the document may already contain a mixed-in
  result, so re-read it before trying again.
- Prefer `file_patch_file` over `file_overwrite_file` for small, targeted edits — it's cheaper to
  get right and easier to verify than regenerating an entire document's content.

**Conditionally-mounted namespaces mean conditionally-real features.** `review_*` (track
changes/comments), `github_*` (GitHub sync), and `pandoc_*` (docx/markdown import-export) only
appear in your tool list when the connected server actually supports them (this is a CE-vs-CEP
distinction the server detects at startup, not something you can toggle). If one of these tools
isn't available to you, don't assume it exists on a different call path or ask the user to enable
it via some tool parameter — it simply isn't there for this server, and the equivalent action (if
any) has to happen through Overleaf's own web UI instead.

## Typical workflows

**Get oriented in a project**
1. `project_list_projects` → pick a `project_id`.
2. `file_list_files` (repeat per folder, or start at `path=""` for the root) to see the tree, or
   `editing_search_project` if you already know what you're looking for.
3. `config_get_project_config` to see the compiler, root document, and bibliography — useful
   context before editing, and often the actual cause when a compile fails with something like
   "no main file specified".

**Read and understand a document**
- `editing_get_outline` for a structural view (sections/subsections) before deciding where to
  look in detail.
- `editing_read_lines` for a numbered range once you know roughly where to look; `file_read_file`
  with `offset`/`limit` as an alternative when you don't need line numbers.
- `editing_search_file` / `editing_search_project` to locate something by content across one file
  or the whole project (Overleaf itself has no server-side search, so this fetches and searches
  documents locally — expect it to be slower on large projects).

**Make an edit**
1. Read the current content first (see above).
2. Use `file_patch_file` for a small, exact-text change, or `file_overwrite_file` when replacing
   the whole document is genuinely simpler than patching it piece by piece.
3. If the project has track changes semantics you need to respect (a shared/reviewed document),
   use the `review_*` equivalents (`review_patch_file_tracked`,
   `review_overwrite_file_tracked`) instead — they record the edit as a pending, attributed
   suggestion rather than applying it outright, regardless of whether track changes is currently
   toggled on. `review_set_track_changes` toggles the project-wide setting for edits made in the
   Overleaf UI directly; it does not gate whether the tracked-edit tools work.

**Compile and check the result**
1. `compile_project` (set `draft=True` for a faster, lower-fidelity pass while iterating).
2. Use the returned build id with `compile_get_compile_errors` for a parsed error list, or
   `compile_get_compile_log` for the raw log (includes warnings the parsed view omits).
3. `compile_get_output_file` downloads the PDF to a local path — it's not returned inline, since
   raw PDF bytes aren't something a model can usefully read.
4. If a compile fails outright rather than producing errors, suspect `config_*` first (wrong
   compiler, missing root document) before assuming the document content is broken.

**Work with citations**
- `citation_check_citations` first — it cross-references every `\cite`-family command against
  every `.bib` entry in one pass and flags both undefined keys (compile-time "?" marks) and
  unused entries, which is usually faster than manually reconciling `citation_list_citations`
  against `citation_find_citation_usage`.
- `citation_find_citation_usage` when you need to see *where* a specific key is used (e.g. before
  renaming or removing it).

**Recover or inspect history**
- `history_list_history` is paginated oldest-excluded/most-recent-first; pass a previous page's
  `next_before_timestamp` as `before` to page backward.
- `history_get_diff` and `history_restore_file` both take version numbers from a history page's
  `from_v`/`to_v` — fetch the page first, don't guess a version number.
- `history_restore_file` is non-destructive: it adds the restored content as a new, separately
  named file rather than overwriting the current one. Follow it with `file_overwrite_file` if the
  intent was to actually revert the current file.
- `history_create_label` before a risky multi-step edit gives you a named checkpoint to compare
  against or restore from later.

**Review mode, if available (`review_*`)**
- Track-changes edits (`review_overwrite_file_tracked`/`review_patch_file_tracked`) and comment
  threads (`review_create_comment`, `review_reply_comment`, `review_resolve_comment`, …) are
  independent features sharing this namespace — a project can have comments without track changes
  being on, or vice versa.
- Both `review_create_comment` and `review_patch_file_tracked` anchor to exact, unique text via a
  `find` parameter, same constraint as `file_patch_file`.
- `review_list_tracked_changes` / `review_list_comments` before accepting, rejecting, resolving,
  or reopening anything — you need real ids from a current listing, not ones from an earlier
  conversation turn, since ids for these are per-thread/per-change and won't survive being
  guessed at.

**GitHub sync, if available (`github_*`)**
- `github_get_sync_state` first. A `merge_status` of `"need-export"` means the project isn't
  linked to a repo at all — linking/unlinking only happens from Overleaf's web UI, this bridge
  only triggers syncs on a project that's already linked.
- `github_trigger_sync` pulls, merges, and pushes in one step; there's no separate pull-only or
  push-only action.

**Pandoc import/export, if available (`pandoc_*`)**
- `pandoc_import_file` is the general-purpose way to add any file to a project — prefer it over
  `file_create_file`/`file_create_linked_file` when it's available, since it converts `.docx`/`.md`
  to Overleaf-native content automatically (anything else is added as-is).
- `pandoc_export_project` converts the whole project to one of `docx`/`markdown`/`html` and saves
  it locally, the same download-to-disk pattern as `compile_get_output_file`.

## Working with the account safely

The account this bridge logs in as should be scoped to only what it needs — treat every write
tool as something that really executes against the live project, with real collaborators
potentially watching it happen in their browser in real time. There's no dry-run mode: test an
uncertain `find`/`replace` pattern by reading the surrounding content first rather than by trying
the edit and hoping it raises cleanly on a bad match.
