import redis.asyncio as redis_sync
import random
import string
from datetime import timedelta
from typing import List, Mapping
from dataclasses import dataclass, asdict
from exceptions.game_exceptions import ActiveGameNotFound
from exceptions.general_exceptions import PlayerNotFound
from .helpers import pipeline_watch
from . import GameId

class GameStatus:
    """
    API wrapper for reddis db which handles the status of games

    All data in the db is in form
    GameId: GameState
    """
    
    __db_number = 1
    __pool = redis_sync.Redis(db=__db_number)

    @dataclass
    class GameState:
        # 0 = unconfirmed | 1 = confirmed but queued | 2 = in progress | 3 = finished
        status: int
        game: str
        bet: int
        starting_player: int
        player_names: Mapping[str, str]
        confirmed_players: List[int]
        unconfirmed_players: List[int]
        
    @staticmethod
    def create_game_id() -> GameId:
        return ''.join(random.choices(
            string.ascii_letters +
            string.digits,
            k=16
        ))

    @staticmethod
    async def get_game(game_id: GameId) -> GameState:
        if (game_state := await GameStatus.__pool.json().get(game_id)):
            return GameStatus.GameState(**game_state)
        raise ActiveGameNotFound

    @staticmethod
    async def add_game(game_id: GameId, state: GameState, timeout_minutes: float):
        await GameStatus.__pool.json().set(game_id, '.', asdict(state))
        await GameStatus.__pool.expire(game_id, timedelta(minutes=timeout_minutes))
        
    @staticmethod
    async def extend_game(game_id: GameId, timeout_minutes: float):
        await GameStatus.__pool.expire(game_id, timedelta(minutes=timeout_minutes))

    @staticmethod
    async def delete_game(game_id: GameId):
        await GameStatus.__pool.delete(game_id)


    @staticmethod
    @pipeline_watch(__pool, "game_id", ActiveGameNotFound)
    async def player_confirm(
        game_id: GameId,
        player_id: int,
        pipe: redis_sync.client.Pipeline = None # type: ignore
    ) -> List[int]:
        # Make sure player exists
        if ((index := await pipe.json().arrindex(game_id, '.unconfirmed_players', player_id)) > -1):
            # Switch to buffered mode after watch
            pipe.multi()
            pipe.json().arrpop(game_id, '.unconfirmed_players', index)
            pipe.json().arrappend(game_id, '.confirmed_players', player_id)
            pipe.json().get(game_id, '.unconfirmed_players')
            results = await pipe.execute()

            return results[2]

        else:
            raise PlayerNotFound(player_id)

    @staticmethod
    async def set_game_queued(game_id: GameId):
        await GameStatus.__pool.json().set(game_id, '.status', 1)
    
    @staticmethod
    async def set_game_in_progress(game_id: GameId):
        await GameStatus.__pool.json().set(game_id, '.status', 2)