"""Unit tests for wormhole daemon."""

import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path


class TestWormholeDaemon:
    """Tests for WormholeDaemon class."""

    def test_init_defaults(self):
        """Test default initialization values."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()
        assert daemon.port == 9475
        assert daemon.verbose is False
        assert daemon.connections == {}

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon(port=8080, verbose=True)
        assert daemon.port == 8080
        assert daemon.verbose is True


class TestDaemonRelayEndpoint:
    """Tests for the daemon relay config endpoint."""

    @pytest.mark.asyncio
    async def test_handle_get_relays(self):
        """Test that handle_get_relays returns relay config."""
        from wh.cli.daemon import WormholeDaemon
        from wh.relay.config import RelayConfigManager

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Set up test config
            config_manager = RelayConfigManager(config_dir=config_dir)
            config_manager.add_relay(
                name="test_relay",
                mailbox_url="ws://test:4000/v1",
                transit_url="tcp:test:4001",
                description="Test relay",
                set_default=True,
            )

            daemon = WormholeDaemon()

            # Mock request object
            request = MagicMock()

            # Mock get_relay_manager to return our test manager
            with patch("wh.relay.config.get_relay_manager") as mock_get:
                mock_get.return_value = config_manager

                response = await daemon.handle_get_relays(request)

                # Response should be a web.json_response
                assert response.status == 200

    @pytest.mark.asyncio
    async def test_handle_get_relays_format(self):
        """Test the format of relay config response."""
        from wh.cli.daemon import WormholeDaemon
        from wh.relay.config import RelayConfigManager
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Set up test config
            config_manager = RelayConfigManager(config_dir=config_dir)
            config_manager.add_relay(
                name="relay1",
                mailbox_url="ws://relay1:4000/v1",
                transit_url="tcp:relay1:4001",
                set_default=True,
            )
            config_manager.add_relay(
                name="relay2",
                mailbox_url="ws://relay2:4000/v1",
                transit_url="tcp:relay2:4001",
            )

            daemon = WormholeDaemon()
            request = MagicMock()

            with patch("wh.relay.config.get_relay_manager") as mock_get:
                mock_get.return_value = config_manager

                response = await daemon.handle_get_relays(request)

                # Parse response body
                body = json.loads(response.body.decode("utf-8"))

                assert "relays" in body
                assert "default" in body
                assert len(body["relays"]) >= 2  # At least our 2 relays

                # Check relay format
                relay_names = [r["name"] for r in body["relays"]]
                assert "relay1" in relay_names
                assert "relay2" in relay_names

                # Find relay1 and check fields
                relay1 = next(r for r in body["relays"] if r["name"] == "relay1")
                assert relay1["mailboxUrl"] == "ws://relay1:4000/v1"
                assert relay1["transitUrl"] == "tcp:relay1:4001"
                assert relay1["isDefault"] is True

    @pytest.mark.asyncio
    async def test_handle_get_relays_error(self):
        """Test error handling in relay config endpoint."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()
        request = MagicMock()

        with patch("wh.relay.config.get_relay_manager") as mock_get:
            mock_get.side_effect = Exception("Config error")

            response = await daemon.handle_get_relays(request)

            assert response.status == 500


class TestDaemonHandlers:
    """Tests for daemon HTTP handlers."""

    @pytest.mark.asyncio
    async def test_handle_status(self):
        """Test status endpoint handler."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()
        request = MagicMock()

        response = await daemon.handle_status(request)

        assert response.status == 200

    @pytest.mark.asyncio
    async def test_handle_cors(self):
        """Test CORS handler."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()
        request = MagicMock()

        response = await daemon.handle_cors(request)

        assert response.status == 200


class TestDaemonConnections:
    """Tests for daemon connection management."""

    def test_connections_dict(self):
        """Test connections dictionary is initialized."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()

        assert daemon.connections == {}
        assert isinstance(daemon.connections, dict)

    def test_server_none_initially(self):
        """Test server is None initially."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()

        assert daemon.server is None


