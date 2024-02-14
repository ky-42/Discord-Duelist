from unittest.mock import ANY, AsyncMock, Mock, call

import pytest
import pytest_mock

from game_handling.game_notifications import GameNotifications

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_message():
    mock_message = AsyncMock()
    mock_message.id = 0
    mock_message.delete.return_value = 0
    mock_message.edit.return_value = 1

    return mock_message


@pytest.fixture
def mock_dm(mock_message, mocker: pytest_mock.MockerFixture):
    mock_user_dm = AsyncMock()
    mock_user_dm.fetch_message.return_value = mock_message
    mock_user_dm.send.return_value = mock_message

    mocker.patch("bot.Bot.get_dm_channel", return_value=mock_user_dm)

    return mock_user_dm


async def test_added_game_notification_delete(
    mock_message, mock_dm, mocker: pytest_mock.MockFixture
):
    mock_user_status = AsyncMock()
    mock_user_status.notification_id = 1
    mock_user_status.notifications = ["one"]

    mocker.patch("data_wrappers.UserStatus.get", return_value=mock_user_status)

    mocker.patch("bot.Bot.get_dm_channel", return_value=mock_dm)

    await GameNotifications.added_game_notification(0)

    mock_dm.fetch_message.assert_called_once_with(1)
    mock_message.delete.assert_called_once()
    mock_dm.send.assert_called_once()


async def test_added_game_notification_no_delete(
    mock_message, mock_dm, mocker: pytest_mock.MockFixture
):
    mock_user_status = AsyncMock()
    mock_user_status.notification_id = None
    mock_user_status.notifications = ["one"]

    mocker.patch("data_wrappers.UserStatus.get", return_value=mock_user_status)

    assert not await GameNotifications.added_game_notification(0)

    mock_dm.fetch_message.assert_not_called()
    mock_message.delete.assert_not_called()
    mock_dm.send.assert_called_once()


async def test_removed_game_notification_delete(
    mock_message, mock_dm, mocker: pytest_mock.MockFixture
):
    mock_user_status = AsyncMock()
    mock_user_status.notification_id = 1
    mock_user_status.notifications = []

    mocker.patch("data_wrappers.UserStatus.get", return_value=mock_user_status)

    assert await GameNotifications.removed_game_notification(0)

    mock_dm.fetch_message.assert_called_once_with(1)
    mock_message.delete.assert_called_once()


async def test_removed_game_notification_no_delete(
    mock_message,
    mock_dm,
    mocker: pytest_mock.MockFixture,
):
    mock_user_status = AsyncMock()
    mock_user_status.notification_id = 1
    mock_user_status.notifications = ["one"]

    mocker.patch("data_wrappers.UserStatus.get", return_value=mock_user_status)

    assert not await GameNotifications.removed_game_notification(0)

    mock_dm.fetch_message.assert_called_once_with(1)
    mock_message.delete.assert_not_called()
    mock_message.edit.assert_called_once()


async def test_removed_game_notification_unsynced(
    mocker: pytest_mock.MockFixture,
):
    mock_user_status = AsyncMock()
    mock_user_status.notification_id = None
    mock_user_status.notifications = ["one"]

    mocker.patch("data_wrappers.UserStatus.get", return_value=mock_user_status)

    mock_add_call = mocker.patch(
        "game_handling.GameNotifications.added_game_notification"
    )

    assert not await GameNotifications.removed_game_notification(0)

    mock_add_call.assert_called_once_with(0)


async def test_game_end(mocker: pytest_mock.MockFixture):
    mock_game_status = Mock()
    mock_game_status.all_users = [0, 1]
    mock_game_status.usernames = {"0": "0", "1": "1"}
    mocker.patch("data_wrappers.GameStatus.get", return_value=mock_game_status)

    mocker.patch("bot.Bot.get_user_obj", autospec=True)
    mock_summary_call = mocker.patch(
        "game_handling.game_notifications.game_summary_embed", autospec=True
    )

    await GameNotifications.game_end("game_id", [1])

    mock_summary_call.assert_has_calls(
        [
            call(
                ["1"],
                ["0"],
                mock_game_status,
                "You won!",
            ),
            call(
                ["1"],
                ["0"],
                mock_game_status,
                ANY,
            ),
        ],
        any_order=True,
    )


async def test_game_end_tie(mocker: pytest_mock.MockFixture):
    mock_game_status = Mock()
    mock_game_status.all_users = [0, 1]
    mock_game_status.usernames = {"0": "0", "1": "1"}
    mocker.patch("data_wrappers.GameStatus.get", return_value=mock_game_status)

    mocker.patch("bot.Bot.get_user_obj", autospec=True)
    mock_summary_call = mocker.patch(
        "game_handling.game_notifications.game_summary_embed", autospec=True
    )

    await GameNotifications.game_end("game_id", [])

    mock_summary_call.assert_has_calls(
        [
            call(
                [],
                ["0", "1"],
                mock_game_status,
                "Its a tie!",
            ),
            call(
                [],
                ["0", "1"],
                mock_game_status,
                "Its a tie!",
            ),
        ],
        any_order=True,
    )
