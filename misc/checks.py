from discord import app_commands, Interaction
from misc.constants import ADMIN_USER_IDS


def is_admin():
    """Allows users with Manage Messages permission or those in ADMIN_USER_IDS."""
    async def predicate(interaction: Interaction) -> bool:
        if interaction.user.id in ADMIN_USER_IDS:
            return True
        return interaction.user.guild_permissions.manage_messages
    return app_commands.check(predicate)