class TestAsyncCommand:
    """Tests for async_command decorator."""

    def test_async_command_exists(self):
        """Test async_command decorator exists."""
        from wh.cli.daemon import async_command

        assert callable(async_command)


class TestDaemonResolveHandler:
    """Tests for daemon resolve handler."""

    @pytest.mark.asyncio
    async def test_handle_resolve_exception(self):
        """Test resolve handles exceptions."""
        from wh.cli.daemon import WormholeDaemon
        from unittest.mock import AsyncMock

        daemon = WormholeDaemon()

        # Mock request that raises exception
        request = MagicMock()
        request.json = AsyncMock(side_effect=Exception("Parse error"))

        response = await daemon.handle_resolve(request)

        assert response.status == 500


class TestDaemonConnectHandler:
    """Tests for daemon connect handler."""

    @pytest.mark.asyncio
    async def test_handle_connect_exception(self):
        """Test connect handles exceptions."""
        from wh.cli.daemon import WormholeDaemon
        from unittest.mock import AsyncMock

        daemon = WormholeDaemon()

        request = MagicMock()
        request.json = AsyncMock(side_effect=Exception("Connection error"))

        response = await daemon.handle_connect(request)

        assert response.status == 500


class TestDaemonStatusResponse:
    """Tests for daemon status response format."""

    @pytest.mark.asyncio
    async def test_status_response_format(self):
        """Test status response has correct format."""
        from wh.cli.daemon import WormholeDaemon
        import json

        daemon = WormholeDaemon(port=9999)
        request = MagicMock()

        response = await daemon.handle_status(request)

        body = json.loads(response.body.decode("utf-8"))

        assert body["running"] is True
        assert body["port"] == 9999
        assert "version" in body
        assert "connections" in body


class TestDaemonListenerState:
    """Tests for ListenerState and ConnectionState dataclasses."""

    def test_listener_state_creation(self):
        """Test ListenerState can be created."""
        from wh.cli.daemon import ListenerState

        listener = ListenerState(
            id="test-id",
            code="7-guitar-sunset",
            manager=MagicMock(),
            protocol_name="wh-http",
        )

        assert listener.id == "test-id"
        assert listener.code == "7-guitar-sunset"
        assert listener.protocol_name == "wh-http"
        assert listener.closed is False
        assert listener.connections is not None

    def test_connection_state_creation(self):
        """Test ConnectionState can be created."""
        from wh.cli.daemon import ConnectionState

        conn = ConnectionState(
            id="conn-id",
            listener_id="listener-id",
            protocol=MagicMock(),
        )

        assert conn.id == "conn-id"
        assert conn.listener_id == "listener-id"
        assert conn.closed is False
        assert conn.read_queue is not None
        assert conn.write_queue is not None


class TestDaemonListenerTracking:
    """Tests for daemon listener/connection tracking."""

    def test_listeners_dict_initialized(self):
        """Test listeners dictionary is initialized."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()

        assert daemon.listeners == {}
        assert isinstance(daemon.listeners, dict)

    def test_active_connections_dict_initialized(self):
        """Test active_connections dictionary is initialized."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()

        assert daemon.active_connections == {}
        assert isinstance(daemon.active_connections, dict)


class TestDaemonListenHandler:
    """Tests for daemon /listen endpoint."""

    @pytest.mark.asyncio
    async def test_handle_listen_exception(self):
        """Test listen handles exceptions."""
        from wh.cli.daemon import WormholeDaemon
        from unittest.mock import AsyncMock

        daemon = WormholeDaemon()

        # Mock request that causes WormholeManager to fail
        request = MagicMock()
        request.body_exists = True
        request.json = AsyncMock(return_value={"protocol": "test"})

        # Patch the import path where WormholeManager is used
        with patch("wh.core.wormhole_manager.WormholeManager") as mock_manager:
            mock_manager.from_relay_config.side_effect = Exception("Manager error")

            response = await daemon.handle_listen(request)

            assert response.status == 500


