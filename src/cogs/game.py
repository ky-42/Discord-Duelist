import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

class Game(commands.GroupCog, name="game"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="play")
    async def play(
            self,
            interaction: discord.Interaction,
            game: str,
            player_one: discord.User,
            bet: Optional[app_commands.Range[int, 10]],
            player_two: Optional[discord.User],
            player_three: Optional[discord.User],
            player_four: Optional[discord.User],
            player_five: Optional[discord.User],
            player_six: Optional[discord.User],
            player_seven: Optional[discord.User],
            player_eight: Optional[discord.User],
    ) -> None:
        players = [player_one, player_two, player_three, player_four, player_five, player_six, player_seven, player_eight]
        players = [player for player in players if player != None]
        game_handler.get_game_details(game)
    
        await interaction.response.send_message("Hello from sub command 1", ephemeral=True)

    @play.autocomplete('game')
    async def game_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name="abc", value="abc")
        ]


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

