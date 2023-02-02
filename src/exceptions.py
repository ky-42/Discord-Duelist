
class GameNotFound(Exception):
    """Raised when game is not found in db"""

class PlayerNotFound(Exception):
    """Raised when looking for a player but they are not found"""
    
    def __init__(self, player_id: int, *args: object) -> None:
        self.player_id = player_id
        super().__init__(*args)
        
    def __str__(self) -> str:
        return f"Player with id {self.player_id} not found"

class ToManyPlayers(Exception):
    """Raised when game is trying to initialize with to many players"""
    
    def __init__(self, player_count:int, max_player_count:int, *args: object) -> None:
        self.player_count = player_count
        self.max_player_count = max_player_count
        super().__init__(*args)
    
    def __str__(self) -> str:
        return f'This game supports up to {self.max_player_count} players but you tryed to play with {self.player_count} players!'

class NotEnoughPlayers(Exception):
    """Raised when game is trying to initialize with not enough players"""
    
    def __init__(self, player_count:int, min_player_count:int, *args: object) -> None:
        self.player_count = player_count
        self.min_player_count = min_player_count
        super().__init__(*args)

    def __str__(self) -> str:
        return f'This game supports up to {self.min_player_count} players but you tryed to play with {self.player_count} players!'
