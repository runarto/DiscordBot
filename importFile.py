import discord
import logic
import asyncio
import json
import file_functions
from dateutil import parser
import perms
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from functools import partial
from collections import defaultdict
from datetime import datetime
from apscheduler.jobstores.base import JobLookupError
from discord.ext import commands
import os
import requests
from datetime import timedelta, datetime
import pytz  # This library is used for time zone conversions
from perms import API_TOKEN
from dateutil import parser
from discord.ext import commands




channel_id = perms.CHANNEL_ID
intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True
client = discord.Client(intents=intents)
scheduler = AsyncIOScheduler()
