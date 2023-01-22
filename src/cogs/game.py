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
        players = [player.id for player in players if player != None]
        
        game_admin = self.bot.game_admin
        
        try:
            game_admin.check_game_details(game=game, player_count=len(players))
        except ModuleNotFoundError:
            await interaction.response.send_message("Game not found")


        



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

class Accept(discord.ui.View):
    def __init__(self):
        super().__init__()

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # interaction.client.
        await interaction.response.send_message('Game accepted', ephemeral=True)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Decline', style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('Game declined', ephemeral=True)
        self.stop()


bot = Bot()