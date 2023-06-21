import pytest
import redis
from datetime import timedelta
import redis.asyncio as redis_sync

from . import UserStatus

db_number = UserStatus._UserStatus__db_number # type: ignore

class TestGetGame:
    conn = redis.Redis(db=db_number)
    pytestmark = pytest.mark.asyncio
    
    
    @pytest.fixture(scope="class", autouse=True)
    def setup_delete_db(self):

        yield
        
        # After tests in this class clears db
        TestGetGame.conn.flushdb()
    
    def 