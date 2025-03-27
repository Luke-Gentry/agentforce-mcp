# stdlib
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from starlette.requests import Request

# 3p
import httpx

logger = logging.getLogger(__name__)


class MCPProxy:
    """A class to intercept and record HTTP requests made through httpx clients."""

    def __init__(
        self,
        cassette_dir: str = "cassettes",
        forward_headers: Optional[Dict[str, Any]] = None,
        client_builder: Optional[Callable[[], httpx.AsyncClient]] = None,
    ):
        """Initialize the recorder with a directory to store cassettes.

        Args:
            cassette_dir: Directory where request/response cassettes will be stored
            forward_headers: Headers to forward from the incoming request
            client_builder: Function that returns an AsyncClient. Defaults to creating a new httpx.AsyncClient
        """
        self.cassette_dir = Path(cassette_dir)
        self.cassette_dir.mkdir(parents=True, exist_ok=True)
        self.forward_headers = forward_headers
        self.client_builder = client_builder or (lambda: httpx.AsyncClient())

    async def do_request(
        self,
        request: Request,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Record and execute an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: The URL to make the request to
            params: Query parameters
            json_body: JSON body data
            **kwargs: Additional arguments to pass to httpx.Client.request

        Returns:
            The httpx Response object
        """
        # Pass along any headers that were set in the server config
        request_headers = {}
        if self.forward_headers:
            for header in self.forward_headers:
                if header in request.headers:
                    request_headers[header] = request.headers[header]

        # Create a unique filename for this request
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{method.lower()}_{Path(url).name}.json"
        cassette_path = self.cassette_dir / filename

        # Log the request
        logger.info(f"Making {method} request to {url}")
        if params:
            logger.debug(f"Query parameters: {params}")
        if json_body:
            logger.debug(f"Request body: {json_body}")

        # Make the actual request using the provided client builder
        client = self.client_builder()
        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                headers=request_headers,
            )
        finally:
            await client.aclose()

        # Record the request and response
        cassette_data = {
            "request": {
                "method": method,
                "url": url,
                "params": params,
                "json": json_body,
            },
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "text": response.text,
            },
            "timestamp": timestamp,
        }

        # Save to file
        with open(cassette_path, "w") as f:
            json.dump(cassette_data, f, indent=2)

        logger.info(f"Request recorded to {cassette_path}")
        return response
