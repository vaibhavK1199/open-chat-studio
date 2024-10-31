import httpx
from celery.utils.text import dedent
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, ConfigDict, Field

from apps.custom_actions.models import CustomAction


class OpenAPIToolInput(BaseModel):
    endpoint: str = Field(..., description="The API endpoint to call")
    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE, etc.)")
    params: dict | None = Field(..., description="Query parameters for the request")
    data: dict | None = Field(..., description="Request body data")
    headers: dict | None = Field(..., description="Custom headers for the request")


class OpenAPITool(BaseTool):
    """A custom tool for making API requests based on OpenAPI specifications. This is a single tool that
    can handle multiple API endpoints and methods. The tool is configured with a list of CustomAction objects,
    each of which represents an API service with its own OpenAPI schema. The tool will determine which action
    to use based on the endpoint and method provided in the input. The tool will then make the API request
    using the appropriate action and return the response."""

    custom_actions: list[CustomAction]

    name: str = "openapi_request_tool"
    description: str = dedent(
        """
        Makes HTTP requests to API endpoints defined in the OpenAPI specification shown below.
        Authentication and request formatting are handled based on the OpenAPI schema.

        Generate the full API request details for answering the user question.
        You should build the API request in order to get a response that is as short as possible, while still
        getting the necessary information to answer the question. Pay attention to deliberately exclude
        any unnecessary pieces of data in the API call.
        """
    )
    args_schema: type[OpenAPIToolInput] = OpenAPIToolInput
    handle_tool_error: bool = True
    executors: list["ActionExecutor"] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.executors = [ActionExecutor(action) for action in self.custom_actions]

    def _run(self, endpoint: str, method: str, params: dict | None, data: dict | None, headers: dict | None) -> str:
        for executor in self.executors:
            if executor.can_run(endpoint, method):
                return executor.run(endpoint, method, params, data, headers)
        raise ToolException(f"Endpoint {endpoint} with method {method} not found in OpenAPI spec")


class ActionExecutor:
    def __init__(self, action: CustomAction):
        self.action = action
        self.auth_service = action.get_auth_service()
        self.spec = action.api_schema
        self.base_url = self.spec["servers"][0]["url"]

    def can_run(self, endpoint: str, method: str) -> bool:
        return self._validate_endpoint(endpoint, method)

    def run(self, endpoint: str, method: str, params: dict | None, data: dict | None, headers: dict | None) -> str:
        if not self._validate_endpoint(endpoint, method):
            raise ToolException(f"Endpoint {endpoint} with method {method} not found in OpenAPI spec")

        url = self._build_url(endpoint)

        with self.auth_service.get_http_client() as client:
            try:
                return self.auth_service.call_with_retries(
                    self._make_request, client, url, method, params, data, headers
                )
            except httpx.HTTPError as e:
                raise ToolException(f"Error making request: {str(e)}")

    def _make_request(
        self,
        http_client: httpx.Client,
        url: str,
        method: str,
        params: dict | None,
        data: dict | None,
        headers: dict | None,
    ) -> str:
        response = http_client.request(
            method.upper(),
            url,
            params=params,
            data=data,
            headers=headers,
            follow_redirects=False,
        )
        response.raise_for_status()
        return response.text

    def _build_url(self, endpoint: str) -> str:
        """Build the full URL for the API request."""
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def _validate_endpoint(self, endpoint: str, method: str) -> bool:
        """
        Validate if the endpoint and method exist in the OpenAPI spec.

        Args:
            endpoint: API endpoint path
            method: HTTP method

        Returns:
            bool: True if endpoint exists in spec, False otherwise
        """
        for path, operations in self.spec["paths"].items():
            if self._paths_match(endpoint, path):
                return method.lower() in [op.lower() for op in operations.keys()]
        return False

    def _paths_match(self, request_path: str, spec_path: str) -> bool:
        """
        Check if a request path matches a path template from the OpenAPI spec.
        Handles path parameters (e.g., /users/{id} matches /users/123)
        """
        request_parts = request_path.strip("/").split("/")
        spec_parts = spec_path.strip("/").split("/")

        if len(request_parts) != len(spec_parts):
            return False

        for req_part, spec_part in zip(request_parts, spec_parts):
            if not (spec_part.startswith("{") and spec_part.endswith("}")) and spec_part != req_part:
                return False
        return True
