# MCP OpenAPI Server

Run an MCP server which creates tools for a subset of API endpoints based on OpenAPI routes.

Supports:

- JSON and YAML local or remote OpenAPI schemas.
- Exposing a subset of routes based on regular expressions.
- Providing strictly typed arguments to tools based on the schemas.

## Quick Start

Install the necessary dependencies using [uv](https://github.com/astral-sh/uv).

```bash
uv sync
```

Define your servers following the structure of `services.yaml.example`:

```
servers:
  - namespace: httpbin
    name: httpbin
    url: file://apis/httpbin.yaml
    base_url: https://httpbin.org/
    paths:
      - /get
      - /status
      - /ip
      - /headers

  - namespace: zendesk
    name: Zendesk API
    url: file://apis/zendesk-oas.yaml
    base_url: https://api.zendesk.com
    paths:
      - /api/v2/tickets
      - /api/v2/users
```

* You can point to either a remote URL or local file (using `file://`).
* In `paths` you define Regular Expressions which will match the paths you want to expose.

Then you can run your server to expose it:

```bash
uv run main.py
```