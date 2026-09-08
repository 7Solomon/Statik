# statik-mcp

Statik as MCP tools, so an agent can build, draw, check and solve structural
systems.

The agent reads the drawing itself -- there is no detector in this path. These
tools are the workbench: write the system down, draw it back, see whether it
matches, see whether it can be solved, solve it.

## Install

Needs Python 3.10+ and a running Statik instance.

```bash
cd mcp
uv sync                     # or: python -m venv .venv && .venv/bin/pip install -e .
```

## Configure

| Variable | Meaning | Default |
|---|---|---|
| `STATIK_URL` | Base URL of the Statik instance | `http://localhost` |
| `STATIK_TOKEN` | Sent as `Authorization: Bearer ...` if set | unset |

`STATIK_TOKEN` is wired up in advance of the backend checking it -- see the
auth note in `docs/agent-integration-plan.md`.

### Claude Code

```bash
claude mcp add statik --env STATIK_URL=https://statik.7solomon.duckdns.org \
  -- uv --directory /home/johannes/Dokumente/server/Statik/mcp run statik-mcp
```

### Claude Desktop / any client with a JSON config

```json
{
  "mcpServers": {
    "statik": {
      "command": "uv",
      "args": ["--directory", "/home/johannes/Dokumente/server/Statik/mcp",
               "run", "statik-mcp"],
      "env": { "STATIK_URL": "https://statik.7solomon.duckdns.org" }
    }
  }
}
```

Without `uv`, point `command` at the venv's Python and use
`["-m", "statik_mcp.server"]`.

## Tools

| Tool | Does |
|---|---|
| `statik_conventions` | Every keyword, the sign conventions, a worked example |
| `statik_examples` | Stored systems in compact form, as worked examples |
| `statik_list_systems` | What is stored, with URLs |
| `statik_build_system` | Write a system down; returns a slug and a URL |
| `statik_get_system` | Read one back |
| `statik_update_system` | Replace whole sections of one |
| `statik_render` | **PNG back to the agent** -- the only check on whether it read the drawing right |
| `statik_validate` | Kinematic DOF; `dof > 0` means unsolvable |
| `statik_analyze` | `solution` / `simplify` / `dynamics` |

Resources: `statik://conventions`, `statik://examples`.

## The loop

```
build_system -> render -> compare with the source -> update_system
             -> validate (dof == 0?) -> analyze
```

`render` is not optional. Nothing else in this path ever looked at the original
drawing.

## Notes for maintenance

* Written against **mcp 2.x**, where `FastMCP` was renamed to `MCPServer`.
  Code written for 1.x (`from mcp.server.fastmcp import FastMCP`) will not
  import.
* Failures must be raised as `ToolError`. Any other exception has its message
  replaced by a generic one before it reaches the model, which would throw away
  the backend's error text -- and that text is the useful part: it names the
  unknown keyword and lists the valid ones.
* No structural logic lives here. Every tool is one call to `/api/agent/*`, so
  the editor's web UI and an agent can never drift apart. Anything that needs
  mechanics belongs in `backend/src/plugins/agent/`.
