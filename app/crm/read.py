from app.mcp.registry import MCPTool, PermissionLevel, register_tool

def get_account_details(account_id: str = "default"):
    return {
        "account_id": account_id,
        "name": "Acme Corp",
        "status": "Active",
        "plan": "Enterprise"
    }

register_tool(
    MCPTool(
        name="get_account_details",
        permission=PermissionLevel.READ,
        handler=get_account_details
    )
)
