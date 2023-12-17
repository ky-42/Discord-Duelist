import functools
from datetime import timedelta

from discord import Embed

from bot import bot
from data_types import DiscordMessage, GameId, UserId
from data_wrappers import GameData, GameStatus, UserStatus
from games.game_handling.game_notifications import GameNotifications
from user_interfaces.game_embeds import game_info_embed, game_summary_embed
from user_interfaces.game_views import GameConfirm

from .game_loading import GameLoading


class GameAdmin:
    @staticmethod
    async def players_selected(game_details: GameStatus.Game, players: dict[str, str]):
        # Add 1 to the player count to include the player who started the game
        if GameLoading.check_game_details(game_details.game, len(players) + 1):
            for player_id, player_name in players.items():
                game_details.player_names[player_id] = player_name
                game_details.all_players.append(int(player_id))
                game_details.unconfirmed_players.append(int(player_id))

            # Adds game to game status store
            game_id = await GameStatus.add(game_details, bot.game_requested_expiry)

            # Sends out confirmations to secondary players
            await GameAdmin.confirm_game(game_id, game_details)
        else:
            raise ValueError("Invalid game details")

    @staticmethod
    async def confirm_game(game_id: GameId, game_state: GameStatus.Game) -> None:
        for player_id in game_state.unconfirmed_players:
            await GameAdmin.send_confirm(player_id, game_id, game_state)

    @staticmethod
    async def send_confirm(
        player_id: int, game_id: GameId, game_state: GameStatus.Game
    ) -> None:
        # Gets the dm channel of the player to send the confirmation over
        dm = await bot.get_dm_channel(player_id)

        await dm.send(
            embed=game_info_embed(
                player_id,
                f"{game_state.player_names[str(game_state.starting_player)]} wants to play a game!",
                game_state,
                GameLoading.get_game(game_state.game).get_details(),
                f"Invite expires in {str(int((bot.game_requested_expiry.total_seconds()//60)%60))} minute",
            ),
            view=GameConfirm(
                functools.partial(GameAdmin.player_confirm, game_id, player_id),
                functools.partial(GameAdmin.cancel_game, game_id),
            ),
            delete_after=bot.game_requested_expiry.seconds,
        )

    @staticmethod
    async def player_confirm(game_id: GameId, player_id: int):
        unconfirmed_list = await GameStatus.confirm_player(game_id, player_id)

        if len(unconfirmed_list) == 0:
            await GameAdmin.start_game(game_id)

    @staticmethod
    async def start_game(game_id: GameId):
        game_status = await GameStatus.get(game_id)

        for player_id in game_status.all_players:
            # Works when called on a game that was qued
            # cause join game checks if user is already in game
            await UserStatus.join_game(player_id, game_id)

        if await UserStatus.check_users_are_ready(game_id, game_status.all_players):
            for player_id in game_status.all_players:
                await (await bot.get_user(int(player_id))).send(
                    embed=game_info_embed(
                        player_id,
                        "Game Started",
                        game_status,
                        GameLoading.get_game(game_status.game).get_details(),
                        f"Game will be ended if {bot.game_no_move_expiry.days} days elapses between replys",
                    )
                )

            game_module = GameLoading.get_game(game_status.game)

            await GameStatus.set_game_in_progress(game_id)
            await GameStatus.set_expiry(game_id, bot.game_no_move_expiry)
            await game_module.start_game(game_id)

        else:
            for player_id in game_status.all_players:
                await (await bot.get_user(int(player_id))).send(
                    embed=game_info_embed(
                        player_id,
                        "Game Queued",
                        game_status,
                        GameLoading.get_game(game_status.game).get_details(),
                    )
                )

            await GameStatus.set_game_queued(game_id)
            await GameStatus.set_expiry(game_id, None)

    @staticmethod
    async def reply(game_id: GameId, replying_user: UserId) -> DiscordMessage:
        only_game_details = await GameStatus.get(game_id)

        await GameStatus.set_expiry(game_id, bot.game_no_move_expiry)

        return await GameLoading.get_game(only_game_details.game).reply(
            game_id, replying_user
        )

    @staticmethod
    async def quit_game(game_id: GameId, user_id: UserId) -> DiscordMessage:
        """
        Used when player quits a game to both cancel the game and inform other players
        """

        cancelled_game = await GameStatus.get(game_id)

        user_objects = {
            game_user_id: await bot.get_user(game_user_id)
            for game_user_id in cancelled_game.all_players
        }

        for game_user_id, game_user_object in user_objects.items():
            if game_user_id != user_id:
                await game_user_object.send(
                    embed=game_summary_embed(
                        [],
                        list(cancelled_game.player_names.values()),
                        cancelled_game,
                        f"Game was cancelled because {user_objects[user_id].name} quit",
                    )
                )

        await GameAdmin.cancel_game(game_id)

        return DiscordMessage("Game Quit")

    @staticmethod
    async def cancel_game(game_id: GameId):
        # Clear all game data from redis
        # so update user status, remove game status, and game data

        game_details = await GameStatus.get(game_id)

        # Clears external data
        if game_details.status > 1:
            await GameData.delete_data(game_id)
        if game_details.status > 0:
            (
                moved_up_games,
                users_with_removed_notification,
            ) = await UserStatus.clear_game(
                game_id,
                game_details.all_players,
            )

            for user in users_with_removed_notification:
                await GameNotifications.remove_game_notification(user)

            # Trys to start any games there were moved from que to active
            for moved_up_game in moved_up_games:
                await GameAdmin.start_game(moved_up_game)

        if game_details.status > -1:
            await GameStatus.delete(game_id)
