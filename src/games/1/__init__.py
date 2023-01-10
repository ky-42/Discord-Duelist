import importlib

helpers = importlib.import_module("games.helpers")

name = "Tic Tac Toe"

details = helpers.game_details(
    min_players = 2,
    max_players = 2
)
