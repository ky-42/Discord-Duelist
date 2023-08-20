import discord
from discord import app_commands
from discord.ext import commands


class Money(commands.GroupCog, name="money"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="bal")
    async def bal(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Hello from sub command 1", ephemeral=True
        )

    @app_commands.command(name="pay")
    async def pay(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "Hello from sub command 1", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Money(bot))
