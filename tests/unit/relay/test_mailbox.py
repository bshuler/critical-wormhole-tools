"""
Unit tests for the mailbox server.
"""

import pytest
from wh.relay.mailbox import MailboxServer, Mailbox, Nameplate


class TestMailbox:
    """Tests for the Mailbox class."""

    def test_create_mailbox(self):
        """Test creating a mailbox."""
        mailbox = Mailbox(id="test-mailbox")
        assert mailbox.id == "test-mailbox"
        assert len(mailbox.sides) == 0
        assert len(mailbox.messages) == 0

    def test_add_message(self):
        """Test adding a message to a mailbox."""
        mailbox = Mailbox(id="test-mailbox")
        msg = mailbox.add_message("side1", "pake", '{"body": "test"}')

        assert msg.side == "side1"
        assert msg.phase == "pake"
        assert msg.body == '{"body": "test"}'
        assert len(mailbox.messages) == 1

    def test_get_messages(self):
        """Test getting messages from a mailbox."""
        mailbox = Mailbox(id="test-mailbox")
        mailbox.add_message("side1", "pake", "msg1")
        mailbox.add_message("side2", "pake", "msg2")
        mailbox.add_message("side1", "version", "msg3")

        # Get all messages
        all_msgs = mailbox.get_messages()
        assert len(all_msgs) == 3

        # Get messages excluding side1
        other_msgs = mailbox.get_messages(exclude_side="side1")
        assert len(other_msgs) == 1
        assert other_msgs[0].side == "side2"

    def test_message_has_id_and_timestamp(self):
        """Test that messages have ID and timestamp."""
        mailbox = Mailbox(id="test-mailbox")
        msg = mailbox.add_message("side1", "pake", "test")

        assert msg.id is not None
        assert len(msg.id) > 0
        assert msg.timestamp > 0


class TestNameplate:
    """Tests for the Nameplate class."""

    def test_create_nameplate(self):
        """Test creating a nameplate."""
        nameplate = Nameplate(id="7", mailbox_id="abc123")
        assert nameplate.id == "7"
        assert nameplate.mailbox_id == "abc123"
        assert len(nameplate.sides) == 0

    def test_nameplate_sides(self):
        """Test adding sides to a nameplate."""
        nameplate = Nameplate(id="7", mailbox_id="abc123")
        nameplate.sides.add("side1")
        nameplate.sides.add("side2")

        assert len(nameplate.sides) == 2
        assert "side1" in nameplate.sides
        assert "side2" in nameplate.sides


class TestMailboxServer:
    """Tests for the MailboxServer class."""

    def test_create_server(self):
        """Test creating a mailbox server."""
        server = MailboxServer(host="127.0.0.1", port=4000)
        assert server.host == "127.0.0.1"
        assert server.port == 4000
        assert len(server.nameplates) == 0
        assert len(server.mailboxes) == 0

    def test_custom_app_id(self):
        """Test custom app ID."""
        server = MailboxServer(app_id="custom-app/v1")
        assert server.app_id == "custom-app/v1"

    @pytest.mark.asyncio
    async def test_allocate_nameplate(self):
        """Test allocating nameplates."""
        server = MailboxServer()

        # Simulate allocating nameplates
        async with server._nameplate_lock:
            np1 = str(server._next_nameplate)
            server._next_nameplate += 1
            np2 = str(server._next_nameplate)
            server._next_nameplate += 1

        assert np1 == "1"
        assert np2 == "2"

    def test_initial_state(self):
        """Test initial server state."""
        server = MailboxServer()
        assert server._running is False
        assert server._server is None
        assert len(server.client_subscriptions) == 0
