# Overleaf MCP Bridge

MCP bridge for Overleaf that uses its web API directly. Targets self-hosted [Overleaf Community Edition](https://github.com/overleaf/overleaf) and [CEP](https://github.com/yu-i-i/overleaf-cep)-only features. Not guaranteed to work with the official Overleaf SaaS or Server Pro, as the author has no paid account to verify against.

## Install

### From Source Code

This project is a Python package, requiring Python 3.12 or newer. Install it with `uv`:

```bash
git clone https://github.com/Firefox2100/overleaf-mcp.git
cd overleaf-mcp
uv sync
```

### From a Container Image

A prebuilt image is published to GitHub Container Registry on every push to `main`:

```bash
docker pull ghcr.io/firefox2100/overleaf-mcp:latest
```

Or with Compose, using the provided `compose.yaml` (defaults to streamable HTTP on port 8000):

```bash
cp example.env .env
docker compose up -d
```

Set the environment variables in the `.env` file before starting. See [Configuration](#configuration) below.

## Configuration

Settings are read from the enviornment, in this order of precedence:

- environment variables in the shell
- an `.env` file (or the file named by `OMCP_ENV_FILE`)
- Docker secrets under `/run/secrets`

| Setting                   | Env var                  | Docker secret file       | Required | Default                    |
|---------------------------|--------------------------|--------------------------|----------|----------------------------|
| Overleaf account email    | `OMCP_OVERLEAF_EMAIL`    | `omcp_overleaf_email`    | yes      | —                          |
| Overleaf account password | `OMCP_OVERLEAF_PASSWORD` | `omcp_overleaf_password` | yes      | —                          |
| Overleaf base URL         | `OMCP_OVERLEAF_BASE_URL` | `omcp_overleaf_base_url` | no       | `https://www.overleaf.com` |

Example `.env`:

```
OMCP_OVERLEAF_BASE_URL=https://overleaf.example.com
OMCP_OVERLEAF_EMAIL=service@example.com
OMCP_OVERLEAF_PASSWORD=...
```

The account used should have its own credentials and only the access it needs — this bridge logs in as that account and acts with its permissions. Giving it a personal account with full access to all projects, or admin access, is not recommended as the MCP client would be able to perform much more destructive actions than perhaps intended.

## Running

### stdio

```bash
uv run overleaf-mcp
```

Equivalently, as a module: `uv run python -m overleaf_mcp`.

By default, this speaks MCP over stdio, so it's meant to be launched by an MCP client (not run standalone). On startup, it logs in to Overleaf immediately and fails fast if that doesn't work — nothing is served on a broken session. After a successful login, the environment variables for email and password are not needed, and can be removed for the next run. The bridge will keep using the same session when possible.

To wire it into an MCP client, point the client at the `overleaf-mcp` command with the environment variables set, e.g. for a client that reads a JSON config with a `mcpServers` map:

```json
{
  "mcpServers": {
    "overleaf": {
      "command": "overleaf-mcp",
      "env": {
        "OMCP_OVERLEAF_BASE_URL": "https://overleaf.example.com",
        "OMCP_OVERLEAF_EMAIL": "service@example.com",
        "OMCP_OVERLEAF_PASSWORD": "..."
      }
    }
  }
}
```

If `overleaf-mcp` isn't on the client's `PATH`, point `command` at `uv --directory /path/to/overleaf-mcp run overleaf-mcp` instead.

### Streamable HTTP

Pass `--http` to serve over streamable HTTP instead of stdio — useful when running the bridge as a standalone service (e.g. in a container) or with other proxy clients like LiteLLM rather than spawning it per-client:

```bash
uv run overleaf-mcp --http --host 0.0.0.0 --port 8000
```

`--host` and `--port` are ignored for the default stdio transport. Point an HTTP-capable MCP client at `http://<host>:<port>/mcp`.

## Tools

Tools are grouped into namespaces, each mounted as its own set of `<namespace>_<tool>` MCP tools. A namespace with [CEP](https://github.com/yu-i-i/overleaf-cep)-specific tools is only mounted when the connected server is probed at startup and found to actually support that feature — a plain Overleaf CE server never exposes it, so clients don't need to know or care which kind of server they're talking to.

| Namespace  | Always mounted                                | Purpose                                                                                                                                                       |
|------------|-----------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `project`  | yes                                           | List, fetch, create, delete, and clone projects; download a project as a zip; list collaborators.                                                             |
| `file`     | yes                                           | Read, list, create, rename, move, overwrite, patch, and delete files; create/refresh linked files (e.g. imported from a URL, or Zotero-linked `.bib` on CEP). |
| `compile`  | yes                                           | Trigger a compile (draft or full), fetch compile logs/errors, download an output file, and get a word count.                                                  |
| `editing`  | yes                                           | Search across a project or within a file (plain or regex), outline a file's structure, and read a specific line range.                                        |
| `config`   | yes                                           | Read/update project config: compiler, root document, main bibliography, spell-check language, and (on CEP) the sandboxed-compile TeX Live image.              |
| `citation` | yes                                           | List `.bib` files and their entries, look up a citation key, find where it's used, and check for broken/duplicate citations.                                  |
| `history`  | yes                                           | List project history, diff a file between versions, restore a file to a prior version, and manage history labels.                                             |
| `review`   | only if the server supports review mode (CEP) | Track changes (enable/disable, tracked edits, accept/reject) and comment threads (create, reply, resolve, reopen, delete).                                    |
| `github`   | only if `githubSyncEnabled` (CEP)             | Read GitHub sync state and trigger a sync. Linking/unlinking a repository stays a web-UI action, out of scope here.                                           |
| `pandoc`   | only if `enablePandocConversions` (CEP)       | Export a whole project to `.docx`/Markdown/HTML, and import a `.docx`/`.md` file into a project.                                                              |

Every tool operates on an already-authenticated session established at startup — there is no per-call login, and no tool exposes credentials or session details to the client.

Each tool's docstring documents its own parameters and behavior in detail. For the concepts that span multiple tools — the `project_id`/path conventions, read-before-write safety, and typical multi-step workflows (editing, compiling, citations, review, history) — see [`skill/SKILL.md`](skill/SKILL.md). It's written as a portable [Claude skill](https://www.anthropic.com/news/skills): drop the `skill` folder into an MCP client's skills directory (e.g. `.claude/skills/overleaf-mcp` for Claude Code) to give it that context automatically.
