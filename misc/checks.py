from discord import app_commands, Interaction
from misc.constants import ADMIN_USER_IDS


def is_admin():
    """Allows users with Manage Messages permission or those in ADMIN_USER_IDS."""
    async def predicate(interaction: Interaction) -> bool:
        if interaction.user.id in ADMIN_USER_IDS:
            return True
        return interaction.user.guild_permissions.manage_messages
    return app_commands.check(predicate)


def admin_command(**default_permission_kwargs):
    """
    Decorator combining default_permissions (for Discord UI visibility)
    with is_admin() (to also allow ADMIN_USER_IDS regardless of role).
    Usage: @admin_command(manage_messages=True)
    """
    def decorator(func):
        func = app_commands.default_permissions(**default_permission_kwargs)(func)
        func = is_admin()(func)
        return func
    return decorator
