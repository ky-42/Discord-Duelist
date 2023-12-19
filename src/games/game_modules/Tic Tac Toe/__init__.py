import os
from typing import Type

import discord

from data_types import DiscordMessage, GameId, UserId
from games.utils import GameInfo, GameModule, GameModuleDetails, get_game_info

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
            min_players=2,
            max_players=2,
            thumbnail_file_path=f"{os.path.dirname(__file__)}/images/thumb.jpg",
        )

    @staticmethod
    @get_game_info
    async def start_game(
        game_info: GameInfo[GameModule.GameState, None],
        game_id: GameId,
    ):
        game_state = game_info.GameState

        game_data = TicTacToeData(
            active_player=game_state.all_players[0],
            player_order=game_state.all_players,
            player_square_type={
                str(game_state.all_players[0]): 1,
                str(game_state.all_players[1]): 2,
            },
            active_board=[[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        )

        await GameModule.store_data(game_id, game_data)

        # Send notification to first player
        await GameModule.send_notification(game_id, game_data.active_player)

    @staticmethod
    @get_game_info
    async def reply(
        game_info: GameInfo[GameModule.GameState, TicTacToeData],
        game_id: GameId,
        user_id: UserId,
    ):
        game_data = game_info.GameData

        if game_data.active_player == user_id:
            return DiscordMessage(
                content=f"Press a button to play your move! You are {'x' if game_data.player_square_type[str(user_id)] == 2 else 'o'}",
                view=TicTacToeView(game_id, game_data, TicTacToe.play_move),
            )
        else:
            return DiscordMessage(content="It's not your turn!")

    @staticmethod
    @get_game_info
    async def play_move(
        game_info: GameInfo[GameModule.GameState, TicTacToeData],
        game_id: GameId,
        row: int,
        column: int,
        interaction: discord.Interaction,
    ):
        await GameModule.remove_notification(game_id, interaction.user.id)

        game_data = game_info.GameData

        # Updates the board with the move
        game_data.active_board[row][column] = game_data.player_square_type[
            str(game_data.active_player)
        ]

        if (winner := check_win(game_data.active_board)) != 0:
            if winner != -1:
                await TicTacToe.end_game(game_id, [game_data.active_player])
            else:
                await TicTacToe.end_game(game_id, [])

        else:
            # Switches the active player
            game_data.active_player = (
                game_data.player_order[0]
                if game_data.active_player == game_data.player_order[1]
                else game_data.player_order[1]
            )

            await GameModule.store_data(game_id, game_data)
            await GameModule.send_notification(game_id, game_data.active_player)


def load() -> Type[GameModule]:
    return TicTacToe
