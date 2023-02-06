import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from main import Bot
from exceptions import NotEnoughPlayers, ToManyPlayers, PlayerNotFound

class Game(commands.GroupCog, name="game"):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="play")
    async def play(
            self,
            interaction: discord.Interaction,
            game_name: str,
            bet: Optional[app_commands.Range[int, 10]],
            player_two: Optional[discord.User],
            player_three: Optional[discord.User],
            player_four: Optional[discord.User],
            player_five: Optional[discord.User],
            player_six: Optional[discord.User],
            player_seven: Optional[discord.User],
            player_eight: Optional[discord.User],
    ) -> None:
        
        player_one = interaction.user.id

        players = [interaction.user, player_two, player_three, player_four, player_five, player_six, player_seven, player_eight]
        players = [player.id for player in players if player != None]
        
        game_admin = self.bot.game_admin
        
        # Instead of using if statments both in this function and in called functions
        # I decided to raise exceptions in called funcs and catch them here so I have
        # access to the interaction object and it dosen't need to be passed around and
        # I dont have a tone of if statments
        try:
            game_admin.check_game_details(game_name=game_name, player_count=len(players))
        except ModuleNotFoundError:
            return await interaction.response.send_message("Game not found")
        except NotEnoughPlayers as e:
            return await interaction.response.send_message(str(e))
        except ToManyPlayers as e:
            return await interaction.response.send_message(str(e))
        except Exception as e:
            # TODO add error loging here
            print(e)
            return await interaction.response.send_message('Unknown error')

            
            
        try:
            await game_admin.initialize_game(game_name, bet if bet else 0, player_one, players)
            return await interaction.response.send_message('Game request processed successfully')
        except PlayerNotFound:
            return await interaction.response.send_message('Error getting one of the players')
        except Exception as e:
            # TODO add error loging here
            print(e)
            return await interaction.response.send_message('Unknown error')
            


        

    # @play.autocomplete('game')
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

async def setup(bot: Bot) -> None:
  await bot.add_cog(Game(bot))