import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from exceptions.general_exceptions import PlayerNotFound

class Bot(commands.Bot):
    async def setup_hook(self: commands.Bot):
        # # Creates connection pools for user db and game cache

        # Loads all cogs
        await self.load_extension("cogs.game")
        await self.load_extension("cogs.tournament")
        await self.load_extension("cogs.money")

        # Syncs commands to mals server
        MY_GUILD = discord.Object(id=715439787288428605)
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    async def get_user(self, user_id: int) -> discord.User:
        if (user_object := super().get_user(user_id)):
            return user_object
        else:
            if (fetched_user := await super().fetch_user(user_id)):
                return fetched_user
            else:
                raise PlayerNotFound(user_id)

    async def get_dm_channel(self, user_id: int) -> discord.DMChannel:

        userToDm = await self.get_user(user_id)

        if not userToDm.dm_channel:
            return await userToDm.create_dm()
        else:
            return userToDm.dm_channel


def create_intents() -> discord.Intents:
    intents = discord.Intents()
    intents.dm_messages = True
    intents.dm_reactions = True
    intents.members = True
    return intents


def main():
    intents = create_intents()
    bot = Bot(command_prefix="/", intents=intents,
              member_cache_flags=discord.MemberCacheFlags.from_intents(intents))

    # Gets token from env and runs bot with it
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Please set DISCORD_TOKEN in .env")


if __name__ == "__main__":
    main()
