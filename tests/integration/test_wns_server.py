"""Integration tests for WNS server module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import pytest


class TestServiceType:
    """Tests for ServiceType enum."""

    def test_service_types_exist(self):
        """Test all service types exist."""
        from wh.wns.server import ServiceType

        assert ServiceType.SSH.value == "ssh"
        assert ServiceType.HTTP.value == "http"
        assert ServiceType.NC.value == "nc"
        assert ServiceType.PORT.value == "port"

    def test_service_type_from_string(self):
        """Test creating ServiceType from string."""
        from wh.wns.server import ServiceType

        assert ServiceType("ssh") == ServiceType.SSH
        assert ServiceType("http") == ServiceType.HTTP
        assert ServiceType("nc") == ServiceType.NC
        assert ServiceType("port") == ServiceType.PORT


class TestWNSServer:
    """Tests for WNSServer class."""

    @pytest.fixture
    def mock_identity(self):
        """Create a mock identity."""
        identity = MagicMock()
        identity.can_sign = True
        identity.address = "abcdefghijklmnopqrstuvwxyz"
        identity.full_address = "wh://abcdefghijklmnopqrstuvwxyz.wns"
        return identity

    def test_init_default(self, mock_identity):
        """Test default initialization."""
        from wh.wns.server import WNSServer, ServiceType

        server = WNSServer(mock_identity)

        assert server.identity is mock_identity
        assert server.service_type == ServiceType.SSH
        assert server.port is None
        assert server.relay_url is None
        assert server.transit_relay is None
        assert server._running is False
        assert server._current_code is None
        assert server._connection_count == 0
        assert server.advertise_to_file is True

    def test_init_with_options(self, mock_identity):
        """Test initialization with options."""
        from wh.wns.server import WNSServer, ServiceType

        on_status = MagicMock()

        server = WNSServer(
            mock_identity,
            service_type=ServiceType.HTTP,
            port=8080,
            relay_url="ws://custom:4000/v1",
            transit_relay="tcp:custom:4001",
            on_status=on_status,
            advertise_to_file=False,
        )

        assert server.service_type == ServiceType.HTTP
        assert server.port == 8080
        assert server.relay_url == "ws://custom:4000/v1"
        assert server.transit_relay == "tcp:custom:4001"
        assert server.on_status is on_status
        assert server.advertise_to_file is False

    def test_init_requires_signing_identity(self):
        """Test init raises error without signing capability."""
        from wh.wns.server import WNSServer

        identity = MagicMock()
        identity.can_sign = False

        with pytest.raises(ValueError, match="must have private key"):
            WNSServer(identity)

    def test_is_running_property(self, mock_identity):
        """Test is_running property."""
        from wh.wns.server import WNSServer

        server = WNSServer(mock_identity)

        assert server.is_running is False

        server._running = True
        assert server.is_running is True

    def test_current_code_property(self, mock_identity):
        """Test current_code property."""
        from wh.wns.server import WNSServer

        server = WNSServer(mock_identity)

        assert server.current_code is None

        server._current_code = "7-guitar-sunset"
        assert server.current_code == "7-guitar-sunset"

    def test_address_property(self, mock_identity):
        """Test address property."""
        from wh.wns.server import WNSServer

        server = WNSServer(mock_identity)

        assert server.address == "wh://abcdefghijklmnopqrstuvwxyz.wns"

    def test_shutdown(self, mock_identity):
        """Test shutdown method sets event."""
        from wh.wns.server import WNSServer

        server = WNSServer(mock_identity)

        assert not server._shutdown_event.is_set()

        server.shutdown()

        assert server._shutdown_event.is_set()

    def test_status_callback(self, mock_identity):
        """Test status callback is called."""
        from wh.wns.server import WNSServer

        statuses = []
        def on_status(msg):
            return statuses.append(msg)

        server = WNSServer(mock_identity, on_status=on_status)
        server._status("test message")

        assert "test message" in statuses

    def test_status_no_callback(self, mock_identity):
        """Test status works without callback."""
        from wh.wns.server import WNSServer

        server = WNSServer(mock_identity)
        server._status("test message")  # Should not raise


class TestWNSServerAsync:
    """Async tests for WNSServer."""

    @pytest.fixture
    def mock_identity(self):
        """Create a mock identity."""
        identity = MagicMock()
        identity.can_sign = True
        identity.address = "abcdefghijklmnopqrstuvwxyz"
        identity.full_address = "wh://abcdefghijklmnopqrstuvwxyz.wns"
        return identity

    @pytest.mark.asyncio
    async def test_publish_advertisement_to_file(self, mock_identity):
        """Test publishing advertisement to file."""
        from wh.wns.server import WNSServer

        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch home directory
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                server = WNSServer(mock_identity, advertise_to_file=True)

                # Mock the advertisement
                with patch("wh.wns.server.CodeAdvertisement") as MockAd:
                    mock_ad = MagicMock()
                    mock_ad.to_json.return_value = '{"code": "7-test"}'
                    MockAd.create.return_value = mock_ad

                    await server._publish_advertisement("7-test-code")

                    # Check file was created
                    ad_file = Path(tmpdir) / ".wh" / "advertise" / f"{mock_identity.address}.json"
                    assert ad_file.exists()

    @pytest.mark.asyncio
    async def test_publish_advertisement_dht_failure(self, mock_identity):
        """Test publish handles DHT failure gracefully."""
        from wh.wns.server import WNSServer

        server = WNSServer(mock_identity, advertise_to_file=False)

        # Mock a failing DHT node
        server._dht_node = MagicMock()
        server._dht_node.is_running = True
        server._dht_node.publish = AsyncMock(side_effect=Exception("DHT error"))

        # Should not raise
        with patch("wh.wns.server.CodeAdvertisement"):
            await server._publish_advertisement("7-test")


class TestRunWNSServer:
    """Tests for run_wns_server function."""

    def test_function_exists(self):
        """Test run_wns_server function exists."""
        from wh.wns.server import run_wns_server

        assert callable(run_wns_server)

    @pytest.mark.asyncio
    async def test_run_wns_server_no_identity(self):
        """Test run_wns_server raises without identity."""
        from wh.wns.server import run_wns_server

        with patch("wh.wns.server.WNSIdentityStore") as MockStore:
            mock_store = MagicMock()
            mock_store.load_identity.return_value = None
            MockStore.return_value = mock_store

            with pytest.raises(ValueError, match="Identity not found"):
                await run_wns_server(identity_address="nonexistent")

    @pytest.mark.asyncio
    async def test_run_wns_server_no_default_identity(self):
        """Test run_wns_server raises without default identity."""
        from wh.wns.server import run_wns_server

        with patch("wh.wns.server.WNSIdentityStore") as MockStore:
            mock_store = MagicMock()
            mock_store.get_default_identity.return_value = None
            MockStore.return_value = mock_store

            with pytest.raises(ValueError, match="No identity found"):
                await run_wns_server()


class TestWNSServerServiceTypes:
    """Tests for different service type handling."""

    @pytest.fixture
    def mock_identity(self):
        """Create a mock identity."""
        identity = MagicMock()
        identity.can_sign = True
        identity.address = "abcdefghijklmnopqrstuvwxyz"
        identity.full_address = "wh://abcdefghijklmnopqrstuvwxyz.wns"
        return identity

    def test_port_service_requires_port(self, mock_identity):
        """Test PORT service type requires port."""
        from wh.wns.server import WNSServer, ServiceType

        server = WNSServer(
            mock_identity,
            service_type=ServiceType.PORT,
            port=None,
        )

        # Port is required for PORT service type
        assert server.service_type == ServiceType.PORT
        assert server.port is None  # Will fail at runtime

    def test_all_service_types(self, mock_identity):
        """Test all service types can be set."""
        from wh.wns.server import WNSServer, ServiceType

        for svc_type in ServiceType:
            server = WNSServer(
                mock_identity,
                service_type=svc_type,
                port=8080 if svc_type == ServiceType.PORT else None,
            )
            assert server.service_type == svc_type


class TestDHTConfig:
    """Tests for DHTConfig usage in WNSServer."""

    @pytest.fixture
    def mock_identity(self):
        """Create a mock identity."""
        identity = MagicMock()
        identity.can_sign = True
        identity.address = "abcdefghijklmnopqrstuvwxyz"
        identity.full_address = "wh://abcdefghijklmnopqrstuvwxyz.wns"
        return identity

    def test_default_dht_config(self, mock_identity):
        """Test default DHT config is used."""
        from wh.wns.server import WNSServer
        from wh.wns.dht import DHTConfig

        server = WNSServer(mock_identity)

        assert isinstance(server.dht_config, DHTConfig)

    def test_custom_dht_config(self, mock_identity):
        """Test custom DHT config is used."""
        from wh.wns.server import WNSServer
        from wh.wns.dht import DHTConfig

        custom_config = DHTConfig(port=9999, ttl_seconds=600)
        server = WNSServer(mock_identity, dht_config=custom_config)

        assert server.dht_config is custom_config
        assert server.dht_config.port == 9999
        assert server.dht_config.ttl_seconds == 600
