import time
import pytest
import redis
from datetime import timedelta
from dataclasses import asdict
from . import ConfirmMessages
import asyncio

from exceptions.game_exceptions import ActiveGameNotFound
from exceptions.general_exceptions import PlayerNotFound

db_number = ConfirmMessages._ConfirmMessages__db_number # type: ignore

class TestConfirmMessages:
    conn = redis.Redis(db=db_number)
    pytestmark = pytest.mark.asyncio
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_delete_db(self):

        yield
        
        # After tests in this class clears db
        TestConfirmMessages.conn.flushdb()

    async def test_set_messages(self):
        await ConfirmMessages.set_messages("abc", [1, 2, 3], timedelta(seconds=5))
        assert [int(x) for x in TestConfirmMessages.conn.lrange("abc", 0, -1)] == [1, 2, 3]
    
    async def test_set_messages_no_ids(self):
        await ConfirmMessages.set_messages("abc1", [], timedelta(seconds=5))
        assert TestConfirmMessages.conn.get("abc1") == None