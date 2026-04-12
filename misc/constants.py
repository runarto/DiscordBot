# League configuration
LEAGUES = {
    "ELITE": {"id": 59, "name": "Eliteserien", "season": 2026, "slug": "eliteserien"},
    "OBOS": {"id": 203, "name": "OBOS-ligaen", "season": 2026, "slug": "1-divisjon"},
    "Cupen": {"id": 206, "name": "NM Cupen", "season": 2026, "slug": "nm-cupen"},
}
DEFAULT_LEAGUE = "ELITE"

# Default emojis for teams without custom emojis
DEFAULT_HOME_EMOJI = "🏠"
DEFAULT_AWAY_EMOJI = "✈️"

NON_ROLES = ["Sørveradministrator", "bot-fikler", "Norges Fotballforbund", "Tippekuppongmester"]
MAX_MESSAGE_LENGTH = 2000
MAX_ROLE_VALUE = 100

CHANNEL_ID = 1094933846383923320 #Kanal hvor meldinger skal sendes.
GUILD_ID = 1039825091430719559
ALLOWED_GUILDS = [GUILD_ID]

TEAMS = [
    "Kristiansund",
    "Tromsø", 
    "Brann",
    "Sarpsborg 08",
    "Viking",
    "Bodø/Glimt",
    "Odd",
    "Haugesund",
    "Sandefjord",
    "Rosenborg",
    "Strømsgodset",
    "Hamarkameratene",
    "Lillestrøm",
    "KFUM",
    "Fredrikstad",
    "Molde",
    "Moss",
    "Kongsvinger",
    "Bryne",
    "Raufoss",
    "Ranheim",
    "Jerv",
    "Skeid",
    "Stabæk",
    "Sogndal",
    "Vålerenga",
    "Start",
    "Aalesund",
    "Sandnes Ulf",
    "Åsane",
    "Lyn Fotball",
    "Hei",
]

TEAMS_NORSKE_NAVN = {
    "Kristiansund BK": "Kristiansund",
    "Tromso": "Tromsø",
    "Brann": "Brann",
    "Sarpsborg 08 FF": "Sarpsborg 08",
    "Viking": "Viking",
    "Bodo/Glimt": "Bodø/Glimt", #5/10
    "Odds Ballklubb": "Odd",
    "Haugesund": "Haugesund", #9/9
    "Sandefjord": "Sandefjord", #10/10
    "Rosenborg": "Rosenborg", #9/9
    "Stromsgodset": "Strømsgodset", #11/13
    "Ham-Kam": "Ham-Kam", #6/7
    "Lillestrom": "Lillestrøm",# > 9/11
    "KFUM Oslo": "KFUM", #4/4
    "Fredrikstad": "Fredrikstad", #11/11
    "Molde": "Molde", #5/5
    "Moss": "Moss",
    "Kongsvinger": "Kongsvinger",
    "Bryne": "Bryne",
    "Raufoss": "Raufoss",
    "Ranheim": "Ranheim",
    "jerv": "Jerv",
    "Skeid": "Skeid",
    "Stabaek": "Stabæk",
    "Sogndal": "Sogndal",
    "Valerenga": "Vålerenga",
    "Start": "Start",
    "Aalesund": "Aalesund",
    "Sandnes ULF": "Sandnes Ulf",
    "Asane": "Åsane"
}

TEAMS_EMOJI_ID = [
    "<:Brann:1039844066487185429>",
    "<:Glimt:1039831920978169857>",
    "<:Fredrikstad:1039945582917210162>",
    "<:Kristiansund:1039834384854941726>",
    "<:Lillestroem:1039835160125902908>",
    "<:Odd:1039839692373368872>",
    "<:Tromsoe:1039842401025527868>",
    "<:Rosenborg:1059898578883051561>",
    "<:Hamkam:1039832337032163358>",
    "<:Molde:1039836329502052444>",
    "<:KFUM:1039945755814805574>",
    "<:Stroemsgodset:1039841950079143937>",
    "<:Viking:1039842907894599760>",
    "<:Sandefjord:1039840813544378418>",
    "<:Haugesund:1039832977158443058>",
    "<:Bryne:1039945160374632489>",
    "<:Vaalerenga:1039843306043080735>"
]



