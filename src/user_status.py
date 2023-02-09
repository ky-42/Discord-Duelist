from main import Bot
import redis.asyncio as redis
from redis.commands.json.path import Path

from dataclasses import dataclass, asdict
from typing import List, Mapping
from game_handling import GameId

@dataclass
class UserState:
    current_game: int
    queued_games: List[int]

class UserStatus:
    def __init__(self, bot: Bot):
        self.pool = redis.Redis(db=2)
        self.bot = bot
    
    async def check_in_game(self, user_id: int) -> bool:
        current_status = await self.__get_status(user_id)
        
        if current_status:
            return True
        else:
            return False

    async def __get_status(self, user_id) -> UserState | None:
        if current_status := await self.pool.json().get(user_id):
            return UserState(**current_status)
    
    async def join_game(self, user_ids: List[int], game_id: GameId):
        pass

    
    # def joined_game(user_id, game_id):
    #     # TODO maybe add a pipe and watch here for any data races
    #     if UserStatus.pool.exists(user_id):
    #         UserStatus.pool.json().set(user_id, '.', {
    #             'current_game': game_id,
    #             'queued_games': []
    #         })
    #     else:
    #         UserStatus.pool.json().ARRAPPEND(user_id, Path('.queued_games'), game_id)

    
    # def game_finished(user_id):
    #     existing_status = redis.get(user_id)
    #     if len(existing_status['queued']):
    #         existing_status['current_game'] 

