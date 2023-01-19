import importlib
import os
import random
from datetime import datetime
from .games import helpers

class GameAdmin:
    def __init__(self):
        self.loaded_games = {}

        for game_name in os.listdir("./games"):
            self.loaded_games[game_name] = None
    
    def get_game_details(self, game_name):
        if (game_module := self.loaded_game[game_name]) == None:
            game_module = self.__load_game(game_name)
        return game_module.detail

    # Not to be called externally and only if the game isnt loaded already
    def __load_game(self, game_name):
        game = importlib.import_module(f"games.{id}")
        self.loaded_games[name] = game
        return game
    
    def initialize_game(self, game, bet, players):
        game_id = random.randint(0, 100000000)
        game_details = {
            status: 0,
            game: game.name,
            bet: bet,
            ready_players: [],
            queued_players: [],
            unconfirmed_players: players
        }
        
        bot.game_status_pool.set(game_id, game_details)
        self.confirm_game(game_id)
    
    def confirm_game(self):
        game_details = bot.game_status_pool.get(game_id)
        
        for player_id in game_details.unconfirmed_players:
            unconfimed_player = bot.get_user(player_id)

    def player_confim(self, player_id):
        pass

    
    def start_game(self):
        pass

    def game_end(self):
        pass


            
class GameData:
    def __init__(self):
        pass

class GameBase:
    
    def play_move()
    
    def get_game_data(key):
        self.base_data['game_data'][key]
    
    def set_game_data(

Redis hashes are record types structured as collections of field-value pairs. You can use hashes to represent basic objects and 

Redis hashes are record types structured as collections of field-value pairs. You can use hashes to represent basic objects and key, value):
        self.base_data['game_data'][key] = value
    