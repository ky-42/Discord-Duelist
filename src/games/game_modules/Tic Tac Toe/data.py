from dataclasses import dataclass
from typing import List, Mapping

from games.utils import Game


@dataclass
class TicTacToeData(Game.GameDataClass):
    """
    Data that needs to be stored for a game of Tic Tac Toe
    """

    active_player: int
    player_order: List[int]
    player_square_type: Mapping[str, int]
    active_board: List[List[int]]
