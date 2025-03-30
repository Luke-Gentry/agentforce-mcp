import inspect
from unittest.mock import AsyncMock, patch
import pytest
import tempfile
import json
import os
from pathlib import Path

from mcp_openapi.tools import (
    Tool,
    ToolParameter,
    create_tool_function_exec,
    tools_from_spec,
)
from mcp_openapi.proxy import MCPProxy
from mcp_openapi.parser import (
    Operation,
    Parameter,
    RequestBody,
    Schema,
    Spec,
)

from starlette.requests import Request


@pytest.fixture
def mock_tool():
    """Create a simple mock tool for testing"""
    return Tool(
        name="test_tool",
        description="A test tool",
        parameters=[
            ToolParameter(
                name="param1", type="str", description="First parameter", default="None"
            ),
            ToolParameter(
                name="param2",
                type="int",
                description="Second parameter",
                default="None",
            ),
            ToolParameter(
                name="body_param",
                type="dict",
                description="Body parameter",
                default="None",
                request_body=True,
            ),
        ],
        method="POST",
        path="/test/path",
    )


@pytest.fixture
def mock_context():
    """Create a mock context with base_url"""

    class MockContext:
        class RequestContext:
            class LifespanContext:
                base_url = "http://test.com"
                proxy = MCPProxy()

            lifespan_context = LifespanContext()
            request = Request(
                scope={
                    "type": "http",
                    "method": "GET",
                    "path": "/test",
                }
            )

        request_context = RequestContext()

    return MockContext()


@pytest.fixture
def weather_tool():
    """Create a weather API tool with enums and defaults"""
    return Tool(
        name="get_forecast",
        description="Get weather forecast",
        parameters=[
            ToolParameter(
                name="temperature_unit",
                type="str",
                description="Temperature unit Options: celsius, fahrenheit",
                default="celsius",
            ),
            ToolParameter(
                name="wind_speed_unit",
                type="str",
                description="Wind speed unit Options: kmh, ms, mph, kn",
                default="kmh",
            ),
            ToolParameter(
                name="timeformat",
                type="str",
                description="Time format Options: iso8601, unixtime",
                default="iso8601",
            ),
        ],
        method="GET",
        path="/v1/forecast",
    )


@pytest.fixture
def mock_operation():
    """Create a mock operation with various parameter types"""
    # Create request body schema with nested properties
    request_body_schema = Schema(
        name="TestRequestBody",
        type="object",
        properties=[
            Schema(
                name="body_string", type="string", description="A body string parameter"
            ),
            Schema(
                name="body_object",
                type="object",
                description="A body object parameter",
                properties=[
                    Schema(
                        name="nested_string",
                        type="string",
                        description="A nested string parameter",
                    ),
                    Schema(
                        name="nested_int",
                        type="integer",
                        description="A nested integer parameter",
                    ),
                ],
            ),
            Schema(
                name="anyof_object_or_string",
                description="A union parameter that can be object or string",
                type=["object", "string"],
                any_of=[
                    Schema(
                        name="ObjectSchema",
                        type="object",
                        properties=[
                            Schema(
                                name="anyof_nested_string",
                                type="string",
                                description="A nested string parameter",
                            ),
                            Schema(
                                name="anyof_nested_int",
                                type="integer",
                                description="A nested integer parameter",
                            ),
                        ],
                    ),
                    Schema(
                        name="anyof_string",
                        type="string",
                        description="A string parameter",
                    ),
                ],
            ),
        ],
    )

    # Create request body
    request_body = RequestBody(
        description="Test request body", schema_=request_body_schema
    )

    # Create parameters
    parameters = [
        Parameter(
            name="string_param",
            **{"in": "query"},
            type="string",
            description="A string parameter",
        ),
        Parameter(
            name="int_param",
            **{"in": "query"},
            type="integer",
            description="An integer parameter",
        ),
        Parameter(
            name="float_param",
            **{"in": "query"},
            type="number",
            description="A float parameter",
        ),
        Parameter(
            name="bool_param",
            **{"in": "query"},
            type="boolean",
            description="A boolean parameter",
        ),
        Parameter(
            name="array_param[]",
            **{"in": "query"},
            type="string",
            description="An array parameter",
            default=[],
        ),
        Parameter(
            name="enum_param",
            **{"in": "query"},
            type="string",
            description="An enum parameter",
            enum=["option1", "option2", "option3"],
            default="option1",
        ),
    ]

    return Operation(
        id="TestOperation",
        summary="Test operation with various parameter types",
        parameters=parameters,
        request_body_=request_body,
        responses={},  # Empty responses for this test
    )


