class PlayerNotFound(Exception):
    """Raised when looking for a player but they are not found"""

    def __init__(self, player_id: int, *args: object) -> None:
        self.player_id = player_id
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Player with id {self.player_id} not found"


class FuncExists(Exception):
    """Raised when a function in a dict already exists"""

    def __init__(self, func_name: str, *args: object) -> None:
        self.func_name = func_name
        super().__init__(*args)

    def __str__(self) -> str:
        return f"{self.func_name} already exists in dict"


class FuncNotFound(Exception):
    """Raised when a function not in dict"""

    def __init__(self, func_name: str, *args: object) -> None:
        self.func_name = func_name
        super().__init__(*args)

    def __str__(self) -> str:
        return f"{self.func_name} does not exist in dict"
