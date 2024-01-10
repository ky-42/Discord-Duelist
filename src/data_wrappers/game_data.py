"""Contains the GameData class which is used to store data for games being played."""

from dataclasses import asdict
from typing import Type, TypeVar

import redis.asyncio as redis

from data_types import GameId
from data_types.protocols import IsDataclass
from exceptions import GameNotFound


class GameData:
    """API wrapper for db which handles the data used by games being played.

    All data in the db is in the key:value form:
        GameId: Data

    Data here is refereing to the dataclass which is used to store the data for
    a game.
    """

    # Redis db number and redis connection pool
    __db_number = 0
    __pool = redis.Redis(db=__db_number)

    # Teype var for get method
    GDC = TypeVar("GDC", bound=IsDataclass)

    @staticmethod
    async def get(game_id: GameId, retrive_data_type: Type[GDC]) -> GDC:
        """Gets data from db and returns it as a passed dataclass.

        Args:
            game_id (GameId): Id of game to retrive data for.
            retrive_data_type (Type[GDC]): Dataclass to put retrived data into.

        Raises:
            GameNotFound: Raised if game_id is not found in db.

        Returns:
            GDC: Instance of retrive_data_type parameter with data from db.
        """

        if game_state := await GameData.__pool.json().get(game_id):
            return retrive_data_type(**game_state)
        raise GameNotFound(f"Game {game_id} not found")

    @staticmethod
    async def store(game_id: GameId, data: IsDataclass) -> None:
        """Stores game data in db.

        Args:
            game_id (GameId): Id of game to store data for.
            data (IsDataclass): Data to store in the form of a dataclass.
        """

        # Check if data is empty
        if len(list((data_dict := asdict(data)).keys())) == 0:
            print("No data to store")
        await GameData.__pool.json().set(game_id, ".", data_dict)

    @staticmethod
    async def delete(game_id: GameId) -> None:
        """Deletes data from db.

        Won't do anything if game_id is not found in db.

        Args:
            game_id (GameId): Id of game to delete data for.
        """

        delete_amount = await GameData.__pool.delete(game_id)
        if not delete_amount:
            print("No data deleted")
