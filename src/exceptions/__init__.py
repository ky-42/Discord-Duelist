from data_types import GameId, UserId


class UserNotFound(Exception):
    """Raised when user can not be found.

    Attributes:
        user_id: user id that was not found.
    """

    def __init__(self, user_id: UserId, *args: object) -> None:
        """Initializes the exception with the user id.

        Args:
            user_id (UserId): Id of the user that was not found.
        """

        self.user_id = user_id
        super().__init__(*args)

    def __str__(self) -> str:
        return f"User with id {self.user_id} not found"


class GameNotFound(Exception):
    """Raised when game is not found.

    Attributes:
        game_id: game id that was not found.
    """

    def __init__(self, game_id: GameId, *args: object) -> None:
        """Initializes the exception with the game id.

        Args:
            game_id (GameId): Id of the game that was not found.
        """

        self.game_id = game_id
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Game with id {self.game_id} not found"
