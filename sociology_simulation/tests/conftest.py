from __future__ import annotations

import asyncio


def pytest_sessionstart(session):  # type: ignore[unused-argument]
    """Ensure a default asyncio event loop exists for tests that directly use
    get_event_loop().run_until_complete(). Always create and set one at session start.
    """
    asyncio.set_event_loop(asyncio.new_event_loop())


def _pick_free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def pytest_configure(config):  # type: ignore[unused-argument]
    # Nothing for now; reserved for future global test setup.
    pass


def pytest_unconfigure(config):  # type: ignore[unused-argument]
    # Close event loop if present to avoid resource warnings.
    try:
        loop = asyncio.get_event_loop()
        loop.close()
    except Exception:
        pass


import pytest


@pytest.fixture
def random_free_port() -> int:
    """Return an ephemeral free TCP port for local tests."""
    return _pick_free_port()


@pytest.fixture(autouse=True)
def _ensure_event_loop_per_test():
    """Guarantee an event loop exists in each test context that may call
    asyncio.get_event_loop().run_until_complete().
    """
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
