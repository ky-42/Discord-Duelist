"""Stores global custom bot instance"""

import os
from datetime import timedelta

import discord
from discord.ext import commands

from data_types import UserId
from exceptions import UserNotFound


class Bot(commands.Bot):
    """Custom Bot class is used to add cogs and overide methods"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_requested_expiry = timedelta(minutes=15)
        self.game_no_move_expiry = timedelta(days=2)

    async def setup_hook(self: commands.Bot):
        # Loads all cogs
        await self.load_extension("cogs.game")
        await self.load_extension("cogs.task")

        if os.getenv("TESTING"):
            await self.load_extension("cogs.debug")

        MY_GUILD = discord.Object(id=1186488380612157441)
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def get_user(self, user_id: UserId) -> discord.User:
        """Fetches a discord user object given their user id

        Raises:
            UserNotFound: If given user does not exists
        """

        # Trys the local cache
        if user_object := super().get_user(user_id):
            return user_object
        else:
            try:
                return await super().fetch_user(user_id)
            except:
                raise UserNotFound(user_id)

    async def get_dm_channel(self, user_id: int) -> discord.DMChannel:
        """Creates or fetchs a discord dm object for a given user id

        Raises:
            UserNotFound: If given user does not exists
        """
        userToDm = await self.get_user(user_id)

        # Checks for existing dm
        if not userToDm.dm_channel:
            return await userToDm.create_dm()
        else:
            return userToDm.dm_channel


intents = discord.Intents()
intents.dm_messages = True
intents.dm_reactions = True
intents.members = True
bot = Bot(
    command_prefix="/",
    intents=intents,
    member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
)
