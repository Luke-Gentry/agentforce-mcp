import pytest
from pathlib import Path
import json
from unittest.mock import AsyncMock, MagicMock
from starlette.requests import Request
from httpx import Response, AsyncClient
from mcp_openapi.proxy import MCPProxy


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx client."""
    mock_client = AsyncMock(spec=AsyncClient)
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.text = '{"test": "response"}'
    mock_response.request = MagicMock()
    mock_response.request.headers = {}
    mock_client.request.return_value = mock_response
    return mock_client


@pytest.fixture
def proxy(tmp_path, mock_httpx_client):
    """Create a proxy instance with a temporary cassette directory and mock client."""
    return MCPProxy(
        cassette_dir=str(tmp_path),
        client_builder=lambda: mock_httpx_client,
        record=True,
    )


@pytest.fixture
def mock_request():
    """Create a mock request with headers."""
    request = Request(
        scope={
            "type": "http",
            "headers": [
                (b"authorization", b"Bearer test-token"),
                (b"content-type", b"application/json"),
                (b"x-custom-header", b"test-value"),
            ],
        }
    )
    return request


@pytest.mark.asyncio
async def test_proxy_params(proxy, mock_request, mock_httpx_client):
    """Test that query parameters are correctly passed in the request."""
    url = "https://api.example.com/test"
    params = {"key1": "value1", "key2": "value2"}

    response = await proxy.do_request(
        request=mock_request,
        method="GET",
        url=url,
        params=params,
    )
    assert response.status_code == 200
    assert response.text == '{"test": "response"}'

    # Verify the request was made with correct parameters
    mock_httpx_client.request.assert_called_once_with(
        method="GET",
        url=url,
        params=params,
        json=None,
        headers={},
    )

    # Check that a cassette file was created
    cassette_files = list(Path(proxy.cassette_dir).glob("*.json"))
    assert len(cassette_files) == 1

    # Verify the recorded data
    with open(cassette_files[0]) as f:
        recorded_data = json.load(f)

    assert recorded_data["request"]["method"] == "GET"
    assert recorded_data["request"]["url"] == url
    assert recorded_data["request"]["params"] == params


@pytest.mark.asyncio
async def test_proxy_forward_headers(proxy, mock_request, mock_httpx_client):
    """Test that only specified headers are forwarded."""
    # Set up recorder with specific headers to forward
    proxy.forward_headers = ["authorization", "x-custom-header"]

    url = "https://api.example.com/test"

    response = await proxy.do_request(
        request=mock_request,
        method="GET",
        url=url,
    )
    assert response.status_code == 200
    assert response.text == '{"test": "response"}'

    # Verify the request was made with correct headers
    mock_httpx_client.request.assert_called_once_with(
        method="GET",
        url=url,
        params=None,
        json=None,
        headers={
            "authorization": "Bearer test-token",
            "x-custom-header": "test-value",
        },
    )

    # Check that a cassette file was created
    cassette_files = list(Path(proxy.cassette_dir).glob("*.json"))
    assert len(cassette_files) == 1


@pytest.mark.asyncio
async def test_proxy_json_body(proxy, mock_request, mock_httpx_client):
    """Test that JSON body is correctly passed and recorded."""
    url = "https://api.example.com/test"
    json_body = {"test": "data"}

    response = await proxy.do_request(
        request=mock_request,
        method="POST",
        url=url,
        json_body=json_body,
    )
    assert response.status_code == 200
    assert response.text == '{"test": "response"}'

    # Verify the request was made with correct JSON body
    mock_httpx_client.request.assert_called_once_with(
        method="POST",
        url=url,
        params=None,
        json=json_body,
        headers={},
    )

    # Check that a cassette file was created
    cassette_files = list(Path(proxy.cassette_dir).glob("*.json"))
    assert len(cassette_files) == 1

    # Verify the recorded data
    with open(cassette_files[0]) as f:
        recorded_data = json.load(f)

    assert recorded_data["request"]["method"] == "POST"
    assert recorded_data["request"]["url"] == url
    assert recorded_data["request"]["json"] == json_body
