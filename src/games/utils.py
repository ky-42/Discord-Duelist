import functools
import inspect
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Awaitable,
    Callable,
    Concatenate,
    Generic,
    ParamSpec,
    Type,
    TypeVar,
    get_args,
)

from data_types import DiscordMessage, GameId, UserId
from data_wrappers import GameData, GameStatus
from data_wrappers.user_status import UserStatus
from games.game_handling.game_admin import GameAdmin
from games.game_handling.game_notifications import GameNotifications

# Generics for the GameInfo class
S = TypeVar("S", bound=GameStatus.Game | None)
D = TypeVar("D", bound=GameData.GameDataClass | None)


@dataclass
class GameInfo(Generic[S, D]):
    """
    Dataclass for holding the game state and game data when passed using get_game_info
    """

    GameState: S
    GameData: D


P = ParamSpec("P")
R = TypeVar("R")


def get_game_info(
    fn: Callable[Concatenate[GameInfo, P], Awaitable[R]]
) -> Callable[P, Awaitable[R]]:
    """
    Decorator for getting the game state and game data for a game
    the parameter to pass the data to must always be the first parameter
    and the wrapped function must also have a game_id parameter

    Uses the annotations of the function to determine what to get and the type of the data

    Examples:
        game_info: GameInfo[GameState, None]
            Fetches the game state for the game but not the data
        game_info: GameInfo[None, GameDataClass]
            Fetches the game data for the game but not the state
        game_info: GameInfo[GameState, GameDataClass]
            Fetches both the game state and game data for the game
    """

    @functools.wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # Gets the signature of the wrapped function
        func_sig = inspect.signature(fn)

        first_param_name = iter(func_sig.parameters).__next__()

        # This works because the paramter we need to pass to will always be the first one
        # because of the type definition of this decorator
        func_params = func_sig.bind(None, *args, **kwargs)

        # Game id is needed to get the state or data for a game
        if "game_id" in (args_dict := func_params.arguments):
            game_id = args_dict["game_id"]

            data_state_param = func_sig.parameters[first_param_name]

            try:
                state_type = get_args(data_state_param.annotation)[0]
                game_data_type = get_args(data_state_param.annotation)[1]
            except:
                raise TypeError("Invalid annotation for game_info parameter")

            # Fetches state and data
            fetched_state: GameStatus.Game | None = None
            fetched_game_data: GameData.GameDataClass | None = None

            if state_type != type(None):
                fetched_state = await GameStatus.get(game_id)

            if game_data_type != type(None):
                fetched_game_data = await GameData.retrive_data(game_id, game_data_type)

            fetched_info = GameInfo(fetched_state, fetched_game_data)

            return await fn(fetched_info, *args, **kwargs)

        else:
            raise TypeError("Missing required parameter: game_id")

    return wrapper


@dataclass
class GameDetails:
    """
    Dataclass for holding the details of a game
    """

    min_players: int
    max_players: int
    thumbnail_file_path: str

    def check_player_count(self, player_count):
        return player_count >= self.min_players and player_count <= self.max_players


class Game(ABC):
    """
    Abstract class for defining a game
    """

    GameState = GameStatus.Game
    GameDataClass = GameData.GameDataClass

    @staticmethod
    @abstractmethod
    def get_details() -> GameDetails:
        """
        Returns a GameDetails object for the game
        """
        pass

    @staticmethod
    @abstractmethod
    @get_game_info
    async def start_game(
        game_info: GameInfo[GameState, None],
        game_id: GameId,
    ) -> None:
        """
        Used it initialize a game
        """
        pass

    @staticmethod
    @abstractmethod
    @get_game_info
    async def reply(
        game_info: GameInfo[GameState, GameDataClass], game_id: GameId, user_id: UserId
    ) -> DiscordMessage:
        """
        Used to play a move in a game

        All data from the interactions by players
        in a game is passed to this method
        """
        pass

    @staticmethod
    async def send_notification(game_id: GameId, player_id: UserId):
        """
        Sends a message that its the players turn
        """

        await UserStatus.add_notifiction(game_id, player_id)
        new_message_id = await GameNotifications.add_game_notification(player_id)
        await UserStatus.set_notification_id(player_id, new_message_id)

    @staticmethod
    async def remove_notification(game_id: GameId, player_id: UserId):
        await UserStatus.remove_notification(game_id, player_id)
        if await GameNotifications.remove_game_notification(player_id):
            await UserStatus.remove_notification_id(player_id)

    @staticmethod
    async def store_data(game_id: GameId, game_data: Type[GameData.GDC]) -> None:
        """
        Used to store data for a game
        """
        await GameData.store_data(game_id, game_data)

    @staticmethod
    async def end_game(
        game_id: GameId,
        winner_ids: list[int],
    ):
        """
        Used to end a game

        Param:
            winner - List of user ids who won pass empty list for a tie
        """

        await GameNotifications.game_end(game_id, winner_ids)
        await GameAdmin.cancel_game(game_id)
