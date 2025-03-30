"""
Setup:

    uv pip install mcp-openapi httpx-sse

    export OPENAI_API_KEY=<your-openai-api-key>

Put this in your `servers.yaml` file:

```
servers:
- namespace: httpbin
    name: httpbin
    url: file://test-specs/httpbin.yaml
    base_url: https://httpbin.org
    paths:
    - /get
    - /status
    - /ip
    - /headers
    - /user-agent

- namespace: weather
    name: Open Meteo API
    url: https://raw.githubusercontent.com/open-meteo/open-meteo/refs/heads/main/openapi.yml
    base_url: https://api.open-meteo.com
    # Forward the API key from the client's query parameters
    paths:
    - /v1/forecast$
    # Forward the Authorization header to the OpenAPI endpoint.
    headers:
        - Authorization
```

Run the server (if not already running):

    uv run main.py

Finally, run the example:

    uv run examples/low_level_client.py
"""

import asyncio
import logging
from dataclasses import dataclass

from mcp import ClientSession, types
from mcp.client.sse import sse_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_sampling_message(
    message: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    """Handle sampling messages from the server."""
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text="Hello, world! from model",
        ),
        model="gpt-4o-mini",
        stopReason="endTurn",
    )


@dataclass
class FakeUseContext:
    weather_auth_header: str


async def run_agent(context: FakeUseContext):
    # Configure SSE client with custom headers
    async with sse_client(
        "http://localhost:8000/weather/sse",
        headers={
            "Authorization": context.weather_auth_header,
        },
    ) as (read, write):
        async with ClientSession(
            read, write, sampling_callback=handle_sampling_message
        ) as session:
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            logger.info("Available tools: %s", tools)

            # Call the weather forecast tool
            try:
                result = await session.call_tool(
                    "weather/v1/forecast",
                    arguments={
                        "latitude": 52.52,
                        "longitude": 13.41,
                        "hourly": ["temperature_2m", "relative_humidity_2m"],
                    },
                )
                logger.info("Weather forecast result: %s", result)
            except Exception as e:
                logger.error("Error calling weather tool: %s", e)

            # Call an httpbin tool
            try:
                result = await session.call_tool(
                    "httpbin/get",
                    arguments={"name": "test"},
                )
                logger.info("Httpbin result: %s", result)
            except Exception as e:
                logger.error("Error calling httpbin tool: %s", e)


if __name__ == "__main__":
    ctx = FakeUseContext(weather_auth_header="Test Authorization Header")
    asyncio.run(run_agent(ctx))
