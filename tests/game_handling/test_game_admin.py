from unittest.mock import call

import pytest
import pytest_mock

from data_types import DiscordMessage
from game_handling import GameAdmin
from tests.testing_data import Testing_Game
from tests.testing_data.data_generation import generate_game_status

pytestmark = pytest.mark.asyncio(scope="module")


async def test_user_selected(mocker: pytest_mock.MockFixture):
    test_status = generate_game_status(
        state=0,
        game_module_name="Testing Game",
        user_count=1,
        pending_user_count=0,
    )

    details_call = mocker.patch(
        "game_modules.GameModuleLoading.check_game_module_details", return_value=True
    )
    mocker.patch("data_wrappers.GameStatus.add", return_value="game_id")
    mocker.patch("game_handling.GameNotifications.send_game_invites", return_value=None)

    assert isinstance(
        await GameAdmin.users_selected(test_status, {"10000": "10000"}), DiscordMessage
    )

    details_call.assert_called_once_with("Testing Game", 2)

    assert len(test_status.all_users) == 2
    assert test_status.pending_users == [10000]
    assert test_status.usernames.get("10000") == "10000"


async def test_user_accepted(mocker: pytest_mock.MockFixture):
    test_status = generate_game_status(
        state=0,
        game_module_name="Testing Game",
        user_count=2,
        pending_user_count=1,
    )

    mocker.patch("data_wrappers.GameStatus.user_accepted", return_value=[])
    start_call = mocker.patch(
        "game_handling.GameAdmin._GameAdmin__start_game", return_value=None
    )

    await GameAdmin._GameAdmin__user_accepted("game_id", 10000)  # type: ignore

    start_call.assert_called_once_with("game_id")


async def test_start_game_max_games(mocker: pytest_mock.MockFixture):
    mocker.patch(
        "data_wrappers.GameStatus.get",
        return_value=generate_game_status(
            state=0,
            game_module_name="Testing Game",
            user_count=2,
            pending_user_count=0,
        ),
    )

    mocker.patch("data_wrappers.UserStatus.join_game", return_value=False)

    max_games_call = mocker.patch("game_handling.GameNotifications.max_games")
    delete_call = mocker.patch("game_handling.GameAdmin.delete_game")

    await GameAdmin._GameAdmin__start_game("game_id")  # type: ignore

    max_games_call.assert_called_once_with("game_id", 0)
    delete_call.assert_called_once_with("game_id")


async def test_start_game_que(mocker: pytest_mock.MockFixture):
    mocker.patch(
        "data_wrappers.GameStatus.get",
        return_value=generate_game_status(
            state=0,
            game_module_name="Testing Game",
            user_count=2,
            pending_user_count=0,
        ),
    )

    mocker.patch("data_wrappers.UserStatus.join_game", return_value=True)
    mocker.patch("data_wrappers.UserStatus.check_users_are_ready", return_value=False)

    que_call = mocker.patch("game_handling.GameNotifications.game_queued")
    state_call = mocker.patch("data_wrappers.GameStatus.set_game_state")
    expiry_call = mocker.patch("data_wrappers.GameStatus.set_expiry")

    await GameAdmin._GameAdmin__start_game("game_id")  # type: ignore

    que_call.assert_called_once_with("game_id")
    state_call.assert_called_once()
    expiry_call.assert_called_once()


async def test_start_game(mocker: pytest_mock.MockFixture):
    mocker.patch(
        "data_wrappers.GameStatus.get",
        return_value=generate_game_status(
            state=0,
            game_module_name="Testing Game",
            user_count=2,
            pending_user_count=0,
        ),
    )

    mocker.patch("data_wrappers.UserStatus.join_game", return_value=True)
    mocker.patch("data_wrappers.UserStatus.check_users_are_ready", return_value=True)

    start_call = mocker.patch("game_handling.GameNotifications.game_start")
    module_call = mocker.patch(
        "game_modules.GameModuleLoading.get_game_module",
        return_value=Testing_Game.load(),
    )
    state_call = mocker.patch("data_wrappers.GameStatus.set_game_state")
    expire_call = mocker.patch("data_wrappers.GameStatus.set_expiry")
    start_game_call = mocker.patch(
        "tests.testing_data.Testing_Game.TestingGame.start_game"
    )

    await GameAdmin._GameAdmin__start_game("game_id")  # type: ignore

    start_call.assert_called_once_with("game_id")
    module_call.assert_called_once_with("Testing Game")
    state_call.assert_called_once()
    expire_call.assert_called_once()
    start_game_call.assert_called_once()


async def test_reply(mocker: pytest_mock.MockFixture):
    mocker.patch(
        "data_wrappers.GameStatus.get",
        return_value=generate_game_status(
            state=2,
            game_module_name="Testing Game",
            user_count=2,
            pending_user_count=0,
        ),
    )

    mocker.patch("data_wrappers.GameStatus.set_expiry")
    mocker.patch(
        "game_modules.GameModuleLoading.get_game_module",
        return_value=Testing_Game.load(),
    )
    mocker.patch(
        "tests.testing_data.Testing_Game.TestingGame.reply",
        return_value=DiscordMessage("test"),
    )

    assert await GameAdmin.reply("game_id", 10000) == DiscordMessage("test")


async def test_delete_unstarted_game(mocker: pytest_mock.MockFixture):
    mocker.patch(
        "data_wrappers.GameStatus.get",
        return_value=generate_game_status(
            state=0,
            game_module_name="Testing Game",
            user_count=2,
            pending_user_count=0,
        ),
    )

    status_delete_call = mocker.patch("data_wrappers.GameStatus.delete")

    await GameAdmin.delete_game("game_id")

    status_delete_call.assert_called_once_with("game_id")


async def test_delete_game(mocker: pytest_mock.MockFixture):
    mocker.patch(
        "data_wrappers.GameStatus.get",
        return_value=generate_game_status(
            state=2,
            game_module_name="Testing Game",
            user_count=2,
            pending_user_count=0,
        ),
    )

    data_delete_call = mocker.patch("data_wrappers.GameData.delete")
    clear_call = mocker.patch(
        "data_wrappers.UserStatus.clear_game",
        return_value=(["test", "test_two"], [0]),
    )
    remove_notification_call = mocker.patch(
        "game_handling.GameNotifications.removed_game_notification"
    )
    start_call = mocker.patch("game_handling.GameAdmin._GameAdmin__start_game")
    status_delete_call = mocker.patch("data_wrappers.GameStatus.delete")

    await GameAdmin.delete_game("game_id")

    data_delete_call.assert_called_once_with("game_id")
    clear_call.assert_called_once()

    remove_notification_call.assert_called_once_with(0)

    assert start_call.call_count == 2
    start_call.assert_has_calls([call("test"), call("test_two")])

    status_delete_call.assert_called_once_with("game_id")
