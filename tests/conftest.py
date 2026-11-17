import sqlite3
from collections.abc import Iterator

import pytest

from src.trainer.db import connect, init_db

@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = connect(":memory:")
    init_db(connection)
    yield connection
    connection.close()
