import functools
import random
from typing import Awaitable, Callable, List

from bot import bot
from data_types import GameId, MessageId, UserId
from data_wrappers.game_status import GameStatus
from data_wrappers.user_status import UserStatus
from exceptions import UserNotFound
from game_handling.game_module_loading import GameModuleLoading
from user_interfaces.game_embeds import game_info_embed, game_summary_embed
from user_interfaces.game_views import GameConfirm


class GameNotifications:
    @staticmethod
    async def game_confirms(
        user_ids: List[int],
        game_id: GameId,
        accept_callback: Callable[[UserId], Awaitable[None]],
        reject_callback: Callable[[], Awaitable[None]],
    ) -> None:
        for user_id in user_ids:
            # Gets the dm channel of the user to send the confirmation over
            dm = await bot.get_dm_channel(user_id)
            game_status = await GameStatus.get(game_id)

            await dm.send(
                embed=game_info_embed(
                    user_id,
                    f"{game_status.usernames[str(game_status.starting_user)]} wants to play a game!",
                    game_status,
                    GameModuleLoading.get_game_module(
                        game_status.game_module_name
                    ).get_details(),
                    f"Invite expires in {str(int((bot.game_requested_expiry.total_seconds()//60)%60))} minute",
                ),
                view=GameConfirm(
                    functools.partial(accept_callback, user_id), reject_callback
                ),
                delete_after=bot.game_requested_expiry.seconds,
            )

    @staticmethod
    async def game_start(game_id: GameId):
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
    async def game_queued(game_id: GameId):
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
    def __get_game_notifications_message(notification_amount: int):
        if notification_amount > 1:
            return f"You have {notification_amount} notifications! Use the /reply command to view them!"
        else:
            return f"You have a notification! Use the /reply command to view it!"

    @staticmethod
    async def add_game_notification(user_id: UserId) -> MessageId:
        user = await UserStatus.get(user_id)
        user_dm_channel = await bot.get_dm_channel(user_id)

        if user:
            if user.notification_id:
                try:
                    notification_message = await user_dm_channel.fetch_message(
                        user.notification_id
                    )

                except:
                    pass

                else:
                    await notification_message.delete()

            new_message = await user_dm_channel.send(
                GameNotifications.__get_game_notifications_message(
                    len(user.notifications)
                )
            )

            return new_message.id

        else:
            raise UserNotFound(user_id)

    @staticmethod
    async def remove_game_notification(user_id: UserId) -> bool:
        """
        Returns bool: True means message was delete
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
                else:
                    await notification_message.edit(
                        content=GameNotifications.__get_game_notifications_message(
                            len(user.notifications)
                        )
                    )

        return False

    @staticmethod
    async def game_quit(game_id: GameId, quiting_user: UserId):
        cancelled_game = await GameStatus.get(game_id)

        user_objects = {
            game_user_id: await bot.get_user(game_user_id)
            for game_user_id in cancelled_game.all_users
        }

        for game_user_id, game_user_object in user_objects.items():
            if game_user_id != quiting_user:
                await game_user_object.send(
                    embed=game_summary_embed(
                        [],
                        list(cancelled_game.usernames.values()),
                        cancelled_game,
                        f"Game was cancelled because {user_objects[quiting_user].name} quit",
                    )
                )

    @staticmethod
    async def game_expired(game_id: GameId):
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
    ):
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

            # Creats list of names of winners and other users needed for the summary embed
            all_user_ids = game_status.all_users.copy()
            winner_names = []
            for user_id in winner_ids:
                all_user_ids.remove(user_id)
                winner_names.append(game_status.usernames[str(user_id)])
            other_users_names = [
                game_status.usernames[str(user_id)] for user_id in all_user_ids
            ]

            await (await bot.get_user(user)).send(
                embed=game_summary_embed(
                    winner_names, other_users_names, game_status, footer
                )
            )
