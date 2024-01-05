"""Contains classes for defining aspects of game modules"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from data_types import DiscordMessage, GameId, UserId
from data_types.protocols import IsDataclass
from data_wrappers import GameData, GameStatus
from data_wrappers.user_status import UserStatus
from game_handling.game_admin import GameAdmin
from game_handling.game_notifications import GameNotifications
from game_modules.utils import GameInfo, get_game_info


@dataclass
class GameModuleDetails:
    """Holds the details of a game module.

    Attributes:
        min_users (int): Minimum number of users needed to play the game.
        max_users (int): Maximum number of users that can play the game.
        thumbnail_file_path (str): Path to the thumbnail image for the game.
    """

    min_users: int
    max_users: int
    thumbnail_file_path: str

    def check_valid_user_count(self, user_count) -> bool:
        return user_count >= self.min_users and user_count <= self.max_users


class GameModule(ABC):
    """Abstract class for defining a game module.

    This module should be inherited by all game modules.
    """

    GameStatus = GameStatus.Game

    @staticmethod
    @abstractmethod
    def get_details() -> GameModuleDetails:
        pass

    @staticmethod
    @abstractmethod
    @get_game_info
    async def start_game(
        game_info: GameInfo[GameStatus, None],
        game_id: GameId,
    ) -> None:
        """Called after all users have accepted and are ready to start the game.

        Should be overridden by all game modules with functionality to start
        the game. This includes sending the first notification to the users and
        setting up the game data.

        Args:
            game_id (GameId): Id of game thats starting.
        """

        pass

    @staticmethod
    @abstractmethod
    @get_game_info
    async def reply(
        game_info: GameInfo[GameStatus, IsDataclass], game_id: GameId, user_id: UserId
    ) -> DiscordMessage:
        """Method called when a user replies to a game notification.

        Should send user the interface for the game.

        Args:
            game_id (GameId): Id of game the user is replying to.
            user_id (UserId): Id of user replying.

        Returns:
            DiscordMessage: Message to be sent to the user.
        """

        pass

    @staticmethod
    async def send_notification(game_id: GameId, user_id: UserId) -> None:
        """Send a notification to a user that they should reply to a game"""

        await UserStatus.add_notifiction(game_id, user_id)
        new_message_id = await GameNotifications.added_game_notification(user_id)
        await UserStatus.set_notification_id(user_id, new_message_id)

    @staticmethod
    async def remove_notification(game_id: GameId, user_id: UserId) -> None:
        """Remove a notification from a user.

        Should be called after user replies to a game.
        """

        await UserStatus.remove_notification(game_id, user_id)
        if await GameNotifications.removed_game_notification(user_id):
            await UserStatus.remove_notification_id(user_id)

    @staticmethod
    async def store_game_data(game_id: GameId, game_data: IsDataclass) -> None:
        await GameData.store_data(game_id, game_data)

    @staticmethod
    async def game_over(
        game_id: GameId,
        winner_ids: list[int],
    ) -> None:
        """Clears data and notify users that the game has ended.

        Args:
            game_id (GameId): Id of game to end.
            winner_ids (list[int]): List of ids of users who won the game.
        """

        await GameNotifications.game_end(game_id, winner_ids)
        await GameAdmin.delete_game(game_id)
