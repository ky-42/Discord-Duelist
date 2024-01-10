"""Contains the GameAdmin class which is used to manage games"""

import functools

from bot import bot
from data_types import DiscordMessage, GameId, UserId
from data_wrappers import GameData, GameStatus, UserStatus
from game_handling.game_notifications import GameNotifications

from .game_module_loading import GameModuleLoading


class GameAdmin:
    """Collection of static methods used to manage games"""

    @staticmethod
    async def users_selected(
        game_status: GameStatus.Game, users: dict[str, str]
    ) -> DiscordMessage:
        """Ensures valid game details, stores game status, and sends invites

        Should be called when the starting user selects other users to play with.
        This will store the game status for the first time and send invites to
        the selected users.

        Args:
            game_status (GameStatus.Game): Starting game status.
            users (dict[str, str]): Should be in format {user_id: username} where
                each entry is a based on selected users.

        Raises:
            ValueError: Raised when the game details are invalid
                (ex. not enough users)

        Returns:
            DiscordMessage: Message to send to user who selected.
        """

        if GameModuleLoading.check_game_module_details(
            game_status.game_module_name,
            # Add 1 to the user count to include the user who started the game
            len(users) + 1,
        ):
            # Adds selected users to game status
            for user_id, user_name in users.items():
                game_status.usernames[user_id] = user_name
                game_status.all_users.append(int(user_id))
                game_status.pending_users.append(int(user_id))

            game_id = await GameStatus.add(game_status, bot.game_requested_expiry)

            await GameNotifications.send_game_invites(
                game_status.pending_users,
                game_id,
                functools.partial(GameAdmin.__user_accepted, game_id),
                functools.partial(GameAdmin.delete_game, game_id),
            )

            return DiscordMessage(
                "Game created! Please wait for other players to accept invite"
            )
        else:
            raise ValueError("Invalid game details")

    @staticmethod
    async def __user_accepted(game_id: GameId, user_id: int) -> None:
        """Called when a user accepts a game"""

        unaccepted_list = await GameStatus.user_accepted(game_id, user_id)

        if len(unaccepted_list) == 0:
            await GameAdmin.__start_game(game_id)

    @staticmethod
    async def __start_game(game_id: GameId) -> None:
        """Makes sure all users are ready and starts or queues the game"""

        game_status = await GameStatus.get(game_id)

        for user_id in game_status.all_users:
            # Works when called on a game that was qued
            # cause join game checks if user is already in game
            if not await UserStatus.join_game(user_id, game_id):
                # If user is in too many games game will be deleted
                # and user will be informed
                await GameNotifications.max_games(game_id, user_id)
                await GameAdmin.delete_game(game_id)

        if await UserStatus.check_users_are_ready(game_status.all_users, game_id):
            await GameNotifications.game_start(game_id)

            game_module = GameModuleLoading.get_game_module(
                game_status.game_module_name
            )

            await GameStatus.set_game_state(game_id, 2)
            await GameStatus.set_expiry(game_id, bot.game_no_move_expiry)
            await game_module.start_game(game_id)

        else:
            await GameNotifications.game_queued(game_id)

            await GameStatus.set_game_state(game_id, 1)
            await GameStatus.set_expiry(game_id, None)

    @staticmethod
    async def reply(game_id: GameId, replying_user: UserId) -> DiscordMessage:
        """Gets the reply from the game module and sends to player.

        Also resets the expiry time.

        Args:
            game_id (GameId): Id of game user is replying to.
            replying_user (UserId): Id of user replying to game.

        Returns:
            DiscordMessage: Message from game module to send to user.
        """

        only_game_details = await GameStatus.get(game_id)

        await GameStatus.set_expiry(game_id, bot.game_no_move_expiry)

        return await GameModuleLoading.get_game_module(
            only_game_details.game_module_name
        ).reply(game_id, replying_user)

    @staticmethod
    async def quit_game(game_id: GameId, quitting_user: UserId) -> DiscordMessage:
        """Ends a game and informs other users.

        Args:
            game_id (GameId): Id of game to end.
            quiting_user (UserId): Id of user quitting game.

        Returns:
            DiscordMessage: Message to quitting send to user.
        """

        await GameNotifications.game_quit(game_id, quitting_user)

        await GameAdmin.delete_game(game_id)

        return DiscordMessage("Game Quit")

    @staticmethod
    @GameStatus.handle_game_expire
    async def __game_expired(game_id: GameId) -> None:
        """Called when a game expires. Cancels the game and informs users"""

        await GameNotifications.game_expired(game_id)

        await GameAdmin.delete_game(game_id)

    @staticmethod
    async def delete_game(game_id: GameId) -> None:
        """Deletes all data associated with a game no matter what state its in.

        Args:
            game_id (GameId): Id of game to delete.
        """

        game_details = await GameStatus.get(game_id)

        # Game started
        if game_details.state > 1:
            await GameData.delete(game_id)

        # Game qued
        if game_details.state > 0:
            (
                moved_up_games,
                users_with_removed_notification,
            ) = await UserStatus.clear_game(game_details.all_users, game_id)

            # Removes any game notifications for users who had one when game was removed
            for user in users_with_removed_notification:
                await GameNotifications.removed_game_notification(user)

            # Trys to start any games there were moved from que to active
            for moved_up_game in moved_up_games:
                await GameAdmin.__start_game(moved_up_game)

        # Game not accepted
        if game_details.state > -1:
            await GameStatus.delete(game_id)
