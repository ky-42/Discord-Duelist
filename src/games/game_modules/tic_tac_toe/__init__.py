import os
from bot import bot
import discord
from dataclasses import dataclass
from games.utils import GameInfo, Game, load_game_data, load_game_state
from data_wrappers import GameStatus, GameData
from games.game_handling import GameAdmin
from typing import List, Mapping
from data_types import GameId

details = GameInfo(
    min_players=2,
    max_players=2,
    thumbnail_file_path=f'{os.path.dirname(__file__)}/thumb.jpg'
)


@dataclass
class GameDataaaa:
    current_player: int
    player_order: List[int]
    player_square_type: Mapping[int, int]
    current_board: List[List[int]]

@staticmethod
@load_game_state
async def start_game(
    game_id: GameId,
    game_state = any # type: ignore
):
    new_game_state = GameDataaaa(
        current_player=game_state.confirmed_players[0],
        player_order=game_state.confirmed_players,
        player_square_type={game_state.confirmed_players[0]: 1, game_state.confirmed_players[1]: 2},
        current_board=[[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    )

    await GameData.store_data(game_id, new_game_state)

    await (await bot.get_user(new_game_state.current_player)).send('Its your turn! Use the /reply command to play your move!')



@staticmethod
@load_game_data(GameDataaaa)
@load_game_state
async def reply(
    game_id: GameId,
    interaction: discord.Interaction,
    game_state = any, # type: ignore
    game_data = any # type: ignore
):
    if game_data.current_player == interaction.user.id:
        await interaction.response.send_message(
            content='Press a button to play your move!',
            delete_after=60*15,
            view=TicTacToeView(game_id, game_data)
        )

@staticmethod
@load_game_state
@load_game_data
async def play_move(
    game_id: GameId, 
    row: int,
    column: int,
    interaction: discord.Interaction,
    game_state = any, # type: ignore
    game_data = any # type: ignore
):
    if game_data.current_player == interaction.user.id:
        game_data.current_board[row][column] = game_data.player_square_type[game_data.current_player]
        if (winner := check_win(game_data.current_board)) != 0:
            await end_game(game_id, winner, game_state, game_data)
        else:
            game_data.current_player = game_data.player_order[0] if game_data.current_player == game_data.player_order[1] else game_data.player_order[1]
            await GameData.store_data(game_id, game_data)
            await bot.get_user(game_data.current_player).send('Its your turn! Use the /reply command to play your move!')


@staticmethod
async def end_game(
    game_id: GameId, 
    winner: int,
    game_state: GameStatus.GameState,
    game_data: GameDataaaa
):
    winning_user = await bot.get_user(game_data.player_order[winner])

    for player in game_state.confirmed_players:
        if winner > 0:
            await bot.get_user(player).send(f'Game of Tic-Tac-Toe is over! The winner is {winning_user.name}!')
        else:
            await bot.get_user(player).send('Game of Tic-Tac-Toe is over! Its a tie!')
    
    await GameAdmin.game_end(game_id, winner)

@staticmethod
def check_win(board: List[List[int]]) -> int:
    # Check rows
    for row in board:
        if row[0] == row[1] == row[2] != 0:
            return row[0]

    # Check columns
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] != 0:
            return board[0][col]

    # Check diagonals
    if board[0][0] == board[1][1] == board[2][2] != 0:
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != 0:
        return board[0][2]

    # Check for a tie
    if all(row.count(0) == 0 for row in board):
        return -1

    # No winner
    return 0


class TicTacToeButton(discord.ui.Button):
    def __init__(self, row: int, column:int, state: int):
        if state == 0:
            super().__init__(style=discord.ButtonStyle.secondary, label="U+200B", row=row)
        elif state == 1:
            super().__init__(style=discord.ButtonStyle.success, label="o", row=row, disabled=True)
        elif state == 2:
            super().__init__(style=discord.ButtonStyle.danger, label="x", row=row, disabled=True)
        
        self.row = row
        self.column = column
        
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        self.view.pressed(self.row, self.column, interaction)


class TicTacToeView(discord.ui.View):
    def __init__(self, game_id: GameId, game_data: GameDataaaa):
        super().__init__(timeout=None)
        self.game_id = game_id
        self.game_data = game_data

        for i in range(3):
            for j in range(3):
                self.add_item(TicTacToeButton(i, j, self.game_data.current_board[i][j]))
        
    async def pressed(self, row: int, column: int, interaction: discord.Interaction):
        await play_move(self.game_id, row, column, interaction)
        self.stop()