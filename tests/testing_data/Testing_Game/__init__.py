"""Game created solely for testing purposes"""

from dataclasses import dataclass
from typing import Type

from data_types import GameId, UserId
from game_modules.game_classes import GameModule, GameModuleDetails
from game_modules.utils import GameInfo, get_game_info


@dataclass
class TestingGameData:
    """Data that needs to be stored for a game of Testing Game"""

    test_data: str


class TestingGame(GameModule):
    """Game for testing purposes"""

    @staticmethod
    def get_details() -> GameModuleDetails:
        return GameModuleDetails(
            min_users=2,
            max_users=4,
        )

    @staticmethod
    @get_game_info
    async def start_game(
        game_info: GameInfo[GameModule.GameStatus, None],
        game_id: GameId,
    ):
        pass

    @staticmethod
    @get_game_info
    async def reply(
        game_info: GameInfo[GameModule.GameStatus, TestingGameData],
        game_id: GameId,
        user_id: UserId,
    ):
        pass


def load() -> Type[GameModule]:
    return TestingGame
