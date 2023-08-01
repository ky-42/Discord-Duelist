from bot import bot
from data_types import GameId
from typing import List, Mapping
from data_wrappers import GameStatus, UserStatus, GameData
from .game_loading import GameLoading
from .user_ui import GameConfirm, create_confirm_embed

class GameAdmin:

    @staticmethod
    async def initialize_game(
        game_name: str,
        bet: int,
        player_one: int,
        # Does not include player one id
        secondary_player_ids: List[int],
        # Includes player one. Is in form {id: username}
        player_names: Mapping[str, str]
    ):

        game_id = GameStatus.create_game_id()

        game_details = GameStatus.GameState(
            status=0,
            game=game_name,
            bet=bet,
            starting_player=player_one,
            player_names=player_names,
            confirmed_players=[player_one],
            unconfirmed_players=secondary_player_ids
        )

        # Adds game to game status store
        await GameStatus.add_game(
            game_id,
            game_details,
            bot.game_requested_expiry
        )

        # Sends out confirmations to secondary players
        await GameAdmin.confirm_game(game_id, game_details)

    # ---------------------------------------------------------------------------- #

            

    @staticmethod
    async def start_game(game_id: GameId):
        game_details = await GameStatus.get_game(game_id)

        for player_id in game_details.confirmed_players:
            # TODO add to game status expire timer
            # TODO check if game needs to be qued
            await UserStatus.join_game(player_id, game_id)

        if await UserStatus.check_users_are_ready(game_id, game_details.confirmed_players):

            for player_id in game_details.confirmed_players:
                # a = list(game_details.player_names.values())

                # if player_id != game_details.starting_player:
                #     a.remove(game_details.player_names[str(game_details.starting_player)])
                # a.remove(game_details.player_names[str(player_id)])

                # b = ', '.join(a[:-1]) + ' and ' + a[-1]

                c = f'Game of {game_details.game} is starting!'

                await (await bot.get_user(int(player_id))).send(
                    c
                )

            game_module = GameLoading.get_game(game_details.game)
            
            await GameStatus.set_game_in_progress(game_id)
            await game_module.start_game(game_id)

        else:
            await GameStatus.set_game_queued(game_id)


    @staticmethod
    async def game_end(game_id: GameId, winner: int):
        # TODO update player status and call check game status to see if game needs to
        # next queued game to see if all players are ready now

        # This needs to be done first before the game is deleted
        game_details = await GameStatus.get_game(game_id)
        
        # Checks if after players were removed from the game if they are in another game that can start
        await UserStatus.clear_game(game_id, game_details.confirmed_players)
        for player_id in game_details.confirmed_players:
            if (user_new_game_id := await UserStatus.check_in_game(player_id)) != None:
                await GameAdmin.start_game(user_new_game_id)

                
        await GameStatus.delete_game(game_id)
        await GameData.delete_data(game_id)

    @staticmethod
    async def cancel_game(game_id: GameId):
        # Clear all game data from redis
        # so update user status, remove game status, and game data

        game_details = await GameStatus.get_game(game_id)

        # Clears external data
        if game_details.status > 1:
            await GameData.delete_data(game_id)
        if game_details.status > 0:
            await UserStatus.clear_game(game_id, game_details.confirmed_players + game_details.unconfirmed_players)
        if game_details.status > -1:
            await GameStatus.delete_game(game_id)

        # Determines what message to send to players
        if game_details.status == 0:
            cancel_message = f'A player declined the game of {game_details.game}'
        else:
            cancel_message = f'Game of {game_details.game} has been cancelled'

        # Sends message to all players
        for accepted_player_id in game_details.confirmed_players:
            try:
                await (
                    await bot.get_dm_channel(
                        accepted_player_id
                    )
                ).send(cancel_message)
            except:
                print('User not found while sending cancel game message')
        
    @staticmethod
    async def confirm_game(game_id: GameId, game_state: GameStatus.GameState) -> None:
        for player_id in game_state.unconfirmed_players:
            await GameAdmin.send_confirm(player_id, game_id, game_state)

    @staticmethod
    async def send_confirm(player_id: int, game_id: GameId, game_state: GameStatus.GameState) -> None:

        # Gets the dm channel of the player to send the confirmation over
        dm = await bot.get_dm_channel(player_id)

        await dm.send(
            embed=create_confirm_embed(
                player_id,
                game_state,
                GameLoading.get_game(game_state.game).details
            ),
            view=GameConfirm(game_id, GameAdmin.player_confirm, GameAdmin.cancel_game),
            delete_after=bot.game_requested_expiry
        )

    @staticmethod
    async def player_confirm(player_id: int, game_id: GameId):
        unconfirmed_list = await GameStatus.player_confirm(game_id, player_id)

        if len(unconfirmed_list) == 0:
            await GameAdmin.start_game(game_id)
