from bot import bot
from data_types import DiscordMessage, GameId, UserId
from data_wrappers.game_status import GameStatus

from .game_admin import GameAdmin


class GameActions:
    @staticmethod
    async def quit_game(game_id: GameId, user_id: UserId) -> DiscordMessage:
        """
        Used when player quits a game to both cancel the game and inform other players
        """

        cancelled_game = await GameStatus.get(game_id)

        user_objects = {
            game_user_id: await bot.get_user(game_user_id)
            for game_user_id in cancelled_game.all_players
        }

        for game_user_id, game_user_object in user_objects.items():
            if game_user_id != user_id:
                # Creates list of all names of users in game that are not
                # the quiting user or user that the message will be sent to
                other_user_names = [
                    user_objects[temp_user_id].name
                    for temp_user_id in cancelled_game.all_players
                    if temp_user_id not in [user_id, game_user_id]
                ]

                user_string = ""
                if len(other_user_names):
                    user_string = " with " + ", ".join(other_user_names)

                await game_user_object.send(
                    f"Your game of {cancelled_game.game}{user_string} was cancelled because {user_objects[user_id].name} quit"
                )

        await GameAdmin.cancel_game(game_id)

        return DiscordMessage("Game Quit")
