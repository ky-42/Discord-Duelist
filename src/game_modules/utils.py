"""Utility functions used by game modules and game classes"""

import functools
import inspect
from dataclasses import dataclass
from typing import (
    Awaitable,
    Callable,
    Concatenate,
    Generic,
    ParamSpec,
    TypeVar,
    get_args,
)

from data_types.protocols import IsDataclass
from data_wrappers import GameData, GameStatus

# Generics for the GameInfo class
OptionalStatus = TypeVar("OptionalStatus", bound=GameStatus.Game | None)
OptionalData = TypeVar("OptionalData", bound=IsDataclass | None)


@dataclass
class GameInfo(Generic[OptionalStatus, OptionalData]):
    """Holds game status and game data.

    Generics are used so that the true type of each attribute can be specified
    in a functions type hints. It makes possible this:

    def ex(
        game_info: GameInfo[GameModule.GameStatus, None]
    ):

    This is used by the get_game_info function to figure out what to pass to
    functions with a similar type hint. It also makes it easier to deal with
    this class in a function as we know from the start what was actually passed.

    Attributes:
        GameStatus (GameStatus.Game, Optional, Generic): Should either be
            GameStatus.Game or none. This is the status of a game.
        GameData (Dataclass, Optional, Generic): Should either
            be a dataclass or none. This is the data associated with a game.
    """

    GameStatus: OptionalStatus
    GameData: OptionalData


# Generics for get_game_info decorator
LeftoverParams = ParamSpec("LeftoverParams")
ReturnType = TypeVar("ReturnType")


def get_game_info(
    fn: Callable[Concatenate[GameInfo, LeftoverParams], Awaitable[ReturnType]]
) -> Callable[LeftoverParams, Awaitable[ReturnType]]:
    """Decorator for getting the game status and game data for a game.

    Used to get the game status and game data for a game and pass it to a function.
    To use this decorator the function must have a paramter called "game_id" that
    contains the id of the game to get the status and data for. The parameter to
    pass the data to must always be the first parameter with a type hint of
    type GameInfo with its generic parameters specifiying what data to get.
    An example of such a type hint to only get game status is shown below:

        game_info: GameInfo[GameStatus, None]
            Fetches the game status for the game but not the data.

    Another example of a type hint to get both game status and game data is this:

        game_info: GameInfo[GameStatus, GameDataClass]
            Fetches both the game status and game data for the game.

    Args:
        fn (Callable[Concatenate[GameInfo, LefoverParams], Awaitable[ReturnType]]):
            Function to wrap.

    Raises:
        TypeError: The function does not have a game_id parameter.
        TypeError: The parameter to pass the data to is not the first parameter
            or does not have a type hint of type GameInfo.
    """

    @functools.wraps(fn)
    async def wrapper(
        *args: LeftoverParams.args, **kwargs: LeftoverParams.kwargs
    ) -> ReturnType:
        # Gets the signature of the wrapped function
        func_sig = inspect.signature(fn)

        first_param_name = iter(func_sig.parameters).__next__()

        # This works because the paramter we need to pass to will always be the first one
        # because of the type definition of this decorator
        func_params = func_sig.bind(None, *args, **kwargs)

        # Game id is needed to get the status or data for a game
        if "game_id" in (args_dict := func_params.arguments):
            game_id = args_dict["game_id"]

            game_info_param = func_sig.parameters[first_param_name]

            try:
                status_type = get_args(game_info_param.annotation)[0]
                game_data_type = get_args(game_info_param.annotation)[1]
            except:
                raise TypeError("Invalid annotation for game_info parameter")

            # Fetches status and data
            fetched_status: GameStatus.Game | None = None
            fetched_game_data: IsDataclass | None = None

            if status_type != type(None):
                fetched_status = await GameStatus.get(game_id)

            if game_data_type != type(None):
                fetched_game_data = await GameData.get(game_id, game_data_type)

            fetched_info = GameInfo(fetched_status, fetched_game_data)

            return await fn(fetched_info, *args, **kwargs)

        else:
            raise TypeError("Missing required parameter: game_id")

    return wrapper