class TestDaemonAcceptHandler:
    """Tests for daemon /accept endpoint."""

    @pytest.mark.asyncio
    async def test_handle_accept_listener_not_found(self):
        """Test accept returns 404 for unknown listener."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()

        request = MagicMock()
        request.match_info = {"listener_id": "nonexistent"}
        request.query = {"timeout": "1"}

        response = await daemon.handle_accept(request)

        assert response.status == 404

    @pytest.mark.asyncio
    async def test_handle_accept_listener_closed(self):
        """Test accept returns 410 for closed listener."""
        from wh.cli.daemon import WormholeDaemon, ListenerState

        daemon = WormholeDaemon()

        # Add a closed listener
        listener = ListenerState(
            id="closed-listener",
            code="test-code",
            manager=MagicMock(),
        )
        listener.closed = True
        daemon.listeners["closed-listener"] = listener

        request = MagicMock()
        request.match_info = {"listener_id": "closed-listener"}
        request.query = {"timeout": "1"}

        response = await daemon.handle_accept(request)

        assert response.status == 410


class TestDaemonSendRecvHandlers:
    """Tests for daemon /send and /recv endpoints."""

    @pytest.mark.asyncio
    async def test_handle_send_connection_not_found(self):
        """Test send returns 404 for unknown connection."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()

        request = MagicMock()
        request.match_info = {"conn_id": "nonexistent"}

        response = await daemon.handle_send(request)

        assert response.status == 404

    @pytest.mark.asyncio
    async def test_handle_recv_connection_not_found(self):
        """Test recv returns 404 for unknown connection."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()

        request = MagicMock()
        request.match_info = {"conn_id": "nonexistent"}
        request.query = {"timeout": "1", "max_bytes": "1024"}

        response = await daemon.handle_recv(request)

        assert response.status == 404

    @pytest.mark.asyncio
    async def test_handle_send_connection_closed(self):
        """Test send returns 410 for closed connection."""
        from wh.cli.daemon import WormholeDaemon, ConnectionState

        daemon = WormholeDaemon()

        # Add a closed connection
        conn = ConnectionState(
            id="closed-conn",
            listener_id="listener",
            protocol=MagicMock(),
        )
        conn.closed = True
        daemon.active_connections["closed-conn"] = conn

        request = MagicMock()
        request.match_info = {"conn_id": "closed-conn"}

        response = await daemon.handle_send(request)

        assert response.status == 410


class TestDaemonCloseHandlers:
    """Tests for daemon close endpoints."""

    @pytest.mark.asyncio
    async def test_handle_close_listener_not_found(self):
        """Test close listener returns 404 for unknown listener."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()

        request = MagicMock()
        request.match_info = {"listener_id": "nonexistent"}

        response = await daemon.handle_close_listener(request)

        assert response.status == 404

    @pytest.mark.asyncio
    async def test_handle_close_connection_not_found(self):
        """Test close connection returns 404 for unknown connection."""
        from wh.cli.daemon import WormholeDaemon

        daemon = WormholeDaemon()

        request = MagicMock()
        request.match_info = {"conn_id": "nonexistent"}

        response = await daemon.handle_close_connection(request)

        assert response.status == 404

    @pytest.mark.asyncio
    async def test_handle_close_connection_success(self):
        """Test close connection succeeds for valid connection."""
        from wh.cli.daemon import WormholeDaemon, ConnectionState

        daemon = WormholeDaemon()

        # Create a mock protocol with transport
        mock_transport = MagicMock()
        mock_protocol = MagicMock()
        mock_protocol.transport = mock_transport

        conn = ConnectionState(
            id="test-conn",
            listener_id="listener",
            protocol=mock_protocol,
        )
        daemon.active_connections["test-conn"] = conn

        request = MagicMock()
        request.match_info = {"conn_id": "test-conn"}

        response = await daemon.handle_close_connection(request)

        assert response.status == 200
        assert "test-conn" not in daemon.active_connections
        mock_transport.loseConnection.assert_called_once()
