import redis.asyncio as redis


class GameData:
    pool = redis.Redis(db=0)
