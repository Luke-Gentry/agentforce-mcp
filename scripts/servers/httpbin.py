from mcp.server.fastmcp import FastMCP, Context
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import AsyncIterator
from pydantic import Field
import httpx

APP_NAME = "HTTP Bin"
APP_ROUTE = "httpbin"


@dataclass
class AppContext:
    base_url: str


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    base_url = "https://httpbin.org/"
    try:
        yield AppContext(base_url=base_url)
    finally:
        pass


mcp = FastMCP(
    APP_NAME,
    lifespan=app_lifespan,
    sse_path=f"/{APP_ROUTE}/sse",
    message_path=f"/{APP_ROUTE}/messages/",
    debug=True,
)


@mcp.tool(name="post_request", description="Returns POST data")
async def post_request(
    ctx: Context,
) -> dict:
    """Returns POST data"""
    base_url = ctx.request_context.lifespan_context.base_url
    params = {}

    json = {}

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method="POST",
            url=f"{base_url}/post",
            params=params,
            json=json,
        )
        return response.text
