# MCP OpenAPI Scripts

## `make-mcp`

This script can be used to generate one-off MCP servers (rather than having this all generated dynamically).

You can create either with a URL to a spec file or a file.

** Create for HTTPBin /get**

```bash
uv run scripts/make-mcp -f test-specs/httpbin.yaml \
    -n "HTTPBin.org" \
    -r httpbin \
    -b https://httpbin.org/ \
    --routes /get --routes /ip
```

**Create for NASA Picture of the Data**

```
uv run scripts/make-mcp \
    -u https://raw.githubusercontent.com/APIs-guru/openapi-directory/refs/heads/main/APIs/nasa.gov/apod/1.0.0/openapi.yaml \
    -n "NASA Astronomy Picture of the Day" \
    -r nasapod -b https://api.nasa.gov/planetary \
    --routes /apod
```
