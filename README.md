# MCP-OpenAPI Server

A server that exposes multiple OpenAPI endpoints as tools via the [Model Context Protocol (MCP)](https://www.anthropic.com/news/model-context-protocol), allowing hosted AI agents to interact with your APIs in a standardized way.

The MCP-OpenAPI Server provides a bridge between AI agents and your existing APIs by exposing OpenAPI-defined endpoints through the Model Context Protocol. This allows AI agents to discover and use your APIs with properly typed arguments and responses.

## Key Features

- **SSE Transport**: This server leverages the SSE transport for MCP so it works well for multiple agent clients.
  - Each OpenAPI server is available at a separate route `<host>/<namespace>/sse` (e.g., `https://my-mcp-server/stripe/sse`).
- **Authentication forwarding**: Share the same MCP tools across multiple users by forwarding the appropriate authorization headers and/or query parameters.
  - See the [client examples below](#access-from-mcp-clients) for how to configure this.
- **Selective Route Exposure**: Expose only specific routes based on regular expression
- **Type Safety**: Tools are generated with typed arguments on schemas - supporting both JSON body and query parameters - to ensure agents have enough context to make the correct call.

## Running

### Start the Server

Define your servers following the structure in `servers.yaml`:

```
servers:
  - namespace: stripe
    # Define headers to forward to the server
    headers:
      - Authorization
    # This is the name as it appears to the LLM
    name: Stripe API
    url: https://raw.githubusercontent.com/stripe/openapi/refs/heads/master/openapi/spec3.yaml
    base_url: https://api.stripe.com
    # Select which API paths to expose over MCP
    paths:
      - /v1/customers$

  - namespace: weather
    name: OpenWeatherMap API
    url: https://gist.githubusercontent.com/mor10/6fb15f2270f8ac1d8b99aa66f9b63410/raw/0e2c4ed43eb4c126ec2284bc7c069de488b53d99/openweatherAPI.json
    base_url: https://api.openweathermap.org/data/2.5
    # Forward the API key from the client's query parameters
    query_params:
      - appid
    paths:
      - /data/2.5/weather

  - namespace: httpbin
    name: httpbin
    # You can also point to a local spec file
    url: file://test-specs/httpbin.yaml
    base_url: https://httpbin.org
    paths:
      - /get
      - /status
      - /ip
      - /headers
      - /user-agent

```

_⚠️ Note: For large (multi-megabyte) OpenAPI specs you might find the initial cold start slow as it processes the whole file. To mitigate this you can use the `slim-openapi` script described below⚠️_

Then you can run your server:

**Locally (requires [uv](https://github.com/astral-sh/uv))**

```bash
uv sync
uv run main.py
```

**Via Docker**

```bash
docker build -t mcp-openapi .
docker run -p 8000:8000 -v $(pwd)/servers.yaml:/app/servers.yaml mcp-openapi
```

The `-v` flag mounts your local `servers.yaml` file into the container. You can also use environment variables to configure the service:

- `PORT`: The port to run the server on (default: 8000)
- `CONFIG`: Path to the servers configuration file (default: servers.yaml)

Example with environment variables:

```bash
docker run -p 8000:8000 \
  -v $(pwd)/servers.yaml:/app/servers.yaml \
  -e PORT=8000 \
  -e CONFIG=servers.yaml \
  mcp-openapi
```

### Access from MCP clients

The project includes two example clients that demonstrate different ways to interact with the MCP-OpenAPI server. Both examples use the same server configuration and demonstrate header forwarding for authentication. The low-level client is particularly useful for custom integrations or when you need more direct control over the MCP client.

- **[Low-Level Client](client-examples/low_level_client.py))**: This example demonstrates direct usage of the MCP client with SSE transport using the low level client.
- **[LangChain Integration](client-examples/langchain_client.py)**: This example shows how to integrate the MCP-OpenAPI server with LangChain (using the [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters)), allowing AI agents to use these APIs through LangChain's tool system.

## Tool Inspection

Alongside the MCP servers, the server exposes a couple HTTP endpoints for inspection of the available tools.

- `/tools/` and `/tools/{namespace}` will show the tools and parameters they have exposed.

```bash
curl -s localhost:8000/tools | jq '.'
{
  "httpbin": [
    {
      "name": "get_ip",
      "description": "Returns origin IP",
      "parameters": []
    },
    {
      "name": "get_headers",
      "description": "Returns headers",
      "parameters": []
    },
    {
      "name": "get_user_agent",
      "description": "Returns user-agent",
      "parameters": []
    },
    ...
  ],
  "stripe": [
    {
      "name": "get_customers",
      "description": "List all customers",
      "parameters": [
        {
          "name": "test_clock",
          "type": "str",
          "default": "None",
          "description": "Provides a list of customers that are associated with the specified test clock. The response will not include customers with test clocks if this parameter is not set."
        },
        {
          "name": "starting_after",
          "type": "str",
          "default": "None",
          "description": "A cursor for use in pagination. `starting_after` is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, ending with `obj_foo`, your subsequent call can include `starting_after=obj_foo` in order to fetch the next page of the list."
        },
        {
          "name": "limit",
          "type": "int",
          "default": "None",
          "description": "A limit on the number of objects to be returned. Limit can range between 1 and 100, and the default is 10."
        },
        {
          "name": "expand",
          "type": "str",
          "default": "None",
          "description": "Specifies which fields in the response should be expanded."
        },
        {
          "name": "ending_before",
          "type": "str",
          "default": "None",
          "description": "A cursor for use in pagination. `ending_before` is an object ID that defines your place in the list. For instance, if you make a list request and receive 100 objects, starting with `obj_bar`, your subsequent call can include `ending_before=obj_bar` in order to fetch the previous page of the list."
        },
        {
          "name": "email",
          "type": "str",
          "default": "None",
          "description": "A case-sensitive filter on the list based on the customer's `email` field. The value must be a string."
        },
        {
          "name": "created",
          "type": "str",
          "default": "None",
          "description": "Only return customers that were created during the given date interval."
        }
      ]
    },
    ...
  ]
}
```

The MCP inspector is also useful for seeing what's available.

![mcp-inspector](images/mcp-inspector-httpbin.png)

## Slimming down large spec files with `slim-openapi`

For large (multi-megabyte) OpenAPI specs you might find the initial cold start slow as it processes the whole file.

Some SaaS tools (e.g. Stripe, Zendesk) have multi-megabyte spec YAML files which are processed somewhat inefficiently today. Using the `slim-openapi` tool you can shorten these to just the spec needed for your routes. All references will be resolved appropriately so it can still parse.

```bash
uv run scripts/slim-openapi \
    -u https://raw.githubusercontent.com/stripe/openapi/refs/heads/master/openapi/spec3.yaml \
    --routes "/v1/customers$" \
    -o stripe-slim.yaml
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project uses [aiopenapi3](https://github.com/commonism/aiopenapi3) for OpenAPI specification parsing and validation. Many thanks to the maintainers and contributors of that project for their excellent work.
