import discord
from discord import app_commands
from discord.ext import commands
from discord import ui
from bot import Bot
from games.game_handling.game_admin import GameAdmin
from games.game_handling.game_loading import GameLoading
from data_wrappers import UserStatus, GameStatus

class Game(commands.GroupCog, name="game"):
    def __init__(self) -> None:
        super().__init__()

    @app_commands.command(name="play")
    async def play(
            self,
            interaction: discord.Interaction,
            game_name: str,
    ) -> None:

        try:
            game_details = GameLoading.get_game(game_name).details

            # Sends out UI to select players this is done to avoid the users
            # having to type out the names in inital interaction
            # instead they can just select the users from a dropdown menu
            return await interaction.response.send_message(
                content="Please select the players you want to play with",
                ephemeral=True,
                view=GetPlayersClassInner(
                    game_name=game_name,
                    max=game_details.max_players,
                    min=game_details.min_players
                )
            )

        except Exception as e:
            return await interaction.response.send_message(e)

    @app_commands.command(name="reply")
    async def reply(
        self,
        interaction: discord.Interaction
    ):
        """
        When ran this will check if the user is in a game and if they are check if it is their turn
        and if it is send them the game UI
        """
        if (game_id := await UserStatus.check_in_game(interaction.user.id)):
            game_details = await GameStatus.get_game(game_id)
            await GameLoading.get_game(game_details.game).reply(game_id, interaction)
            
    # @app_commands.command(name="quit")
    # async def quit(self, interaction: discord.Interaction) -> None:
    #     await interaction.response.send_message("Hello from sub command 1", ephemeral=True)
            

class GetPlayersClassInner(ui.View):
    """
    Dropdown menu to select players for a game
    """

    def __init__(self, game_name: str, min: int, max: int):
        super().__init__()
        self.game_name = game_name

        self.user_select = ui.UserSelect(
            placeholder="Select a user please!",
            min_values=min-1,
            max_values=max-1,
            row=0,
            custom_id="user-select"
        )

        self.add_item(self.user_select)
        self.user_select.callback = self.user_select_callback

    async def user_select_callback(self, _interaction: discord.Interaction):
        pass

    @ui.button(label="Confirm Players", style=discord.ButtonStyle.green, row=1)
    async def confirm(self, interaction: discord.Interaction, _: ui.Button):
        player_one = interaction.user
        secondary_players = self.user_select.values

        # Double checks that the number of players is allowed. Just in case
        if GameLoading.check_game_details(self.game_name, len(secondary_players) + 1):
            self.stop()
            return await interaction.response.send_message(
                content="Problem with request",
                ephemeral=True
            )
        else:
            await GameAdmin.initialize_game(
                game_name=self.game_name,
                bet=0,
                player_one=player_one.id,
                secondary_player_ids=[
                    player.id for player in self.user_select.values
                ],
                player_names={
                    str(player.id): player.name for player in
                    (secondary_players + [player_one])
                }
            )

    @ui.button(label="Cancel Game", style=discord.ButtonStyle.red, row=1)
    async def cancel(self, interaction: discord.Interaction, _: ui.Button):
        self.stop()

    # # @play.autocomplete('game')
    # async def game_autocomplete(self, interaction: discord.Interaction, current: str):
    #     return [
    #         app_commands.Choice(name="abc", value="abc")
    #     ]

    # @app_commands.command(name="queue")
    # async def queue(self, interaction: discord.Interaction) -> None:
    #     await interaction.response.send_message("Hello from sub command 1", ephemeral=True)

    # @app_commands.command(name="status")
    # async def status(self, interaction: discord.Interaction) -> None:
    #     await interaction.response.send_message("Hello from sub command 1", ephemeral=True)



async def setup(bot: Bot) -> None:
    await bot.add_cog(Game())
