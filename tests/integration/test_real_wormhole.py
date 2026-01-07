"""Integration tests against real wormhole relay.

These tests are slow and require network access.
Uses crochet to properly bridge Twisted and synchronous pytest.
"""

import pytest
import crochet
from twisted.internet.defer import inlineCallbacks

# Initialize crochet - this starts the Twisted reactor in a thread
crochet.setup()

# Mark all tests in this module as integration
pytestmark = pytest.mark.integration


@crochet.wait_for(timeout=30)
@inlineCallbacks
def allocate_code():
    """Allocate a code from the wormhole relay."""
    from wh.core.wormhole_manager import WormholeManager

    manager = WormholeManager()
    try:
        code = yield manager.create_and_allocate_code_deferred()
        return code
    finally:
        yield manager.close_deferred()


@crochet.wait_for(timeout=60)
@inlineCallbacks
def connect_two_managers():
    """Connect two managers and verify connection."""
    from wh.core.wormhole_manager import WormholeManager
    from twisted.internet.defer import DeferredList

    manager1 = WormholeManager()
    manager2 = WormholeManager()

    try:
        # Manager 1 allocates code
        code = yield manager1.create_and_allocate_code_deferred()

        # Manager 2 uses the code
        yield manager2.create_and_set_code_deferred(code)

        # Both verify connection
        results = yield DeferredList([
            manager1.verify_connection_deferred(),
            manager2.verify_connection_deferred(),
        ])

        return (code, results[0][1], results[1][1])
    finally:
        yield DeferredList([
            manager1.close_deferred(),
            manager2.close_deferred(),
        ])


@crochet.wait_for(timeout=180)
@inlineCallbacks
def dilate_two_managers():
    """Connect and dilate two managers."""
    from wh.core.wormhole_manager import WormholeManager
    from twisted.internet.defer import DeferredList

    manager1 = WormholeManager()
    manager2 = WormholeManager()

    try:
        # Connect
        code = yield manager1.create_and_allocate_code_deferred()
        yield manager2.create_and_set_code_deferred(code)

        # Dilate both
        yield DeferredList([
            manager1.dilate_deferred(),
            manager2.dilate_deferred(),
        ])

        return (
            code,
            manager1.is_dilated,
            manager2.is_dilated,
            manager1.dilated_wormhole,
            manager2.dilated_wormhole,
        )
    finally:
        yield DeferredList([
            manager1.close_deferred(),
            manager2.close_deferred(),
        ])


class TestRealWormholeConnection:
    """Tests using real wormhole relay infrastructure."""

    def test_code_allocation(self):
        """Test allocating a code from the real relay."""
        code = allocate_code()

        assert code is not None
        assert "-" in code  # Format: number-word-word
        parts = code.split("-")
        assert len(parts) >= 2

    def test_code_format(self):
        """Test code follows number-word-word format."""
        code = allocate_code()

        parts = code.split("-")
        # First part should be numeric
        assert parts[0].isdigit()
        # Following parts should be words
        for word in parts[1:]:
            assert word.isalpha()


class TestRealWormholePair:
    """Tests with two connected wormhole instances."""

    def test_two_managers_connect(self):
        """Test two managers can connect using code."""
        code, versions1, versions2 = connect_two_managers()

        assert code is not None
        assert versions1 is not None
        assert versions2 is not None

    def test_dilation(self):
        """Test wormhole dilation between two managers."""
        code, dilated1, dilated2, dw1, dw2 = dilate_two_managers()

        assert code is not None
        assert dilated1
        assert dilated2
        assert dw1 is not None
        assert dw2 is not None
        # DilatedWormhole objects have connector_for and listener_for methods
        assert hasattr(dw1, 'connector_for')
        assert hasattr(dw1, 'listener_for')
        assert hasattr(dw2, 'connector_for')
        assert hasattr(dw2, 'listener_for')
