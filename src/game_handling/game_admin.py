import functools

from bot import bot
from data_types import DiscordMessage, GameId, UserId
from data_wrappers import GameData, GameStatus, UserStatus
from game_handling.game_notifications import GameNotifications

from .game_module_loading import GameModuleLoading


class GameAdmin:
    @staticmethod
    async def users_selected(game_status: GameStatus.Game, users: dict[str, str]):
        # Add 1 to the user count to include the user who started the game
        if GameModuleLoading.check_game_module_details(
            game_status.game_module_name, len(users) + 1
        ):
            for user_id, user_name in users.items():
                game_status.usernames[user_id] = user_name
                game_status.all_users.append(int(user_id))
                game_status.unconfirmed_users.append(int(user_id))

            # Adds game to game status store
            game_id = await GameStatus.add(game_status, bot.game_requested_expiry)

            # Sends out confirmations to secondary users
            await GameNotifications.game_confirms(
                game_status.unconfirmed_users,
                game_id,
                # TODO consider adding function to notify users between
                # before calling cancel_game in the reject callback
                functools.partial(GameAdmin.user_confirmed, game_id),
                functools.partial(GameAdmin.cancel_game, game_id),
            )

            return DiscordMessage(
                "Game created! Please wait for other players to accept game"
            )
        else:
            raise ValueError("Invalid game details")

    @staticmethod
    async def user_confirmed(game_id: GameId, user_id: int):
        unconfirmed_list = await GameStatus.confirm_user(game_id, user_id)

        if len(unconfirmed_list) == 0:
            await GameAdmin.start_game(game_id)

    @staticmethod
    async def start_game(game_id: GameId):
        game_status = await GameStatus.get(game_id)

        for user_id in game_status.all_users:
            # Works when called on a game that was qued
            # cause join game checks if user is already in game
            await UserStatus.join_game(user_id, game_id)

        if await UserStatus.check_users_are_ready(game_id, game_status.all_users):
            await GameNotifications.game_start(game_id)

            game_module = GameModuleLoading.get_game_module(
                game_status.game_module_name
            )

            await GameStatus.set_game_in_progress(game_id)
            await GameStatus.set_expiry(game_id, bot.game_no_move_expiry)
            await game_module.start_game(game_id)

        else:
            await GameNotifications.game_queued(game_id)

            await GameStatus.set_game_queued(game_id)
            await GameStatus.set_expiry(game_id, None)

    @staticmethod
    async def reply(game_id: GameId, replying_user: UserId) -> DiscordMessage:
        only_game_details = await GameStatus.get(game_id)

        await GameStatus.set_expiry(game_id, bot.game_no_move_expiry)

        return await GameModuleLoading.get_game_module(
            only_game_details.game_module_name
        ).reply(game_id, replying_user)

    @staticmethod
    async def quit_game(game_id: GameId, quiting_user: UserId) -> DiscordMessage:
        """
        Used when user quits a game to both cancel the game and inform other users
        """
        await GameNotifications.game_quit(game_id, quiting_user)

        await GameAdmin.cancel_game(game_id)

        return DiscordMessage("Game Quit")

    @staticmethod
    @GameStatus.handle_game_expire
    async def game_expired(game_id: GameId):
        await GameNotifications.game_expired(game_id)

        await GameAdmin.cancel_game(game_id)

    @staticmethod
    async def cancel_game(game_id: GameId):
        """
        Clears a game and all its data no matter what state its in.
        Any notification to user should be done before or after calling this function
        """

        # Clear all game data from redis
        # so update user status, remove game status, and game data

        game_details = await GameStatus.get(game_id)

        # Clears external data
        if game_details.status > 1:
            await GameData.delete_data(game_id)
        if game_details.status > 0:
            (
                moved_up_games,
                users_with_removed_notification,
            ) = await UserStatus.clear_game(
                game_id,
                game_details.all_users,
            )

            for user in users_with_removed_notification:
                await GameNotifications.remove_game_notification(user)

            # Trys to start any games there were moved from que to active
            for moved_up_game in moved_up_games:
                await GameAdmin.start_game(moved_up_game)

        if game_details.status > -1:
            await GameStatus.delete(game_id)
