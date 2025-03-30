# stdlib
import logging
from typing import Any, Dict, Optional, Callable, List
from starlette.requests import Request

# 3p
import httpx

log = logging.getLogger(__name__)


class MCPProxy:
    """A class to intercept and record HTTP requests made through httpx clients."""

    def __init__(
        self,
        forward_headers: Optional[List[str]] = None,
        forward_query_params: Optional[List[str]] = None,
        client_builder: Optional[Callable[[], httpx.AsyncClient]] = None,
        timeout: Optional[float] = None,
    ):
        """Initialize the recorder with a directory to store cassettes.

        Args:
            forward_headers: List of headers to forward from the request to the server
            forward_query_params: List of query parameters to forward from the request to the server
            client_builder: Function that returns an AsyncClient. Defaults to creating a new httpx.AsyncClient
        """
        self.forward_headers = forward_headers
        self.forward_query_params = forward_query_params
        self.client_builder = client_builder or (lambda: httpx.AsyncClient())
        self.timeout = timeout

    async def do_request(
        self,
        request: Request,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Execute an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: The URL to make the request to
            params: Query parameters
            json_body: JSON body data

        Returns:
            The httpx Response object
        """
        # Pass along any headers that were set in the server config
        request_headers = {}
        if self.forward_headers:
            for header in self.forward_headers:
                if header in request.headers:
                    request_headers[header] = request.headers[header]

        # Forward specified query parameters
        if self.forward_query_params and params:
            forwarded_params = {
                k: v for k, v in params.items() if k in self.forward_query_params
            }
            params = forwarded_params

        # Filter out None values from params and json_body
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        if json_body:
            json_body = {k: v for k, v in json_body.items() if v is not None}

        # Log the request
        log.info(f"Making {method} request to {url}")
        if params:
            log.debug(f"Query parameters: {params}")
        if json_body:
            log.debug(f"Request body: {json_body}")

        # Make the actual request using the provided client builder
        client = self.client_builder()
        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                headers=request_headers,
                timeout=self.timeout,
            )
        finally:
            await client.aclose()

        return response
