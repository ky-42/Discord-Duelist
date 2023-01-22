from dataclasses import dataclass

@dataclass
class GameInfo:
    min_players: int
    max_players: int
    
    def check_player_count(self, player_count):
        if player_count >= self.min_players and player_count <= self.max_players:
            return True
        return False
