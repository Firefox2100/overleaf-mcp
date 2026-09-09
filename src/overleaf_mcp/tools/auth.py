from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from .utils import get_app_context, get_auth_component, mounted_lifespan

auth_mcp = FastMCP("auth", lifespan=mounted_lifespan)


@auth_mcp.tool(
    annotations=ToolAnnotations(
        title="Refresh Authentication",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def refresh_authentication(ctx: Context) -> dict[str, bool | str]:
    """
    Replace the current Overleaf session by logging out and signing in again.
    If remote logout fails because the session is already invalid, the locally
    stored session is still cleared before login is attempted.
    """
    session, remote_logout_succeeded = await get_auth_component(ctx).refresh()
    get_app_context(ctx).overleaf_session = session

    return {
        "authenticated": True,
        "email": session.email,
        "remote_logout_succeeded": remote_logout_succeeded,
    }
