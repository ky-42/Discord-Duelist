from dataclasses import dataclass
from exceptions import ToManyPlayers, NotEnoughPlayers

@dataclass
class GameInfo:
    min_players: int
    max_players: int
    
    def check_player_count(self, player_count):
        if player_count < self.min_players:
            raise NotEnoughPlayers(player_count, self.min_players)
        if player_count > self.max_players:
            raise ToManyPlayers(player_count, self.max_players)
        return True
