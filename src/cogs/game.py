import discord
from discord import app_commands
from discord.ext import commands

class Game(commands.GroupCog, name="game"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="play")
    async def play(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Hello from sub command 1", ephemeral=True)

    @app_commands.command(name="queue")
    async def queue(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Hello from sub command 1", ephemeral=True)

    @app_commands.command(name="status")
    async def status(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Hello from sub command 1", ephemeral=True)

    @app_commands.command(name="quit")
    async def quit(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Hello from sub command 1", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(Game(bot))

