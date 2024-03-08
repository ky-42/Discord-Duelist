from datetime import timedelta
from random import randint
from typing import Dict, List, Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from bot import Bot
from data_types import DiscordMessage, GameId, UserId
from data_wrappers.game_status import GameStatus
from data_wrappers.user_status import UserStatus
from data_wrappers.utils import RedisDb
from game_modules import GameModuleLoading
from user_interfaces.game_embeds import game_info_embed, game_summary_embed
from user_interfaces.game_views import EmbedCycle, GameSelect, GetUsers, InviteOptions


class Debug(commands.GroupCog, name="debug"):
    """Cog used to manipulate data and test ui elements"""

    def __init__(self) -> None:
        super().__init__()

    helpers = app_commands.Group(name="helpers", description="Helper commands")
    ui_testing = app_commands.Group(name="ui", description="testing for UI elements")

    @helpers.command(
        name="set-game-expire", description="Changes the expire time of the game"
    )
    async def set_game_expire(
        self, interaction: discord.Interaction, game_id: GameId, seconds: int
    ):
        await GameStatus.set_expiry(game_id, timedelta(seconds=seconds))
        await interaction.response.send_message("Done")

    @helpers.command(
        name="add-accepted-fake-games", description="Adds fake games to user"
    )
    async def fill_games(
        self, interaction: discord.Interaction, amount: int = 6
    ) -> None:
        """Adds fake games to the calling user.

        These games will cause errors if they are interacted with.
        """

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

            game_state = GameStatus.Game.generate_fake(
                state,
                "Testing_Game",
                randint(2, 7),
                0,
                [(interaction.user.id, interaction.user.name)],
            )

            game_id = await GameStatus.add(game_state, timedelta(minutes=50))

            for user_id in game_state.all_users:
                await UserStatus.join_game(user_id, game_id)

        await interaction.response.send_message(content="Done")

    @helpers.command(
        name="clear-games",
        description="Removes all games from a user. Should be used after adding fake games",
    )
    async def clear_games(self, interaction: discord.Interaction):
        user = await UserStatus.get(interaction.user.id)

        if user:
            for game_id in user.active_games + user.queued_games:
                await GameStatus.delete(game_id)
                await UserStatus.clear_game([interaction.user.id], game_id)

        await interaction.response.send_message(content="Done")

    @helpers.command(name="flush-redis", description="Runs flush db command on redis.")
    async def flush(self, interaction: discord.Interaction) -> None:
        await RedisDb.flush_db()
        await interaction.response.send_message(content="Done")

    @ui_testing.command(
        name="send-get-users",
        description="Send yourself a get users message. Should be used in a server",
    )
    async def send_get_users(
        self,
        interaction: discord.Interaction,
        min_users_to_pick: Optional[int],
        max_users_to_pick: Optional[int],
    ) -> None:
        async def test_func(users: Dict[str, str]) -> DiscordMessage:
            print(users)
            return DiscordMessage("Done")

        min_users = 1 if min_users_to_pick is None else min_users_to_pick
        max_users = min_users if max_users_to_pick is None else max_users_to_pick
        await interaction.response.send_message(
            view=GetUsers(interaction.user.id, min_users, max_users, test_func)
        )

    @ui_testing.command(
        name="send-game-confirm", description="Send yourself a comfirm message"
    )
    async def send_game_confirm(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Tests game_info_embed and InviteOptions"""

        fake_game = GameStatus.Game.generate_fake(
            0, "Tic Tac Toe", randint(3, 6), randint(1, 3)
        )

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
            view=InviteOptions(test_accept, test_reject),
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

        generated_games = {
            str(game_number): GameStatus.Game.generate_fake(
                2,
                "Testing_Game",
                randint(2, 7),
                0,
                [(interaction.user.id, interaction.user.name)],
            )
            for game_number in range(2, 10)
        }

        await interaction.response.send_message(
            view=GameSelect(
                interaction.user.id, generated_games, test_func, "Select game"
            )
        )

    @ui_testing.command(
        name="send-embed-cycle", description="Send yourself a embed cycle"
    )
    async def send_embed_cycle(
        self,
        interaction: discord.Interaction,
    ) -> None:
        test_embeds: List[Tuple[discord.Embed, str]] = []

        for embed_number in range(randint(2, 6)):
            new_embed = discord.Embed(title=str(embed_number))

            test_embeds.append((new_embed, str(embed_number)))

        await interaction.response.send_message(
            view=EmbedCycle(test_embeds), embed=test_embeds[0][0]
        )

    @ui_testing.command(
        name="send-game-summary", description="Send yourself a game summary message"
    )
    async def send_game_summary(
        self,
        interaction: discord.Interaction,
    ) -> None:
        game = GameStatus.Game.generate_fake(
            2,
            "Testing_Game",
            randint(2, 7),
            0,
            [(interaction.user.id, interaction.user.name)],
        )

        await interaction.response.send_message(
            embed=game_summary_embed(
                [interaction.user.name],
                [
                    username
                    for username in game.usernames.values()
                    if username != interaction.user.name
                ],
                game,
                ending_reason="Test",
            )
        )


async def setup(bot: Bot) -> None:
    await bot.add_cog(Debug())
