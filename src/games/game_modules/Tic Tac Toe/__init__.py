import os
from typing import Type

import discord

from data_types import GameId
from games.utils import Game, GameDetails, GameInfo, get_game_info

from .data import TicTacToeData
from .helpers import check_win
from .views import TicTacToeView


class TicTacToe(Game):
    """
    Game of Tic Tac Toe
    """

    @staticmethod
    def get_details() -> GameDetails:
        return GameDetails(
            min_players=2,
            max_players=2,
            thumbnail_file_path=f"{os.path.dirname(__file__)}/images/thumb.jpg",
        )

    @staticmethod
    @get_game_info
    async def start_game(
        game_info: GameInfo[Game.GameState, None],
        game_id: GameId,
    ):
        game_state = game_info.GameState

        game_data = TicTacToeData(
            current_player=game_state.all_players[0],
            player_order=game_state.all_players,
            player_square_type={
                str(game_state.all_players[0]): 1,
                str(game_state.all_players[1]): 2,
            },
            current_board=[[0, 0, 0], [0, 0, 0], [0, 0, 0]],
        )

        await Game.store_data(game_id, game_data)

        # Send notification to first player
        await Game.send_notification(game_id, game_data.current_player)

    @staticmethod
    @get_game_info
    async def reply(
        game_info: GameInfo[Game.GameState, TicTacToeData],
        game_id: GameId,
        interaction: discord.Interaction,
    ):
        game_data = game_info.GameData

        if game_data.current_player == interaction.user.id:
            await interaction.response.send_message(
                content="Press a button to play your move!",
                delete_after=60 * 15,
                view=TicTacToeView(game_id, game_data, TicTacToe.play_move),
            )

    @staticmethod
    @get_game_info
    async def play_move(
        game_info: GameInfo[Game.GameState, TicTacToeData],
        game_id: GameId,
        row: int,
        column: int,
        interaction: discord.Interaction,
    ):
        game_data = game_info.GameData

        # Updates the board with the move
        game_data.current_board[row][column] = game_data.player_square_type[
            str(game_data.current_player)
        ]

        if check_win(game_data.current_board) != 0:
            await TicTacToe.end_game(game_id, [game_data.current_player])
        else:
            # Switches the current player
            game_data.current_player = (
                game_data.player_order[0]
                if game_data.current_player == game_data.player_order[1]
                else game_data.player_order[1]
            )

            await Game.store_data(game_id, game_data)
            await Game.send_notification(game_id, game_data.current_player)


def load() -> Type[Game]:
    return TicTacToe
