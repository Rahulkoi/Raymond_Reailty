from app.mcp.registry import MCPTool, PermissionLevel


def ping_handler(payload: dict):
    return {
        "message": "pong",
        "received_payload": payload
    }


ping_tool = MCPTool(
    name="ping",
    permission=PermissionLevel.READ,
    handler=ping_handler
)
