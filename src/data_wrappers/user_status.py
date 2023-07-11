import redis.asyncio as redis_sync
from dataclasses import dataclass, asdict
from typing import List
from .types import GameId
from .helpers import watch_helper
from exceptions.general_exceptions import PlayerNotFound
from exceptions.game_exceptions import ActiveGameNotFound

class UserStatus:
    
    """
    API wrapper for reddis db which handles the status of players
    
    All data in the db is in the form
    UserId: UserState
    """

    __db_number = 2
    __pool = redis_sync.Redis(db=__db_number)
    
    UserId = int
    
    @dataclass
    class UserState:
        current_game: GameId | None
        queued_games: List[GameId]

    @staticmethod
    async def get_status(user_id: UserId) -> UserState | None:
        if current_status := await UserStatus.__pool.json().get(user_id):
            return UserStatus.UserState(**current_status)

    @staticmethod
    async def check_in_game(user_id: UserId) -> None | GameId:
        current_status = await UserStatus.get_status(user_id)
        
        if current_status:
            return current_status.current_game
    
    @staticmethod
    @watch_helper(__pool, "user_id")
    async def join_game(
        user_id: UserId,
        game_id: GameId,
        pipe: redis_sync.client.Pipeline = None # type: ignore
    ):
        if await pipe.json().get(user_id):
            await pipe.json().arrappend(str(user_id), '.queued_games', game_id)
        else:
            await pipe.json().set(user_id, '.', asdict(UserStatus.UserState(
                current_game=game_id,
                queued_games=[]
            )))
    
    @staticmethod
    async def check_users_are_ready(game_id: GameId, user_ids: List[UserId]) -> bool:
        for user_id in user_ids:
            user_status = await UserStatus.get_status(user_id) 
            if user_status:
                if user_status.current_game != game_id and user_status.current_game != None:
                    return False
        return True

    @staticmethod
    async def clear_game(
        game_id: GameId,
        user_id: List[UserId],
    ):
        for user in user_id:
            await UserStatus.remove_game(game_id, user)

    @staticmethod
    @watch_helper(__pool, "user_id")
    async def remove_game(
        game_id: GameId,
        user_id: UserId,
        pipe: redis_sync.client.Pipeline = None # type: ignore
    ):
        if current_status := await pipe.json().get(user_id):
            current_status = UserStatus.UserState(**current_status)
            if current_status.current_game == game_id:
                if len(current_status.queued_games) > 0:
                    await pipe.json().set(
                        user_id,
                        '.current_game',
                        await pipe.json().arrpop(
                            str(user_id),
                            '.queued_games',
                            0
                        )
                    )
                else:
                    await pipe.json().delete(user_id)
            else:
                if (index := await pipe.json().arrindex(str(user_id), '.queued_games', game_id)) > -1:
                    await pipe.json().arrpop(str(user_id), '.queued_games', index)
                else:
                    raise ActiveGameNotFound(game_id)
        else:
            raise PlayerNotFound(user_id)