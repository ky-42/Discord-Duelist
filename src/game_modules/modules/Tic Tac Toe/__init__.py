import os
from typing import Type

import discord

from data_types import DiscordMessage, GameId, UserId
from game_modules.game_classes import GameModule, GameModuleDetails
from game_modules.utils import GameInfo, get_game_info

from .data import TicTacToeData
from .helpers import check_win
from .views import TicTacToeView


class TicTacToe(GameModule):
    """
    Game of Tic Tac Toe
    """

    @staticmethod
    def get_details() -> GameModuleDetails:
        return GameModuleDetails(
            min_users=2,
            max_users=2,
            thumbnail_file_path=f"{os.path.dirname(__file__)}/images/thumb.jpg",
        )

    @staticmethod
    @get_game_info
    async def start_game(
        game_info: GameInfo[GameModule.GameStatus, None],
        game_id: GameId,
    ):
        game_state = game_info.GameStatus

        game_data = TicTacToeData(
            active_user=game_state.all_users[0],
            user_order=game_state.all_users,
            user_square_type={
                str(game_state.all_users[0]): 1,
                str(game_state.all_users[1]): 2,
            },
            active_board=[[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        )

        await GameModule.store_game_data(game_id, game_data)

        # Send notification to first user
        await GameModule.send_notification(game_id, game_data.active_user)

    @staticmethod
    @get_game_info
    async def reply(
        game_info: GameInfo[GameModule.GameStatus, TicTacToeData],
        game_id: GameId,
        user_id: UserId,
    ):
        game_data = game_info.GameData

        if game_data.active_user == user_id:
            return DiscordMessage(
                content=f"Press a button to play your move! You are {'x' if game_data.user_square_type[str(user_id)] == 2 else 'o'}",
                view=TicTacToeView(game_id, game_data, TicTacToe.play_move),
            )
        else:
            return DiscordMessage(content="It's not your turn!")

    @staticmethod
    @get_game_info
    async def play_move(
        game_info: GameInfo[GameModule.GameStatus, TicTacToeData],
        game_id: GameId,
        row: int,
        column: int,
        interaction: discord.Interaction,
    ):
        await GameModule.remove_notification(game_id, interaction.user.id)

        game_data = game_info.GameData

        # Updates the board with the move
        game_data.active_board[row][column] = game_data.user_square_type[
            str(game_data.active_user)
        ]

        if (winner := check_win(game_data.active_board)) != 0:
            if winner != -1:
                await TicTacToe.game_over(game_id, [game_data.active_user])
            else:
                await TicTacToe.game_over(game_id, [])

        else:
            # Switches the active user
            game_data.active_user = (
                game_data.user_order[0]
                if game_data.active_user == game_data.user_order[1]
                else game_data.user_order[1]
            )

            await GameModule.store_game_data(game_id, game_data)
            await GameModule.send_notification(game_id, game_data.active_user)


def load() -> Type[GameModule]:
    return TicTacToe
