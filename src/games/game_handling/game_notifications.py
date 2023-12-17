import random

from bot import bot
from data_types import GameId, UserId
from data_wrappers.game_status import GameStatus
from data_wrappers.user_status import UserStatus
from exceptions import PlayerNotFound
from user_interfaces.game_embeds import game_summary_embed


class GameNotifications:
    @staticmethod
    async def game_end(
        game_id: GameId,
        winner_ids: list[int],
    ):
        game_status = await GameStatus.get(game_id)

        for player in game_status.all_players:
            if len(winner_ids):
                if player in winner_ids:
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

            # Creats list of names of winners and other players needed for the summary embed
            all_player_ids = game_status.all_players.copy()
            winner_names = []
            for player_id in winner_ids:
                all_player_ids.remove(player_id)
                winner_names.append(game_status.player_names[str(player_id)])
            other_players_names = [
                game_status.player_names[str(player_id)] for player_id in all_player_ids
            ]

            await (await bot.get_user(player)).send(
                embed=game_summary_embed(
                    winner_names, other_players_names, game_status, footer
                )
            )

    @staticmethod
    def __get_game_notifications_message(notification_amount: int):
        if notification_amount > 1:
            return f"You have {notification_amount} notifications! Use the /reply command to view them!"
        else:
            return f"You have a notification! Use the /reply command to view it!"

    @staticmethod
    async def add_game_notification(player_id: UserId):
        user = await UserStatus.get(player_id)
        user_dm_channel = await bot.get_dm_channel(player_id)

        if user:
            if user.notification_id:
                notification_message = await user_dm_channel.fetch_message(
                    user.notification_id
                )
                await notification_message.delete()

            new_message = await user_dm_channel.send(
                GameNotifications.__get_game_notifications_message(
                    len(user.notifications)
                )
            )

            await UserStatus.set_notification_id(player_id, new_message.id)

        else:
            raise PlayerNotFound(player_id)

    @staticmethod
    async def remove_game_notification(player_id: UserId):
        user = await UserStatus.get(player_id)
        user_dm_channel = await bot.get_dm_channel(player_id)

        if user:
            if user.notification_id:
                notification_message = await user_dm_channel.fetch_message(
                    user.notification_id
                )

                if len(user.notifications) == 0:
                    await notification_message.delete()
                else:
                    await notification_message.edit(
                        content=GameNotifications.__get_game_notifications_message(
                            len(user.notifications)
                        )
                    )
