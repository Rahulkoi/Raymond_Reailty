from app.mcp.registry import TOOL_REGISTRY
from app.utils.config import config


class MCPServer:
    def __init__(self):
        self.enabled = config.mcp.ENABLED

    def execute(self, tool_name: str, payload: dict):
        if not self.enabled:
            raise RuntimeError("MCP is disabled")

        tool = TOOL_REGISTRY.get(tool_name)
        if not tool:
            raise RuntimeError(f"Tool '{tool_name}' not found")

        # Permission enforcement (basic for now)
        if tool.permission == "write" and not config.mcp.ALLOW_WRITES:
            raise RuntimeError("Write operations are disabled")

        return tool.handler(payload)