# @pytest.mark.asyncio
# async def test_tool_function_noexec(mock_tool, mock_context):
#     """Test the noexec tool function creation"""
#     # Create the tool function
#     tool_func = create_tool_function_noexec(mock_tool)

#     # Mock httpx client
#     mock_response = AsyncMock()
#     mock_response.text = '{"result": "success"}'

#     # Create an AsyncMock for the client itself
#     mock_client_instance = AsyncMock()
#     mock_client_instance.request.return_value = mock_response
#     mock_client_instance.aclose = AsyncMock()  # Add mock for aclose method

#     with patch("httpx.AsyncClient") as mock_client:
#         # Return the mock client instance directly instead of using __aenter__
#         mock_client.return_value = mock_client_instance

#         # Test function execution
#         result = await tool_func(
#             mock_context, param1="test", param2=123, body_param={"key": "value"}
#         )

#         # Verify the request was made correctly
#         mock_client_instance.request.assert_called_once()
#         call_args = mock_client_instance.request.call_args[1]

#         assert call_args["method"] == "POST"
#         assert call_args["url"] == "http://test.com/test/path"
#         assert call_args["params"] == {"param1": "test", "param2": 123}
#         assert call_args["json"] == {"body_param": {"key": "value"}}
#         assert result == '{"result": "success"}'


@pytest.mark.asyncio
async def test_tool_function_exec(mock_tool, mock_context):
    """Test the exec tool function creation"""
    # Create the tool function
    tool_func = create_tool_function_exec(mock_tool)

    # Mock httpx client
    mock_response = AsyncMock()
    mock_response.text = '{"result": "success"}'

    # Create an AsyncMock for the client itself
    mock_client_instance = AsyncMock()
    mock_client_instance.request.return_value = mock_response
    mock_client_instance.aclose = AsyncMock()  # Add mock for aclose method

    with patch("httpx.AsyncClient") as mock_client:
        # Return the mock client instance directly instead of using __aenter__
        mock_client.return_value = mock_client_instance

        # Test function execution
        result = await tool_func(
            mock_context, param1="test", param2=123, body_param={"key": "value"}
        )

        # Verify the request was made correctly
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args[1]
        assert call_args["method"] == "POST"
        assert call_args["url"] == "http://test.com/test/path"
        assert call_args["params"] == {"param1": "test", "param2": 123}
        assert call_args["json"] == {"body_param": {"key": "value"}}
        assert result == '{"result": "success"}'


def test_tool_parameter_conversion():
    """Test that tool parameters are correctly converted to Python types"""
    tool = Tool(
        name="test_tool",
        description="A test tool",
        parameters=[
            ToolParameter(
                name="string_param",
                type="str",
                description="String parameter",
                default="None",
            ),
            ToolParameter(
                name="int_param",
                type="int",
                description="Integer parameter",
                default="None",
            ),
            ToolParameter(
                name="float_param",
                type="float",
                description="Float parameter",
                default="None",
            ),
            ToolParameter(
                name="bool_param",
                type="bool",
                description="Boolean parameter",
                default="None",
            ),
            ToolParameter(
                name="array_param",
                type="list[str]",
                description="Array parameter",
                default="None",
            ),
        ],
        method="GET",
        path="/test/path",
    )

    # Create function using noexec method
    tool_func = create_tool_function_exec(tool)

    # Verify parameter types
    sig = inspect.signature(tool_func)
    assert (
        str(sig.parameters["string_param"])
        == "string_param: str = FieldInfo(annotation=NoneType, required=False, default='None', description='String parameter')"
    )
    assert (
        str(sig.parameters["int_param"])
        == "int_param: int = FieldInfo(annotation=NoneType, required=False, default='None', description='Integer parameter')"
    )
    assert (
        str(sig.parameters["float_param"])
        == "float_param: float = FieldInfo(annotation=NoneType, required=False, default='None', description='Float parameter')"
    )
    assert (
        str(sig.parameters["bool_param"])
        == "bool_param: bool = FieldInfo(annotation=NoneType, required=False, default='None', description='Boolean parameter')"
    )
    assert (
        str(sig.parameters["array_param"])
        == "array_param: list[str] = FieldInfo(annotation=NoneType, required=False, default='None', description='Array parameter')"
    )


