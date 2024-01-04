import random
import string
from datetime import timedelta
from random import randint
from typing import List, Literal

import discord
from discord import app_commands
from discord.ext import commands

from bot import Bot
from data_types import DiscordMessage, GameId, UserId
from data_wrappers.game_status import GameStatus
from data_wrappers.user_status import UserStatus
from data_wrappers.utils import RedisDb
from game_handling.game_module_loading import GameModuleLoading
from user_interfaces.game_embeds import game_info_embed
from user_interfaces.game_views import EmbedCycle, GameConfirm, GameSelect


class TestingStateGeneration:
    # TODO move this to area that can be used by all tests
    """Used to generate fake state for testing purposes"""

    def __init__(self) -> None:
        pass

    @staticmethod
    def create_game_id():
        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

    @staticmethod
    def create_game_state(
        user_one=randint(1, 10000), state: Literal[0, 1, 2] = 0, game="Tic Tac Toe"
    ) -> GameStatus.Game:
        """Creates fake game status"""

        game_details = GameModuleLoading.get_game_module(game).get_details()

        fake_users = {
            str(randint(1, 10000)): f"user{x}"
            for x in range(game_details.max_users - 2)
        }

        user_id_list: List[UserId] = [int(x) for x in list(fake_users.keys())]

        confirmed_users = user_id_list if state != 0 else []

        user_id_list.append(user_one)
        fake_users[str(user_one)] = "user1"

        return GameStatus.Game(
            state, game, user_one, fake_users, user_id_list, confirmed_users
        )


class Debug(commands.GroupCog, name="debug"):
    """Cog used to manipulate data and send items for testing purposes"""

    def __init__(self) -> None:
        super().__init__()

    ui_testing = app_commands.Group(name="ui", description="testing for UI elements")

    @ui_testing.command(
        name="send-game-confirm", description="Send yourself a comfirm message"
    )
    async def send_game_confirm(
        self,
        interaction: discord.Interaction,
    ) -> None:
        fake_game = TestingStateGeneration.create_game_state(interaction.user.id)

        async def test_accept():
            print("accept")

        async def test_reject():
            print("reject")

        await interaction.user.send(
            embed=game_info_embed(
                interaction.user.id,
                "Test",
                fake_game,
                GameModuleLoading.get_game_module(
                    fake_game.game_module_name
                ).get_details(),
                footer_message="Test",
            ),
            view=GameConfirm(test_accept, test_reject),
        )

        await interaction.response.send_message(content="Done")

    @ui_testing.command(
        name="send-game-select", description="Send yourself a game select message"
    )
    async def send_game_select(
        self,
        interaction: discord.Interaction,
    ) -> None:
        async def test_func(game_id: GameId, user_id: UserId):
            return DiscordMessage(f"{game_id} {user_id}")

        abc = {
            str(game_number): TestingStateGeneration.create_game_state(
                interaction.user.id
            )
            for game_number in range(2, 10)
        }

        await interaction.response.send_message(
            view=GameSelect(interaction.user.id, abc, test_func, "Select game")
        )

    @ui_testing.command(
        name="send-embed-cycle", description="Send yourself a embed cycle"
    )
    async def send_embed_cycle(
        self,
        interaction: discord.Interaction,
    ) -> None:
        test_data = []

        for embed_number in range(randint(2, 6)):
            new_embed = discord.Embed(title=str(embed_number))

            test_data.append([new_embed, embed_number])

        await interaction.response.send_message(
            view=EmbedCycle(test_data), embed=test_data[0][0]
        )

    @app_commands.command(
        name="add-accepted-fake-games", description="adds fake game's to user."
    )
    async def fill_games(
        self, interaction: discord.Interaction, amount: int = 6
    ) -> None:
        """Should not be used as real games as users in game don't exists this means not having them unqueued and things like that"""

        user_status = await UserStatus.get(interaction.user.id)

        active_game_offset = 0
        if user_status:
            active_game_offset = len(user_status.active_games)

        for _game_num in range(amount):
            state = 1
            if (
                _game_num + active_game_offset
                < UserStatus._UserStatus__max_active_games
            ):
                state = 2

            game_state = TestingStateGeneration.create_game_state(
                user_one=interaction.user.id, state=state
            )

            game_id = await GameStatus.add(game_state, timedelta(minutes=50))

            for user_id in game_state.all_users:
                await UserStatus.join_game(user_id, game_id)

        await interaction.response.send_message(content="Done")

    @app_commands.command(
        name="clear-fake-games",
        description="Removes all games from a user but not other the users in the game",
    )
    async def clear_games(self, interaction: discord.Interaction):
        user_sfs = await UserStatus.get(interaction.user.id)

        if user_sfs:
            for game_id in user_sfs.active_games + user_sfs.queued_games:
                await GameStatus.delete(game_id)
                await UserStatus.clear_game(game_id, [interaction.user.id])

    @app_commands.command(name="flush-redis", description="Runs flush db command")
    async def flush(self, interaction: discord.Interaction) -> None:
        await RedisDb.flush_db()
        await interaction.response.send_message(content="Done")

    @app_commands.command(
        name="set-game-expire", description="Changes the expire time of the game"
    )
    async def set_game_expire(
        self, interaction: discord.Interaction, game_id: GameId, seconds: int
    ):
        await GameStatus.set_expiry(game_id, timedelta(seconds=seconds))
        await interaction.response.send_message("Done")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Debug())
