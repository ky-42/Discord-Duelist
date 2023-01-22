import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import redis.asyncio as redis
from psycopg_pool.pool_async import AsyncConnectionPool as PgConnectionPool

import game_handling
import user_handling


class Bot(commands.Bot):
    def __init__(
        self, 
        *args,
        **kwags
    ):
        super().__init__(*args, **kwags)
        self.game_admin = game_handling.GameAdmin(self)
        self.game_status = game_handling.GameStatus(self)

    async def setup_hook(self: commands.Bot):
        # # Creates connection pools for user db and game cache
        # self.game_data_pool = redis.Redis(db=0)
        # self.user_data_pool = PgConnectionPool(f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost/{os.getenv('POSTGRES_DB')}")
        
        # Loads all cogs
        await self.load_extension("cogs.game")
        await self.load_extension("cogs.tournament")
        await self.load_extension("cogs.money")

        # Syncs commands to mals server
        MY_GUILD = discord.Object(id=378743556526964737) 
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)


def main():
    #TODO update to only needed intents
    intents = discord.Intents.default()
    bot = Bot(command_prefix="/", intents=intents)

    # Gets token from env and runs bot with it
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Please set token in .env")

if __name__ == "__main__":
    main()
