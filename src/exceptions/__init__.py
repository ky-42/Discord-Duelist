from data_types import GameId


class UserNotFound(Exception):
    """Raised when looking for a user but they are not found"""

    def __init__(self, user_id: int, *args: object) -> None:
        self.user_id = user_id
        super().__init__(*args)

    def __str__(self) -> str:
        return f"User with id {self.user_id} not found"


class GameNotFound(Exception):
    """Raised when game is not found"""

    def __init__(self, game_name: GameId, *args: object) -> None:
        self.game_name = game_name
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Game {self.game_name} not found"
