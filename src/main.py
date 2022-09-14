import discord
from discord.ext import commands

MY_GUILD = discord.Object(id=378743556526964737) 

class Bot(commands.Bot):
    async def setup_hook(self: commands.Bot):
        await self.load_extension("cogs.game")
        # await self.load_extension("cogs.tournament")
        # await self.load_extension("cogs.money")
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

#TODO update to only needed intents

intents = discord.Intents.default()
bot = Bot(command_prefix="/", intents=intents)

bot.run('MTAwNzgyOTY3MDQyNDc1NjI5NQ.G5n_0Z.xvS5biMQ5eUkoCHuBGkn10hRe-9J5ghts1Ugss')