def test_tool_parameter_enums_and_defaults(weather_tool):
    """Test that tool parameters correctly handle enums and defaults"""
    # Create function using noexec method
    tool_func = create_tool_function_exec(weather_tool)

    # Verify parameter types and descriptions
    sig = inspect.signature(tool_func)

    # Test temperature_unit parameter
    temp_param = sig.parameters["temperature_unit"]
    assert (
        str(temp_param)
        == "temperature_unit: str = FieldInfo(annotation=NoneType, required=False, default='celsius', description='Temperature unit Options: celsius, fahrenheit')"
    )

    # Test wind_speed_unit parameter
    wind_param = sig.parameters["wind_speed_unit"]
    assert (
        str(wind_param)
        == "wind_speed_unit: str = FieldInfo(annotation=NoneType, required=False, default='kmh', description='Wind speed unit Options: kmh, ms, mph, kn')"
    )

    # Test timeformat parameter
    time_param = sig.parameters["timeformat"]
    assert (
        str(time_param)
        == "timeformat: str = FieldInfo(annotation=NoneType, required=False, default='iso8601', description='Time format Options: iso8601, unixtime')"
    )


@pytest.mark.asyncio
async def test_weather_tool_execution(weather_tool, mock_context):
    """Test the weather tool function execution with enums and defaults"""
    # Create the tool function
    tool_func = create_tool_function_exec(weather_tool)

    # Mock httpx client
    mock_response = AsyncMock()
    mock_response.text = '{"temperature": 20, "wind_speed": 10}'

    # Create an AsyncMock for the client itself
    mock_client_instance = AsyncMock()
    mock_client_instance.request.return_value = mock_response
    mock_client_instance.aclose = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value = mock_client_instance

        # Test function execution with default values
        result = await tool_func(mock_context)

        # Verify the request was made with default values
        mock_client_instance.request.assert_called_once()
        call_args = mock_client_instance.request.call_args[1]
        assert call_args["method"] == "GET"
        assert call_args["url"] == "http://test.com/v1/forecast"

        # Check that params contain Field objects with correct defaults
        params = call_args["params"]
        assert params["temperature_unit"].default == "celsius"
        assert params["wind_speed_unit"].default == "kmh"
        assert params["timeformat"].default == "iso8601"

        assert result == '{"temperature": 20, "wind_speed": 10}'

        # Test with custom values
        result = await tool_func(
            mock_context,
            temperature_unit="fahrenheit",
            wind_speed_unit="mph",
            timeformat="unixtime",
        )

        # Verify the request was made with custom values
        assert mock_client_instance.request.call_count == 2
        call_args = mock_client_instance.request.call_args[1]
        params = call_args["params"]
        assert params["temperature_unit"] == "fahrenheit"
        assert params["wind_speed_unit"] == "mph"
        assert params["timeformat"] == "unixtime"


def test_tool_from_operation(mock_operation):
    """Test Tool.from_operation with various parameter types"""
    tool = Tool.from_operation("/test/path", "POST", mock_operation)

    # Test basic tool properties
    assert tool.name == "test_operation"
    assert tool.description == "Test operation with various parameter types"
    assert tool.method == "POST"
    assert tool.path == "/test/path"

    # Test parameter types and conversions
    param_map = {p.name: p for p in tool.parameters}

    # Test basic type conversions
    assert param_map["string_param"].type == "str"
    assert param_map["int_param"].type == "int"
    assert param_map["float_param"].type == "float"
    assert param_map["bool_param"].type == "bool"

    # Test array type
    assert param_map["array_params"].type == "list[str]"

    # Test enum parameter
    enum_param = param_map["enum_param"]
    assert enum_param.type == "str"
    assert "Options: option1, option2, option3" in enum_param.description

    anyof_param = param_map["anyof_object_or_string"]
    assert anyof_param.type == "Union[Any, str]"
    assert (
        "A union parameter that can be object or string, one of: (Object with properties: anyof_nested_string, anyof_nested_int) OR (A string parameter)"
        in anyof_param.description
    )


def test_tool_from_operation_with_long_enum():
    """Test Tool.from_operation with a long enum list that should be truncated"""
    # Create a long enum list
    long_enum = [f"option{i}" for i in range(20)]  # Make it longer to ensure truncation

    # Create operation with long enum parameter
    operation = Operation(
        id="TestOperation",
        summary="Test operation with long enum",
        parameters=[
            Parameter(
                name="long_enum_param",
                **{"in": "query"},
                type="string",
                description="A parameter with many enum options",
                enum=long_enum,
                default="option0",
            )
        ],
        request_body_=RequestBody(
            description="Empty request body",
            schema_=Schema(name="EmptySchema", type="object", properties=[]),
        ),
        responses={},
    )

    tool = Tool.from_operation("/test/path", "POST", operation)
    param = tool.parameters[0]

    # Verify the enum description is truncated
    assert param.description.startswith(
        "A parameter with many enum options Options: option0, option1"
    )
    assert param.description.endswith(
        "..."
    )  # Should end with ellipsis due to truncation
    assert len(param.description) <= 100  # MAX_ENUM_DESCRIPTION_LENGTH


