from unittest.mock import call

import pytest
import pytest_mock

from data_types import GameId
from data_wrappers.game_status import GameStatus
from game_modules.utils import GameInfo, get_game_info
from tests.testing_data import Testing_Game
from tests.testing_data.data_generation import create_fake_game_status

pytestmark = pytest.mark.asyncio


async def test_get_game_info(mocker: pytest_mock.MockFixture):
    test_status = create_fake_game_status(
        state=0,
        game_module_name="Testing Game",
        starting_user=0,
        user_count=2,
        pending_user_count=1,
    )
    test_data = Testing_Game.TestingGameData("test")

    status_call = mocker.patch("data_wrappers.GameStatus.get", return_value=test_status)
    data_call = mocker.patch("data_wrappers.GameData.get", return_value=test_data)

    called = 0

    @get_game_info
    async def test_fn_status(
        game_info: GameInfo[GameStatus.Game, None], game_id: GameId
    ) -> None:
        assert game_info.GameStatus == test_status
        assert game_info.GameData == None

        nonlocal called
        called += 1

    @get_game_info
    async def test_fn_data(
        game_info: GameInfo[None, Testing_Game.TestingGameData], game_id: GameId
    ) -> None:
        assert game_info.GameStatus == None
        assert game_info.GameData == Testing_Game.TestingGameData("test")

        nonlocal called
        called += 1

    await test_fn_status(game_id="test")
    await test_fn_data(game_id="test")

    assert status_call.call_args == call("test")
    assert data_call.call_args == call("test", Testing_Game.TestingGameData)

    assert called == 2
