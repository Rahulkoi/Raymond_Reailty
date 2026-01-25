from enum import Enum

class PermissionLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    SYSTEM = "system"


class MCPTool:
    def __init__(self, name: str, permission: PermissionLevel, handler):
        self.name = name
        self.permission = permission
        self.handler = handler


TOOL_REGISTRY: dict[str, MCPTool] = {}


def register_tool(tool: MCPTool):
    TOOL_REGISTRY[tool.name] = tool


def execute_tool(tool_name: str, arguments: dict):
    if tool_name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: {tool_name}")

    tool = TOOL_REGISTRY[tool_name]
    return tool.handler(**arguments)
