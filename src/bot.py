from datetime import timedelta

import discord
from discord.ext import commands

from data_wrappers.game_status import GameStatus
from exceptions import PlayerNotFound

"""
This file functions as a place to store the global bot var
this is so that not everyclass needs and instance of it to access
it as it needs to be used all over
"""


def create_intents() -> discord.Intents:
    intents = discord.Intents()
    intents.dm_messages = True
    intents.dm_reactions = True
    intents.members = True
    return intents


class Bot(commands.Bot):
    """
    Custom Bot class is needed to add cogs and overide methods
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_requested_expiry = timedelta(minutes=15)
        self.game_no_move_expiry = timedelta(days=2)

    async def setup_hook(self: commands.Bot):
        # Loads all cogs
        await self.load_extension("cogs.game")
        await self.load_extension("cogs.tournament")
        await self.load_extension("cogs.money")
        await self.load_extension("cogs.task")

        # Syncs commands to mals server
        MY_GUILD = discord.Object(id=715439787288428605)
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    # Custom get_user that raises PlayerNotFound and trys to fetch user as well
    async def get_user(self, user_id: int) -> discord.User:
        # Trys the local cache
        if user_object := super().get_user(user_id):
            return user_object
        else:
            # Trys requesting for user
            if fetched_user := await super().fetch_user(user_id):
                return fetched_user
            else:
                raise PlayerNotFound(user_id)

    # Custom get_dm_channel to create a dm if it does not exists
    async def get_dm_channel(self, user_id: int) -> discord.DMChannel:
        userToDm = await self.get_user(user_id)

        if not userToDm.dm_channel:
            return await userToDm.create_dm()
        else:
            return userToDm.dm_channel


intents = create_intents()
bot = Bot(
    command_prefix="/",
    intents=intents,
    member_cache_flags=discord.MemberCacheFlags.from_intents(intents),
)
