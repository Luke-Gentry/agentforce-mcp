import json
import pytest
from mcp_openapi.parser import Config


@pytest.fixture
def sample_openapi_spec():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/api/v1/users": {
                "get": {
                    "operationId": "getUsers",
                    "summary": "Get all users",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer"},
                            "description": "Number of users to return",
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "string"},
                                                "name": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operationId": "createUser",
                    "summary": "Create a new user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "User created successfully",
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
                },
            },
            "/api/v1/users/{userId}": {
                "get": {
                    "operationId": "getUser",
                    "summary": "Get user by ID",
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
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
            },
        },
    }


@pytest.fixture
def sample_openapi_spec_with_refs():
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                },
                "UserInput": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                },
            },
            "parameters": {
                "userIdParam": {
                    "name": "userId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                },
            },
        },
        "paths": {
            "/api/v1/users": {
                "get": {
                    "operationId": "getUsers",
                    "summary": "Get all users",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/User"},
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "operationId": "createUser",
                    "summary": "Create a new user",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UserInput"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "User created successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        }
                    },
                },
            },
            "/api/v1/users/{userId}": {
                "get": {
                    "operationId": "getUser",
                    "summary": "Get user by ID",
                    "parameters": [{"$ref": "#/components/parameters/userIdParam"}],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        }
                    },
                }
            },
        },
    }


@pytest.fixture
def nasa_apod_spec():
    return {
        "openapi": "3.0.0",
        "servers": [
            {"url": "https://api.nasa.gov/planetary"},
            {"url": "http://api.nasa.gov/planetary"},
        ],
        "info": {
            "contact": {"email": "evan.t.yates@nasa.gov"},
            "description": "This endpoint structures the APOD imagery and associated metadata so that it can be repurposed for other applications. In addition, if the concept_tags parameter is set to True, then keywords derived from the image explanation are returned. These keywords could be used as auto-generated hashtags for twitter or instagram feeds; but generally help with discoverability of relevant imagery",
            "license": {
                "name": "Apache 2.0",
                "url": "http://www.apache.org/licenses/LICENSE-2.0.html",
            },
            "title": "APOD",
            "version": "1.0.0",
            "x-apisguru-categories": ["media", "open_data"],
            "x-origin": [
                {
                    "format": "swagger",
                    "url": "https://raw.githubusercontent.com/nasa/api-docs/gh-pages/assets/json/APOD",
                    "version": "2.0",
                }
            ],
            "x-providerName": "nasa.gov",
            "x-serviceName": "apod",
        },
        "tags": [
            {
                "description": "An example tag",
                "externalDocs": {
                    "description": "Here's a link",
                    "url": "https://example.com",
                },
                "name": "request tag",
            }
        ],
        "paths": {
            "/apod": {
                "get": {
                    "description": "Returns the picture of the day",
                    "parameters": [
                        {
                            "description": "The date of the APOD image to retrieve",
                            "in": "query",
                            "name": "date",
                            "required": False,
                            "schema": {"type": "string"},
                        },
                        {
                            "description": "Retrieve the URL for the high resolution image",
                            "in": "query",
                            "name": "hd",
                            "required": False,
                            "schema": {"type": "boolean"},
                        },
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "items": {"x-thing": "ok"},
                                        "type": "array",
                                    }
                                }
                            },
                            "description": "successful operation",
                        },
                        "400": {
                            "description": "Date must be between Jun 16, 1995 and Mar 28, 2019."
                        },
                    },
                    "security": [{"api_key": []}],
                    "summary": "Returns images",
                    "tags": ["request tag"],
                }
            }
        },
        "components": {
            "securitySchemes": {
                "api_key": {"in": "query", "name": "api_key", "type": "apiKey"}
            }
        },
    }


@pytest.fixture
def weather_api_spec():
    return {
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


def test_path_pattern_matching(tmp_path, sample_openapi_spec):
    # Create a temporary OpenAPI spec file
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec, f)

    # Test exact path matching
    config = Config.from_file(str(spec_file), ["/api/v1/users$"], base_path=tmp_path)
    assert len(config.paths) == 1
    assert config.paths[0].path == "/api/v1/users"

    # Verify GET operation details
    get_op = config.paths[0].get
    assert get_op.id == "getUsers"
    assert get_op.summary == "Get all users"
    assert len(get_op.parameters) == 1
    assert get_op.parameters[0].name == "limit"
    assert get_op.parameters[0].in_ == "query"
    assert get_op.parameters[0].type == "integer"

    # Test regex pattern matching for path parameters
    config = Config.from_file(
        str(spec_file), [r"/api/v1/users/\{.*\}"], base_path=tmp_path
    )
    assert len(config.paths) == 1
    assert config.paths[0].path == "/api/v1/users/{userId}"

    # Verify path parameter operation
    get_op = config.paths[0].get
    assert get_op.id == "getUser"
    assert get_op.parameters[0].name == "userId"
    assert get_op.parameters[0].in_ == "path"
    assert get_op.parameters[0].required is True


