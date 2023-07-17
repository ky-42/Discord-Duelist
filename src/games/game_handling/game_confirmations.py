from data_types import GameId
from bot import bot
from data_wrappers import GameStatus, UserStatus

class GameConfirmations:
    @staticmethod
    async def confirm_game(game_id: GameId, game_state: GameStatus.GameState):
        for player_id in game_state.unconfirmed_players:
            await GameAdmin.send_confirm(player_id, game_id, game_state)

    @staticmethod
    async def send_confirm(player_id: int, game_id: GameId, game_state: GameStatus.GameState):

        # Gets the dm channel of the player to send the confirmation over
        dm = await bot.get_dm_channel(player_id)

        await dm.send(
            embed=create_confirm_embed(
                player_id,
                game_state,
                GameLoading.get_game(game_state.game).details
            ),
            view=GameConfirm(game_id),
            delete_after=bot.game_requested_expiery
        )

    # ---------------------------------------------------------------------------- #

    @staticmethod
    async def player_confirm(player_id: int, game_id: GameId):
        #TODO maybe redo this part
        print('player confirm')
        unconfirmed_list = await GameStatus.player_confirm(game_id, player_id)

        if len(unconfirmed_list) == 0:
            print('player confirm')
            await GameAdmin.game_confirmed(game_id)

    @staticmethod
    async def reject_game(game_id: GameId, rejecting_player: discord.User | discord.Member):
        game_details = await GameStatus.get_game(game_id)

        for player_id in game_details.confirmed_players:
            await bot.get_user(int(player_id)).send(
                f'{rejecting_player.name} has rejected the game of {game_details.game} the you accepted'
            )
        
        await GameAdmin.cancel_game(game_id)

    # ---------------------------------------------------------------------------- #

    @staticmethod
    async def game_confirmed(game_id: GameId):
        # TODO add to game status expire timer
        # TODO check if game needs to be qued

        game_details = await GameStatus.get_game(game_id)


        for player_id in game_details.confirmed_players:
            await UserStatus.join_game(player_id, game_id)

        await GameAdmin.start_game(game_id)