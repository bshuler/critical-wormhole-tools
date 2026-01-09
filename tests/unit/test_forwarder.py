"""Unit tests for PortForwarder."""

from unittest.mock import MagicMock, AsyncMock, patch


class TestPortForwarder:
    """Tests for PortForwarder class."""

    def test_init(self):
        """Test PortForwarder initialization."""
        from wh.core.forwarder import PortForwarder

        manager = MagicMock()
        forwarder = PortForwarder(manager, local_port=8080)

        assert forwarder.manager is manager
        assert forwarder.local_port == 8080
        assert forwarder.local_host == "127.0.0.1"

    def test_init_custom_host(self):
        """Test PortForwarder with custom host."""
        from wh.core.forwarder import PortForwarder

        manager = MagicMock()
        forwarder = PortForwarder(
            manager,
            local_port=3000,
            local_host="0.0.0.0",
        )

        assert forwarder.local_port == 3000
        assert forwarder.local_host == "0.0.0.0"

    def test_attributes(self):
        """Test forwarder stores manager reference."""
        from wh.core.forwarder import PortForwarder

        manager = MagicMock()
        manager.is_dilated = True

        forwarder = PortForwarder(manager, local_port=9999)

        assert forwarder.manager.is_dilated is True


class TestPortForwarderProperties:
    """Additional tests for PortForwarder properties."""

    def test_local_host_localhost(self):
        """Test default local_host is localhost."""
        from wh.core.forwarder import PortForwarder

        manager = MagicMock()
        forwarder = PortForwarder(manager, local_port=80)

        assert forwarder.local_host == "127.0.0.1"

    def test_local_port_stored(self):
        """Test local_port is stored correctly."""
        from wh.core.forwarder import PortForwarder

        manager = MagicMock()
        forwarder = PortForwarder(manager, local_port=443)

        assert forwarder.local_port == 443

    def test_manager_reference(self):
        """Test manager reference is stored."""
        from wh.core.forwarder import PortForwarder

        manager = MagicMock()
        manager.wormhole_code = "7-test"

        forwarder = PortForwarder(manager, local_port=22)

        assert forwarder.manager.wormhole_code == "7-test"

    def test_ipv6_host(self):
        """Test with IPv6 host."""
        from wh.core.forwarder import PortForwarder

        manager = MagicMock()
        forwarder = PortForwarder(
            manager,
            local_port=8080,
            local_host="::1",
        )

        assert forwarder.local_host == "::1"

    def test_all_interfaces(self):
        """Test binding to all interfaces."""
        from wh.core.forwarder import PortForwarder

        manager = MagicMock()
        forwarder = PortForwarder(
            manager,
            local_port=5000,
            local_host="0.0.0.0",
        )

        assert forwarder.local_host == "0.0.0.0"
        assert forwarder.local_port == 5000
