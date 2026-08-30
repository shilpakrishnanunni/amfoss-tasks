import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

DATABASE_PATH = "data/berry_broker.db"

STARTING_BERRIES = 1_000
DAILY_BERRIES = 500

# Economy cooldowns, in seconds.
DAILY_COOLDOWN = 24 * 60 * 60
RAID_COOLDOWN = 30 * 60

# Raid configuration.
RAID_SUCCESS_CHANCE = 0.45
RAID_MIN_PERCENT = 0.10
RAID_MAX_PERCENT = 0.30

# The bot never allows a raid to completely empty someone.
RAID_MIN_REMAINING = 100