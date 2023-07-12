import pytest
import redis
from datetime import timedelta
from dataclasses import asdict
from . import GameStatus

db_number = GameStatus._GameStatus__db_number # type: ignore

class TestGameData:
    conn = redis.Redis(db=db_number)
    pytestmark = pytest.mark.asyncio
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_delete_db(self):

        yield
        
        # After tests in this class clears db
        TestGameData.conn.flushdb()