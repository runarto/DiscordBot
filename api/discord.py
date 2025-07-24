

def get_members(bot):
    """Fetches all non-bot members from all guilds the bot is in."""
    members = []
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                members.append(member)
    return members

def get_member(bot, user_id):
    """Fetches a specific member by user_id from all guilds the bot is in."""
    for guild in bot.guilds:
        for member in guild.members:
            if member.id == user_id and not member.bot:
                return member
    return None

def get_emojis(bot):
    """Fetches all emojis from all guilds the bot is in."""
    emojis = []
    for guild in bot.guilds:
        for emoji in guild.emojis:
            emojis.append(emoji)
    return emojis

def get_roles(bot):
    """Fetches all roles from all guilds the bot is in, excluding @everyone and roles with position > 120."""
    roles = []
    for guild in bot.guilds: 
        for role in guild.roles:
            if role.position <= 120 or role.name != "@everyone":
                roles.append(role)
    return roles