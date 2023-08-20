from discord.ext import commands, tasks

from bot import Bot
from games.game_handling.game_loading import GameLoading


class Task(commands.Cog):
    """
    Uses the tasks extension of discord.py to run repeated tasks
    """

    def __init__(self) -> None:
        super().__init__()

    @tasks.loop(minutes=15)
    async def clear_old_loaded_games():
        GameLoading.clear_old_games()


async def setup(bot: Bot) -> None:
    await bot.add_cog(Task())