def test_end_to_end_weather_api():
    """Test the complete flow from OpenAPI JSON to tools using the weather API spec"""
    # Weather API spec from test_parser.py
    weather_api_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Weather API", "version": "1.0.0"},
        "paths": {
            "/v1/forecast": {
                "get": {
                    "operationId": "getForecast",
                    "summary": "Get weather forecast",
                    "parameters": [
                        {
                            "name": "temperature_unit",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "default": "celsius",
                                "enum": ["celsius", "fahrenheit"],
                            },
                            "description": "Temperature unit",
                        },
                        {
                            "name": "wind_speed_unit",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "default": "kmh",
                                "enum": ["kmh", "ms", "mph", "kn"],
                            },
                            "description": "Wind speed unit",
                        },
                        {
                            "name": "timeformat",
                            "in": "query",
                            "schema": {
                                "type": "string",
                                "default": "iso8601",
                                "enum": ["iso8601", "unixtime"],
                            },
                            "description": "Time format",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "temperature": {"type": "number"},
                                            "wind_speed": {"type": "number"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }

    # Write the spec to a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(weather_api_spec, f)
        spec_path = f.name

    try:
        spec = Spec.from_file(
            spec_path, ["/v1/forecast"], base_path=Path(spec_path).parent
        )

        tools = tools_from_spec(spec, [])

        # Verify we got exactly one tool
        assert len(tools) == 1
        tool = tools[0]

        assert tool.name == "get_forecast"
        assert tool.description == "Get weather forecast"
        assert tool.method == "GET"
        assert tool.path == "/v1/forecast"

        assert len(tool.parameters) == 3
        param_map = {p.name: p for p in tool.parameters}

        temp_param = param_map["temperature_unit"]
        assert temp_param.type == "str"
        assert temp_param.default == "celsius"
        assert "Options: celsius, fahrenheit" in temp_param.description

        wind_param = param_map["wind_speed_unit"]
        assert wind_param.type == "str"
        assert wind_param.default == "kmh"
        assert "Options: kmh, ms, mph, kn" in wind_param.description

        time_param = param_map["timeformat"]
        assert time_param.type == "str"
        assert time_param.default == "iso8601"
        assert "Options: iso8601, unixtime" in time_param.description

        tool_func = create_tool_function_exec(tool)

        sig = inspect.signature(tool_func)
        assert len(sig.parameters) == 4  # ctx + 3 parameters

        # Verify parameter types and defaults
        temp_param = sig.parameters["temperature_unit"]
        assert (
            str(temp_param)
            == "temperature_unit: str = FieldInfo(annotation=NoneType, required=False, default='celsius', description='Temperature unit Options: celsius, fahrenheit')"
        )

        wind_param = sig.parameters["wind_speed_unit"]
        assert (
            str(wind_param)
            == "wind_speed_unit: str = FieldInfo(annotation=NoneType, required=False, default='kmh', description='Wind speed unit Options: kmh, ms, mph, kn')"
        )

        time_param = sig.parameters["timeformat"]
        assert (
            str(time_param)
            == "timeformat: str = FieldInfo(annotation=NoneType, required=False, default='iso8601', description='Time format Options: iso8601, unixtime')"
        )

    finally:
        # Clean up the temporary file
        os.unlink(spec_path)


def test_end_to_end_form_encoded_api():
    """Test the complete flow from OpenAPI JSON to tools using a complex form-encoded API spec"""
    # Form-encoded API spec with complex request body
    form_encoded_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Form API", "version": "1.0.0"},
        "paths": {
            "/v1/customers": {
                "post": {
                    "operationId": "createCustomer",
                    "summary": "Create a customer",
                    "requestBody": {
                        "content": {
                            "application/x-www-form-urlencoded": {
                                "encoding": {
                                    "address": {"explode": True, "style": "deepObject"},
                                    "metadata": {
                                        "explode": True,
                                        "style": "deepObject",
                                    },
                                },
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "maxLength": 256,
                                            "description": "The customer's full name or business name.",
                                        },
                                        "email": {
                                            "type": "string",
                                            "maxLength": 512,
                                            "description": "Customer's email address",
                                        },
                                        "address": {
                                            "anyOf": [
                                                {
                                                    "type": "object",
                                                    "properties": {
                                                        "line1": {
                                                            "type": "string",
                                                            "maxLength": 5000,
                                                        },
                                                        "city": {
                                                            "type": "string",
                                                            "maxLength": 5000,
                                                        },
                                                        "country": {
                                                            "type": "string",
                                                            "maxLength": 5000,
                                                        },
                                                    },
                                                },
                                                {"type": "string", "enum": [""]},
                                            ],
                                            "description": "The customer's address",
                                        },
                                        "metadata": {
                                            "anyOf": [
                                                {
                                                    "type": "object",
                                                    "additionalProperties": {
                                                        "type": "string"
                                                    },
                                                },
                                                {"type": "string", "enum": [""]},
                                            ],
                                            "description": "Set of key-value pairs",
                                        },
                                        "invoice_settings": {
                                            "type": "object",
                                            "properties": {
                                                "custom_fields": {
                                                    "anyOf": [
                                                        {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "name": {
                                                                        "type": "string",
                                                                        "maxLength": 40,
                                                                    },
                                                                    "value": {
                                                                        "type": "string",
                                                                        "maxLength": 140,
                                                                    },
                                                                },
                                                                "required": [
                                                                    "name",
                                                                    "value",
                                                                ],
                                                            },
                                                        },
                                                        {
                                                            "type": "string",
                                                            "enum": [""],
                                                        },
                                                    ],
                                                }
                                            },
                                        },
                                    },
                                },
                            }
                        },
                        "required": True,
                    },
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "string"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }

    # Write the spec to a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(form_encoded_spec, f)
        spec_path = f.name

    try:
        spec = Spec.from_file(
            spec_path, ["/v1/customers"], base_path=Path(spec_path).parent
        )

        tools = tools_from_spec(spec, [])

        # Verify we got exactly one tool
        assert len(tools) == 1
        tool = tools[0]

        # Verify basic tool properties
        assert tool.name == "create_customer"
        assert tool.description == "Create a customer"
        assert tool.method == "POST"
        assert tool.path == "/v1/customers"

        # Verify parameters
        assert (
            len(tool.parameters) == 4
        )  # name, email, address, metadata (invoice_settings is skipped as it's a nested object)
        param_map = {p.name: p for p in tool.parameters}

        # Test basic string parameters
        name_param = param_map["name"]
        assert name_param.type == "str"
        assert name_param.description == "The customer's full name or business name."
        assert name_param.request_body is True

        email_param = param_map["email"]
        assert email_param.type == "str"
        assert email_param.description == "Customer's email address"
        assert email_param.request_body is True

        # Test address parameter with anyOf
        address_param = param_map["address"]
        assert address_param.type == "Union[Any, str]"
        assert "The customer's address" in address_param.description
        assert (
            "Object with properties: line1, city, country" in address_param.description
        )
        assert address_param.request_body is True

        # Test metadata parameter with anyOf and additionalProperties
        metadata_param = param_map["metadata"]
        assert metadata_param.type == "Union[Any, str]"
        assert "Set of key-value pairs" in metadata_param.description
        assert metadata_param.request_body is True

        # Create the tool function
        tool_func = create_tool_function_exec(tool)

        # Verify the function signature
        sig = inspect.signature(tool_func)
        assert len(sig.parameters) == 5  # ctx + 4 parameters

        # Verify parameter types and descriptions
        name_param = sig.parameters["name"]
        assert (
            str(name_param)
            == "name: str = FieldInfo(annotation=NoneType, required=False, default='None', description=\"The customer's full name or business name.\")"
        )

        email_param = sig.parameters["email"]
        assert (
            str(email_param)
            == "email: str = FieldInfo(annotation=NoneType, required=False, default='None', description=\"Customer's email address\")"
        )

        address_param = sig.parameters["address"]
        assert "Union[Any, str]" in str(address_param)
        assert "The customer's address" in str(address_param)
        assert "Object with properties: line1, city, country" in str(address_param)

        metadata_param = sig.parameters["metadata"]
        assert "Union[Any, str]" in str(metadata_param)
        assert "Set of key-value pairs" in str(metadata_param)

    finally:
        # Clean up the temporary file
        os.unlink(spec_path)
