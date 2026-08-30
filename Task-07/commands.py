import random

import discord
from discord.ext import commands

from config import DAILY_BERRIES
from economy import (
    daily_remaining,
    daily_reward,
    raid_attempt,
    raid_amount,
    raid_remaining,
    reduce_raid_loss,
)
from onepiece_api import OnePieceAPI


def format_berries(amount):
    return f"{amount:,} Berries"


def format_seconds(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m"

    if minutes:
        return f"{minutes}m {secs}s"

    return f"{secs}s"


class EconomyCommands(commands.Cog):
    def __init__(self, bot, database):
        self.bot = bot
        self.db = database
        self.one_piece = OnePieceAPI()

    # -------------------------
    # !bounty
    # -------------------------

    @commands.command()
    async def bounty(self, ctx):
        user = self.db.get_user(
            ctx.guild.id,
            ctx.author.id
        )

        await ctx.send(
            f"**{ctx.author.display_name}'s Bounty**\n"
            f"{format_berries(user['balance'])}"
        )

    # -------------------------
    # !setsail
    # -------------------------

    @commands.command()
    async def setsail(self, ctx):
        user = self.db.get_user(
            ctx.guild.id,
            ctx.author.id
        )

        remaining = daily_remaining(user["last_daily"])

        if remaining:
            await ctx.send(
                f"You already raided the merchant ship. "
                f"Come back in **{format_seconds(remaining)}**."
            )
            return

        lucky_bonus = self.db.get_active_effect(
            ctx.guild.id,
            ctx.author.id,
            "daily_bonus"
        )

        reward = daily_reward(
            DAILY_BERRIES,
            lucky_bonus
        )

        self.db.change_balance(
            ctx.guild.id,
            ctx.author.id,
            reward
        )

        self.db.set_last_daily(
            ctx.guild.id,
            ctx.author.id
        )

        self.db.log_transaction(
            ctx.guild.id,
            ctx.author.id,
            "daily",
            reward,
            description="Daily merchant ship reward"
        )

        if reward > DAILY_BERRIES:
            message = (
                f"The merchant ship was carrying twice the expected loot. "
                f"You received **{format_berries(reward)}**."
            )
        else:
            message = (
                f"You raided the merchant ship and received "
                f"**{format_berries(reward)}**."
            )

        await ctx.send(message)

    # -------------------------
    # !trade @user amount
    # -------------------------

    @commands.command()
    async def trade(
        self,
        ctx,
        member: discord.Member,
        amount: int,
    ):
        if member.bot:
            await ctx.send("You cannot trade with a bot.")
            return

        if member.id == ctx.author.id:
            await ctx.send("You cannot trade with yourself.")
            return

        if amount <= 0:
            await ctx.send("The trade amount must be positive.")
            return

        success = self.db.transfer(
            ctx.guild.id,
            ctx.author.id,
            member.id,
            amount
        )

        if not success:
            await ctx.send(
                "Trade failed. Check that you have enough Berries."
            )
            return

        await ctx.send(
            f"{ctx.author.mention} transferred "
            f"**{format_berries(amount)}** to "
            f"{member.mention}."
        )

    # -------------------------
    # !logpose
    # -------------------------

    @commands.command()
    async def logpose(self, ctx):
        await ctx.send(
            "The Log Pose is spinning..."
        )

        result = await self.one_piece.log_pose()
        print(result)

        if not result:
            await ctx.send(
                "The Log Pose malfunctioned. The Grand Line remains mysterious."
            )
            return

        if result["type"] == "character":
            bounty = result.get("bounty") or "Unknown"

            await ctx.send(
                f"**Log Pose Intel — Pirate Spotted**\n"
                f"Name: **{result['name']}**\n"
                f"Official bounty: **{bounty}**"
            )
        else:
            model = result.get("model", "Unknown")
            fruit_type = result.get("fruit_type", "Unknown")

            await ctx.send(
                f"**Log Pose Intel — Devil Fruit**\n"
                f"Fruit: **{result['name']}**\n"
                f"Type: **{fruit_type}**\n"
                f"Model: **{model}**"
            )

    # -------------------------
    # !shop
    # -------------------------

    @commands.command()
    async def shop(self, ctx):
        items = self.db.get_shop_items()

        embed = discord.Embed(
            title="Berry Broker Shop",
            description="Spend your Berries wisely.",
        )

        for item in items:
            embed.add_field(
                name=(
                    f"{item['name']} — "
                    f"{format_berries(item['cost'])}"
                ),
                value=item["description"],
                inline=False,
            )

        embed.set_footer(
            text="Use !buy <item> to purchase an item."
        )

        await ctx.send(embed=embed)

    # -------------------------
    # !inventory
    # -------------------------

    @commands.command()
    async def inventory(self, ctx):
        items = self.db.get_inventory(
            ctx.guild.id,
            ctx.author.id
        )

        if not items:
            await ctx.send(
                "Your inventory is empty. "
                "The Broker is disappointed."
            )
            return

        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Inventory"
        )

        for item in items:
            status = "ACTIVE" if item["status"] == "active" else "SPENT"

            embed.add_field(
                name=f"{item['name']} [{status}]",
                value=item["description"],
                inline=False,
            )

        await ctx.send(embed=embed)

    # -------------------------
    # !buy item
    # -------------------------

    @commands.command()
    async def buy(self, ctx, *, item_name: str):
        item = self.db.get_shop_item(item_name.strip())

        if not item:
            await ctx.send(
                "That item is not sold by the Berry Broker. "
                "Use `!shop` to see the catalogue."
            )
            return

        success = self.db.buy_item(
            ctx.guild.id,
            ctx.author.id,
            item["id"],
            item["cost"]
        )

        if not success:
            await ctx.send(
                f"You cannot afford **{item['name']}**."
            )
            return

        await ctx.send(
            f"You purchased **{item['name']}** for "
            f"**{format_berries(item['cost'])}**."
        )

    # -------------------------
    # !worstgeneration
    # -------------------------

    @commands.command()
    async def worstgeneration(self, ctx):
        rows = self.db.leaderboard(
            ctx.guild.id,
            limit=5
        )

        if not rows:
            await ctx.send("The leaderboard is empty.")
            return

        lines = []

        for position, row in enumerate(rows, start=1):
            member = ctx.guild.get_member(row["user_id"])

            if member:
                name = member.display_name
            else:
                name = f"Unknown Pirate ({row['user_id']})"

            lines.append(
                f"**{position}. {name}** — "
                f"{format_berries(row['balance'])}"
            )

        embed = discord.Embed(
            title="The Worst Generation",
            description="\n".join(lines),
        )

        await ctx.send(embed=embed)

    # -------------------------
    # !raid @user
    # -------------------------

    @commands.command()
    async def raid(
        self,
        ctx,
        target: discord.Member,
    ):
        if target.bot:
            await ctx.send("Bots have no pirate stash.")
            return

        if target.id == ctx.author.id:
            await ctx.send(
                "You cannot raid your own ship."
            )
            return

        attacker = self.db.get_user(
            ctx.guild.id,
            ctx.author.id
        )

        defender = self.db.get_user(
            ctx.guild.id,
            target.id
        )

        remaining = raid_remaining(attacker["last_raid"])

        if remaining:
            await ctx.send(
                f"Your ship is still recovering from the last raid. "
                f"Try again in **{format_seconds(remaining)}**."
            )
            return

        self.db.set_last_raid(
            ctx.guild.id,
            ctx.author.id
        )

        raid_bonus = self.db.get_active_effect(
            ctx.guild.id,
            ctx.author.id,
            "raid_bonus"
        )

        success = raid_attempt(raid_bonus)

        if not success:
            await ctx.send(
                f"{target.mention} spotted your ship before you could "
                f"reach the treasure. The raid failed."
            )
            return

        amount = raid_amount(defender["balance"])

        if amount <= 0:
            await ctx.send(
                f"{target.mention}'s stash is too small to raid."
            )
            return

        # Seastone protects the defender from part of the loss.
        shield_bonus = self.db.get_active_effect(
            ctx.guild.id,
            target.id,
            "raid_shield"
        )

        protected_amount = reduce_raid_loss(
            amount,
            shield_bonus
        )

        actual_loss = self.db.raid_transfer(
            ctx.guild.id,
            ctx.author.id,
            target.id,
            protected_amount
        )

        if actual_loss <= 0:
            await ctx.send(
                "The raid found an empty treasure chest."
            )
            return

        await ctx.send(
            f"{ctx.author.mention} successfully raided "
            f"{target.mention} and stole "
            f"**{format_berries(actual_loss)}**."
        )

    # -------------------------
    # !history
    # -------------------------

    @commands.command()
    async def history(self, ctx):
        rows = self.db.get_history(
            ctx.guild.id,
            ctx.author.id,
            limit=10
        )

        if not rows:
            await ctx.send(
                "The Broker has no transactions recorded for you."
            )
            return

        lines = []

        for row in rows:
            amount = row["amount"]

            if amount >= 0:
                amount_text = f"+{format_berries(amount)}"
            else:
                amount_text = format_berries(amount)

            lines.append(
                f"`{row['transaction_type']}` "
                f"{amount_text} — "
                f"{row['description'] or 'No description'}"
            )

        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Ledger",
            description="\n".join(lines),
        )

        await ctx.send(embed=embed)

    # -------------------------
    # Error handling
    # -------------------------

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Missing an argument. Check the command syntax."
            )

        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                "Invalid argument. For example: "
                "`!trade @Pirate 500`."
            )