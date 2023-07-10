import os
import discord
from dataclasses import dataclass
from ..utils import GameInfo, Game, load_game_data
from data_wrappers import GameStatus, GameData, UserStatus, GameId
from typing import List, Mapping

details = GameInfo(
    min_players=2,
    max_players=2,
    thumbnail_file_path=f'{os.path.dirname(__file__)}/thumb.jpg'
)

class TicTacToe(Game):
    @dataclass
    class GameDataaaa:
        current_player: int
        player_order: List[int]
        player_square_type: Mapping[int, int]
        current_board: List[List[int]]

    @staticmethod
    async def start_game(game_id: GameId, game_state: GameStatus.GameState):
        new_game_state = TicTacToe.GameDataaaa(
            current_player=game_state.confirmed_players[0],
            player_order=game_state.confirmed_players,
            player_square_type={game_state.confirmed_players[0]: 1, game_state.confirmed_players[1]: 2},
            current_board=[[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        )

        await GameData.store_data(game_id, new_game_state)




    @staticmethod
    @load_game_data(GameDataaaa)
    async def reply(game_id: GameId, interaction: discord.Interaction, game_state, game_data):
        pass

    
    @staticmethod
    async def play_move(game_id: GameId, interaction: discord.Interaction, game_state, game_data):
        pass

class TicTacToeButton(discord.ui.Button):
    def __init__(self, row: int, state: int):
        if state == 0:
            pass
        elif state == 1:
            pass
        elif state == 2:
            pass
        super().__init__(style=discord.ButtonStyle.secondary, label="U+200B", row=row)