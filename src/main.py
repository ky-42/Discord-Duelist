import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

class Bot(commands.Bot):
    async def setup_hook(self: commands.Bot):
        # Loads all cogs
        await self.load_extension("cogs.game")
        await self.load_extension("cogs.tournament")
        await self.load_extension("cogs.money")

        # Syncs commands to mals server
        MY_GUILD = discord.Object(id=378743556526964737) 
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

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

