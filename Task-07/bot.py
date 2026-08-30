import discord
from discord.ext import commands
import logging

from config import DISCORD_TOKEN
from database import Database
from commands import EconomyCommands


if not DISCORD_TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing from the .env file."
    )

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

class BerryBroker(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()

        # Required for prefix commands such as !bounty.
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=commands.DefaultHelpCommand(
                no_category="Berry Broker"
            ),
        )

        self.database = Database()

    async def setup_hook(self):
        await self.add_cog(
            EconomyCommands(
                self,
                self.database
            )
        )

    async def on_ready(self):
        print(
            f"Logged in as {self.user} "
            f"(ID: {self.user.id})"
        )


bot = BerryBroker()
bot.run(DISCORD_TOKEN, log_handler=handler)