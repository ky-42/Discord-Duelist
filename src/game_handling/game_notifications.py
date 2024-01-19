"""Contains GameNotifications which is used to send notifications to users"""

import functools
import random
from typing import Awaitable, Callable, List

from bot import bot
from data_types import GameId, MessageId, UserId
from data_wrappers.game_status import GameStatus
from data_wrappers.user_status import UserStatus
from exceptions import UserNotFound
from game_modules.game_module_loading import GameModuleLoading
from user_interfaces.game_embeds import game_info_embed, game_summary_embed
from user_interfaces.game_views import InviteOptions


class GameNotifications:
    """Contains functions for sending notifications to users"""

    @staticmethod
    async def send_game_invites(
        user_ids: List[int],
        game_id: GameId,
        accept_callback: Callable[[UserId], Awaitable[None]],
        reject_callback: Callable[[], Awaitable[None]],
    ) -> None:
        """Sends game invites to the passed users.

        Raises:
            UserNotFound: Raised user to send message to is not found.

        Args:
            user_ids (List[int]): List of user ids to send invites to.
            game_id (GameId): Id of the game to send invites for.
            accept_callback (Callable[[UserId], Awaitable[None]]): Function to
                call when a user accepts the invite. Should take the user id
                as a parameter.
            reject_callback (Callable[[], Awaitable[None]]): Function to call
                when a user rejects the invite.
        """

        for user_id in user_ids:
            user_dm = await bot.get_dm_channel(user_id)
            game_status = await GameStatus.get(game_id)

            await user_dm.send(
                embed=game_info_embed(
                    user_id,
                    f"{game_status.usernames[str(game_status.starting_user)]} wants to play a game!",
                    game_status,
                    GameModuleLoading.get_game_module(
                        game_status.game_module_name
                    ).get_details(),
                    f"Invite expires in {str(int((bot.game_requested_expiry.total_seconds()//60)%60))} minute",
                ),
                view=InviteOptions(
                    functools.partial(accept_callback, user_id), reject_callback
                ),
                delete_after=bot.game_requested_expiry.seconds,
            )

    @staticmethod
    async def game_start(game_id: GameId) -> None:
        """Informs users that the game has started"""

        game_status = await GameStatus.get(game_id)

        for user_id in game_status.all_users:
            await (await bot.get_user(int(user_id))).send(
                embed=game_info_embed(
                    user_id,
                    "Game Started",
                    game_status,
                    GameModuleLoading.get_game_module(
                        game_status.game_module_name
                    ).get_details(),
                    f"Game will be ended if {bot.game_no_move_expiry.days} days elapses between replys",
                )
            )

    @staticmethod
    async def game_queued(game_id: GameId) -> None:
        """Informs users that the game has been queued"""
        game_status = await GameStatus.get(game_id)

        for user_id in game_status.all_users:
            await (await bot.get_user(int(user_id))).send(
                embed=game_info_embed(
                    user_id,
                    "Game Queued",
                    game_status,
                    GameModuleLoading.get_game_module(
                        game_status.game_module_name
                    ).get_details(),
                )
            )

    @staticmethod
    async def max_games(game_id: GameId, maxed_user: UserId) -> None:
        """Used to inform users that a user has reached their max games.

        Lets players in the game know that a user has reached their max games and
        that the game will not be started. Also informs the user maxed out user.

        Args:
            game_id (GameId): Id of game that was not started.
            maxed_user (UserId): Id of user who has maxed out games.
        """

        game_status = await GameStatus.get(game_id)

        # Informs non-maxed users in game that the game will not be started
        for user_id in game_status.all_users:
            if user_id != maxed_user:
                await (await bot.get_user(int(user_id))).send(
                    embed=game_summary_embed(
                        [],
                        list(game_status.usernames.values()),
                        game_status,
                        f"{game_status.usernames[str(maxed_user)]} has reached their max games and this game will not be started",
                    )
                )

        # Informs maxed user that the game will not be started
        await (await bot.get_user(int(maxed_user))).send(
            embed=game_summary_embed(
                [],
                list(game_status.usernames.values()),
                game_status,
                f"You have reached your max games and this game will not be started",
            )
        )

    @staticmethod
    def __get_game_notifications_message(notification_amount: int) -> str:
        """Determines the message to send to the user.

        This is based on the amount of notifications they have.
        """

        if notification_amount > 1:
            return f"You have {notification_amount} notifications! Use the /reply command to view them!"
        else:
            return f"You have a notification! Use the /reply command to view it!"

    @staticmethod
    async def added_game_notification(user_id: UserId) -> MessageId:
        """Notifies user about it an added game notification.

        Args:
            user_id (UserId): Id of the user to add the notification to.

        Returns:
            MessageId: Id of the message sent to the user informing them of the
                notification.
        """

        user_status = await UserStatus.get(user_id)
        user_dm_channel = await bot.get_dm_channel(user_id)

        if user_status:
            if user_status.notification_id:
                try:
                    notification_message = await user_dm_channel.fetch_message(
                        user_status.notification_id
                    )

                except:
                    pass

                else:
                    await notification_message.delete()

            new_message = await user_dm_channel.send(
                GameNotifications.__get_game_notifications_message(
                    len(user_status.notifications)
                )
            )

            return new_message.id

        else:
            raise UserNotFound(user_id)

    @staticmethod
    async def removed_game_notification(user_id: UserId) -> bool:
        """Removes a notification and updates the users notification message.

        Args:
            user_id (UserId): Id of the user to remove the notification from.

        Returns:
            bool: Whether the notification message was deleted. True if deleted.
        """

        user = await UserStatus.get(user_id)
        user_dm_channel = await bot.get_dm_channel(user_id)

        if user:
            if user.notification_id:
                notification_message = await user_dm_channel.fetch_message(
                    user.notification_id
                )

                if len(user.notifications) == 0:
                    await notification_message.delete()
                    return True

                await notification_message.edit(
                    content=GameNotifications.__get_game_notifications_message(
                        len(user.notifications)
                    )
                )

            else:
                if len(user.notifications) > 0:
                    # If for some reason the user has notifications but no notification message
                    await GameNotifications.added_game_notification(user_id)

        else:
            raise UserNotFound(user_id)

        return False

    @staticmethod
    async def game_quit(game_id: GameId, quiting_user: UserId) -> None:
        """Sends message all users in a game that another user has quit.

        Won't send message to the person who quit.

        Args:
            game_id (GameId): Id of game that had a user quit.
            quiting_user (UserId): Id of user that quit game.
        """

        cancelled_game = await GameStatus.get(game_id)

        quiting_user_object = await bot.get_user(quiting_user)

        user_objects = [
            await bot.get_user(game_user_id)
            for game_user_id in cancelled_game.all_users
            if game_user_id != quiting_user
        ]

        for user_object in user_objects:
            await user_object.send(
                embed=game_summary_embed(
                    [],
                    list(cancelled_game.usernames.values()),
                    cancelled_game,
                    f"Game was cancelled because {quiting_user_object.name} quit",
                )
            )

    @staticmethod
    async def game_expired(game_id: GameId) -> None:
        """Sends message all users in a game that it has expired.

        Args:
            game_id (GameId): Id of game that expired.
        """

        expired_game = await GameStatus.get(game_id)

        for user_id in expired_game.all_users:
            dm = await bot.get_dm_channel(user_id)

            await dm.send(
                embed=game_summary_embed(
                    [],
                    list(expired_game.usernames.values()),
                    expired_game,
                    f"Game ended because no one played a move for {bot.game_no_move_expiry.days} days",
                )
            )

    @staticmethod
    async def game_end(
        game_id: GameId,
        winner_ids: List[int],
    ) -> None:
        """Sends message all users in a game that it has ended.

        This is not for games that expire, are quit or end by the actualy game
        not ending.

        Args:
            game_id (GameId): Id of game that ended.
            winner_ids (List[int]): List of ids of users that won the game.
        """

        game_status = await GameStatus.get(game_id)

        for user in game_status.all_users:
            if len(winner_ids):
                if user in winner_ids:
                    footer = "You won!"

                else:
                    footer = "You lost" + random.choice(
                        [
                            " :(",
                            " so close! Hopefully...",
                            "! You tried your best but thats not saying much...",
                            " you'll get em next time!",
                        ]
                    )

            else:
                footer = "Its a tie!"

            # Creats list of names of winners
            all_user_ids = game_status.all_users.copy()
            winner_names = []

            for user_id in winner_ids:
                all_user_ids.remove(user_id)
                winner_names.append(game_status.usernames[str(user_id)])

            # Creates list of names of other users
            other_users_names = [
                game_status.usernames[str(user_id)] for user_id in all_user_ids
            ]

            await (await bot.get_user(user)).send(
                embed=game_summary_embed(
                    winner_names, other_users_names, game_status, footer
                )
            )
