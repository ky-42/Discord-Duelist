from dataclasses import dataclass
from typing import List, Mapping

from games.utils import GameModule


@dataclass
class TicTacToeData(GameModule.GameDataClass):
    """
    Data that needs to be stored for a game of Tic Tac Toe
    """

    active_user: int
    user_order: List[int]
    user_square_type: Mapping[str, int]
    active_board: List[List[int]]
