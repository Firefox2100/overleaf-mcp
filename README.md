# Overleaf MCP Bridge

MCP bridge for Overleaf that uses its web API directly. Targets self-hosted [Overleaf Community Edition](https://github.com/overleaf/overleaf); future plans including supporting [CEP](https://github.com/yu-i-i/overleaf-cep)-only features. Not guaranteed to work with the official Overleaf SaaS or Server Pro, as the author has no paid account to verify against.

## Install

### From Source Code

This project is a Python package, requiring Python 3.12 or newer. Install it with `uv`:

```bash
git clone https://github.com/Firefox2100/overleaf-mcp.git
cd overleaf-mcp
uv sync
```

## Configuration

Settings are read from the enviornment, in this order of precedence:

- environment variables in the shell
- an `.env` file (or the file named by `OMCP_ENV_FILE`)
- Docker secrets under `/run/secrets`

| Setting             | Env var                 | Docker secret file         | Required | Default                    |
|----------------------|--------------------------|-----------------------------|----------|-----------------------------|
| Overleaf account email | `OMCP_OVERLEAF_EMAIL`    | `omcp_overleaf_email`       | yes      | —                           |
| Overleaf account password | `OMCP_OVERLEAF_PASSWORD` | `omcp_overleaf_password`    | yes      | —                           |
| Overleaf base URL    | `OMCP_OVERLEAF_BASE_URL` | `omcp_overleaf_base_url`    | no       | `https://www.overleaf.com` |

Example `.env`:

```
OMCP_OVERLEAF_BASE_URL=https://overleaf.example.com
OMCP_OVERLEAF_EMAIL=service@example.com
OMCP_OVERLEAF_PASSWORD=...
```

The account used should have its own credentials and only the access it needs — this bridge logs in as that account and acts with its permissions. Giving it a personal account with full access to all projects, or admin access, is not recommended as the MCP client would be able to perform much more destructive actions than perhaps intended.

## Running

```bash
uv run overleaf-mcp
```

This speaks MCP over stdio, so it's meant to be launched by an MCP client (not run standalone). On startup it logs in to Overleaf immediately and fails fast if that doesn't work — nothing is served on a broken session. After a successful login, the environment variables for email and password are not needed, and can be removed for the next run. The bridge will keep using the same session when possible.

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