def test_request_response_processing(tmp_path, sample_openapi_spec):
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec, f)

    config = Config.from_file(str(spec_file), ["/api/v1/users"], base_path=tmp_path)
    assert len(config.paths) == 2
    path = config.paths[0]

    # Test GET response schema
    get_response = path.get.responses["200"]
    assert get_response.format == "application/json"
    assert get_response.description == "Successful response"
    schema = get_response.schema_
    assert schema.properties[0].type == "array"
    assert schema.properties[0].items.type == "object"
    assert len(schema.properties[0].items.properties) == 2

    # Test POST request and response
    post_op = path.post
    assert post_op.request_body_.required is True
    request_schema = post_op.request_body_.schema_
    assert len(request_schema.properties) == 2
    assert {p.name for p in request_schema.properties} == {"name", "email"}
    assert all(p.type == "string" for p in request_schema.properties)

    # Test POST response
    post_response = post_op.responses["201"]
    assert post_response.format == "application/json"
    assert post_response.description == "User created successfully"
    response_schema = post_response.schema_
    assert len(response_schema.properties) == 2
    assert {p.name for p in response_schema.properties} == {"id", "name"}


def test_multiple_path_patterns(tmp_path, sample_openapi_spec):
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec, f)

    # Test matching multiple patterns
    config = Config.from_file(
        str(spec_file), [r"/api/v1/users", r"/api/v1/users/\{.*\}"], base_path=tmp_path
    )
    assert len(config.paths) == 2
    paths = {p.path for p in config.paths}
    assert paths == {"/api/v1/users", "/api/v1/users/{userId}"}

    # Verify all operations are properly loaded
    operations = []
    for path in config.paths:
        if path.get:
            operations.append(path.get.id)
        if path.post:
            operations.append(path.post.id)

    assert set(operations) == {"getUsers", "createUser", "getUser"}


def test_reference_resolution(tmp_path, sample_openapi_spec_with_refs):
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec_with_refs, f)

    config = Config.from_file(str(spec_file), ["/api/v1/users"], base_path=tmp_path)
    assert len(config.paths) == 2
    path = config.paths[0]

    # Test GET response schema with resolved reference
    get_response = path.get.responses["200"]
    schema = get_response.schema_
    assert schema.properties[0].type == "array"
    items = schema.properties[0].items
    assert items.type == "object"
    assert len(items.properties) == 2
    assert {p.name for p in items.properties} == {"id", "name"}

    # Test POST request body with resolved reference
    post_op = path.post
    request_schema = post_op.request_body_.schema_
    assert len(request_schema.properties) == 2
    assert {p.name for p in request_schema.properties} == {"name", "email"}

    # Test POST response with resolved reference
    post_response = post_op.responses["201"]
    response_schema = post_response.schema_
    assert len(response_schema.properties) == 2
    assert {p.name for p in response_schema.properties} == {"id", "name"}


def test_parameter_reference_resolution(tmp_path, sample_openapi_spec_with_refs):
    spec_file = tmp_path / "openapi.json"
    with open(spec_file, "w") as f:
        json.dump(sample_openapi_spec_with_refs, f)

    config = Config.from_file(
        str(spec_file), [r"/api/v1/users/\{.*\}"], base_path=tmp_path
    )
    assert len(config.paths) == 1
    path = config.paths[0]

    # Test resolved parameter reference
    get_op = path.get
    assert len(get_op.parameters) == 1
    param = get_op.parameters[0]
    assert param.name == "userId"
    assert param.in_ == "path"
    assert param.required is True
    assert param.type == "string"


def test_nasa_apod_spec_parsing(tmp_path, nasa_apod_spec):
    # Create a temporary OpenAPI spec file
    spec_file = tmp_path / "nasa_apod.json"
    with open(spec_file, "w") as f:
        json.dump(nasa_apod_spec, f)

    # Parse the spec
    config = Config.from_file(str(spec_file), ["/apod"], base_path=tmp_path)

    # Basic validation
    assert len(config.paths) == 1
    assert config.paths[0].path == "/apod"

    # Validate GET operation
    get_op = config.paths[0].get
    assert get_op.id == "/apod"
    assert get_op.summary == "Returns images"
    assert get_op.description == "Returns the picture of the day"

    # Validate parameters
    assert len(get_op.parameters) == 2
    date_param = next(p for p in get_op.parameters if p.name == "date")
    assert date_param.in_ == "query"
    assert date_param.required is False
    assert date_param.type == "string"

    hd_param = next(p for p in get_op.parameters if p.name == "hd")
    assert hd_param.in_ == "query"
    assert hd_param.required is False
    assert hd_param.type == "boolean"

    # Validate responses
    assert "200" in get_op.responses
    assert "400" in get_op.responses
    success_response = get_op.responses["200"]
    assert success_response.format == "application/json"
    assert success_response.description == "successful operation"


def test_parameter_enums_and_defaults(tmp_path, weather_api_spec):
    spec_file = tmp_path / "weather_api.json"
    with open(spec_file, "w") as f:
        json.dump(weather_api_spec, f)

    config = Config.from_file(str(spec_file), ["/v1/forecast"], base_path=tmp_path)
    assert len(config.paths) == 1
    path = config.paths[0]

    # Test GET operation parameters
    get_op = path.get
    assert len(get_op.parameters) == 3

    # Test temperature_unit parameter
    temp_param = next(p for p in get_op.parameters if p.name == "temperature_unit")
    assert temp_param.type == "string"
    assert temp_param.enum == ["celsius", "fahrenheit"]
    assert temp_param.default == "celsius"

    # Test wind_speed_unit parameter
    wind_param = next(p for p in get_op.parameters if p.name == "wind_speed_unit")
    assert wind_param.type == "string"
    assert wind_param.enum == ["kmh", "ms", "mph", "kn"]
    assert wind_param.default == "kmh"

    # Test timeformat parameter
    time_param = next(p for p in get_op.parameters if p.name == "timeformat")
    assert time_param.type == "string"
    assert time_param.enum == ["iso8601", "unixtime"]
    assert time_param.default == "iso8601"
