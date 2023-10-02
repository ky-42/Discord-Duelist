from data_types import GameId


class PlayerNotFound(Exception):
    """Raised when looking for a player but they are not found"""

    def __init__(self, player_id: int, *args: object) -> None:
        self.player_id = player_id
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Player with id {self.player_id} not found"


class GameNotFound(Exception):
    """Raised when game is not found"""

    def __init__(self, game_name: GameId, *args: object) -> None:
        self.game_name = game_name
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Game {self.game_name} not found"
