"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Test configuration and fixtures for the VeloSim backend.

# This module contains pytest configuration and shared fixtures
# for testing the backend application.

import sys
import os
from typing import Generator
import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from back.tests.mock_utils import create_mock_db_session

# ---------------------------------------------------------------------------
# Silence external I/O BEFORE any back/grafana_logging imports.
#
# grafana_logging.logger evaluates LOG_TO_LOKI and LOG_TO_CONSOLE at module
# import time (module-level booleans). Setting these env vars here — before
# 'from back.main import app' triggers the import chain — ensures that NO
# LokiHandler or StreamHandler is ever attached to any logger during tests.
#
# Without this, every logger.info/error call blocks for ~2 s waiting for a
# TCP connection to the Loki instance that doesn't exist in the test
# environment, making the full test suite take 10+ minutes.
# ---------------------------------------------------------------------------
os.environ["LOG_TO_LOKI"] = "false"
os.environ["LOG_TO_CONSOLE"] = "false"

# Set dummy GraphHopper URL for tests to prevent connection errors
# This must be set before any simulation code tries to initialize GraphHopperConnection
if "GRAPHHOPPER_URL" not in os.environ:
    os.environ["GRAPHHOPPER_URL"] = "http://localhost:8989"

# Add the back directory to Python path for relative imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 'app' can now safely be imported
from back.main import app  # noqa: E402
from back.database.session import get_db, Base  # noqa: E402
import back.models  # noqa: F401, E402

# Test database URL (use in-memory SQLite for tests)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    """Override database dependency for testing with proper transaction management."""
    db = TestingSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Create test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def disable_external_logging() -> Generator[None, None, None]:
    """Strip LokiHandler from all loggers that were created before conftest ran.

    Acts as a belt-and-suspenders guard: LOG_TO_LOKI / LOG_TO_CONSOLE env vars
    above prevent *new* handlers from being added, but modules imported at
    package load time may have already called get_logger() and cached a logger
    with a LokiHandler attached.  This fixture removes those handlers so no
    HTTP call to Loki is ever made during the test session.
    """
    import logging

    try:
        from grafana_logging.logger import LokiHandler
    except ImportError:
        LokiHandler = None  # type: ignore[assignment,misc]

    def _strip(logger: logging.Logger) -> None:
        if LokiHandler is not None:
            for h in list(logger.handlers):
                if isinstance(h, LokiHandler):
                    logger.removeHandler(h)
                    h.close()
        # Also silence StreamHandlers so stdout isn't flooded during tests
        for h in list(logger.handlers):
            if isinstance(h, logging.StreamHandler):
                logger.removeHandler(h)
                h.close()

    # Strip handlers from every logger currently registered in the hierarchy
    root = logging.getLogger()
    _strip(root)
    for name in list(logging.Logger.manager.loggerDict):
        inst = logging.Logger.manager.loggerDict[name]
        if isinstance(inst, logging.Logger):
            _strip(inst)

    yield


@pytest.fixture
def mock_db() -> Mock:
    """Create a mock database session for unit testing without real DB."""
    return create_mock_db_session()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create test client."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
