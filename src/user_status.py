import redis.asyncio as redis

# current_game: game_id
# queued_games: [game_id, ...]

class UserStatus:
    redis_pool = redis.Redis(db=2)
    
    def joined_game(user_id):
        UserStatus.redis_pool.get()
    
    # def game_finished(user_id):
    #     existing_status = redis.get(user_id)
    #     if len(existing_status['queued']):
    #         existing_status['current_game'] 
