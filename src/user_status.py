from main import Bot
import redis.asyncio as redis
from redis.commands.json.path import Path


# current_game: game_id
# queued_games: [game_id, ...]

class UserStatus:
    def __init__(self, bot: Bot):
        self.pool = redis.Redis(db=2)
        self.bot = bot

    def check_status(self, user_id):
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

