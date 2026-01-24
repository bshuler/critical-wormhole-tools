"""Unit tests for DHT bootstrap functions."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch


class TestParseBootstrapNodesEnv:
    """Tests for parse_bootstrap_nodes_env function."""

    def test_parse_bootstrap_nodes_env_empty(self, monkeypatch):
        """Returns empty list when env not set."""
        from wh.wns.dht import parse_bootstrap_nodes_env

        # Ensure WH_DHT_BOOTSTRAP_NODES is not set
        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)

        nodes = parse_bootstrap_nodes_env()
        assert nodes == []

    def test_parse_bootstrap_nodes_env_single(self, monkeypatch):
        """Parses single 'host:port' correctly."""
        from wh.wns.dht import parse_bootstrap_nodes_env

        monkeypatch.setenv("WH_DHT_BOOTSTRAP_NODES", "example.com:6881")

        nodes = parse_bootstrap_nodes_env()
        assert nodes == [("example.com", 6881)]

    def test_parse_bootstrap_nodes_env_multiple(self, monkeypatch):
        """Parses comma-separated nodes."""
        from wh.wns.dht import parse_bootstrap_nodes_env

        monkeypatch.setenv(
            "WH_DHT_BOOTSTRAP_NODES",
            "node1.example.com:6881,node2.example.com:6882,node3.example.com:6883"
        )

        nodes = parse_bootstrap_nodes_env()
        assert nodes == [
            ("node1.example.com", 6881),
            ("node2.example.com", 6882),
            ("node3.example.com", 6883),
        ]

    def test_parse_bootstrap_nodes_env_invalid_format(self, monkeypatch):
        """Skips nodes without port (uses DEFAULT_DHT_PORT)."""
        from wh.wns.dht import parse_bootstrap_nodes_env, DEFAULT_DHT_PORT

        # Nodes without port should use default port
        monkeypatch.setenv("WH_DHT_BOOTSTRAP_NODES", "example.com")

        nodes = parse_bootstrap_nodes_env()
        assert nodes == [("example.com", DEFAULT_DHT_PORT)]

    def test_parse_bootstrap_nodes_env_invalid_port(self, monkeypatch, caplog):
        """Skips non-numeric ports gracefully."""
        from wh.wns.dht import parse_bootstrap_nodes_env

        monkeypatch.setenv("WH_DHT_BOOTSTRAP_NODES", "example.com:invalid")

        nodes = parse_bootstrap_nodes_env()
        assert nodes == []
        # Should log a warning
        assert "Invalid bootstrap node" in caplog.text

    def test_parse_bootstrap_nodes_env_mixed_valid_invalid(self, monkeypatch):
        """Parses valid nodes and skips invalid ones."""
        from wh.wns.dht import parse_bootstrap_nodes_env, DEFAULT_DHT_PORT

        monkeypatch.setenv(
            "WH_DHT_BOOTSTRAP_NODES",
            "node1.example.com:6881,node2.example.com:invalid,node3.example.com,node4.example.com:6882"
        )

        nodes = parse_bootstrap_nodes_env()
        assert nodes == [
            ("node1.example.com", 6881),
            ("node3.example.com", DEFAULT_DHT_PORT),
            ("node4.example.com", 6882),
        ]

    def test_parse_bootstrap_nodes_env_whitespace(self, monkeypatch):
        """Handles whitespace around entries."""
        from wh.wns.dht import parse_bootstrap_nodes_env

        monkeypatch.setenv(
            "WH_DHT_BOOTSTRAP_NODES",
            " node1.example.com:6881 , node2.example.com:6882 "
        )

        nodes = parse_bootstrap_nodes_env()
        assert nodes == [
            ("node1.example.com", 6881),
            ("node2.example.com", 6882),
        ]

    def test_parse_bootstrap_nodes_env_empty_parts(self, monkeypatch):
        """Skips empty parts in comma-separated list."""
        from wh.wns.dht import parse_bootstrap_nodes_env

        monkeypatch.setenv(
            "WH_DHT_BOOTSTRAP_NODES",
            "node1.example.com:6881,,node2.example.com:6882"
        )

        nodes = parse_bootstrap_nodes_env()
        assert nodes == [
            ("node1.example.com", 6881),
            ("node2.example.com", 6882),
        ]


class TestUsePublicBootstrapEnv:
    """Tests for use_public_bootstrap_env function."""

    def test_use_public_bootstrap_env_true(self, monkeypatch):
        """Returns True for 'true'."""
        from wh.wns.dht import use_public_bootstrap_env

        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "true")
        assert use_public_bootstrap_env() is True

    def test_use_public_bootstrap_env_false(self, monkeypatch):
        """Returns False for 'false', '0', 'no'."""
        from wh.wns.dht import use_public_bootstrap_env

        # Test "false"
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "false")
        assert use_public_bootstrap_env() is False

        # Test "0"
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "0")
        assert use_public_bootstrap_env() is False

        # Test "no"
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "no")
        assert use_public_bootstrap_env() is False

    def test_use_public_bootstrap_env_unset(self, monkeypatch):
        """Returns True (default) when not set."""
        from wh.wns.dht import use_public_bootstrap_env

        monkeypatch.delenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", raising=False)
        assert use_public_bootstrap_env() is True

    def test_use_public_bootstrap_env_case_insensitive(self, monkeypatch):
        """TRUE, True, 1, yes all work (case-insensitive)."""
        from wh.wns.dht import use_public_bootstrap_env

        # Test "TRUE" (uppercase)
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "TRUE")
        assert use_public_bootstrap_env() is True

        # Test "True" (mixed case)
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "True")
        assert use_public_bootstrap_env() is True

        # Test "1"
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "1")
        assert use_public_bootstrap_env() is True

        # Test "yes"
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "yes")
        assert use_public_bootstrap_env() is True

        # Test "YES" (uppercase)
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "YES")
        assert use_public_bootstrap_env() is True

    def test_use_public_bootstrap_env_false_case_insensitive(self, monkeypatch):
        """FALSE, False, NO work (case-insensitive)."""
        from wh.wns.dht import use_public_bootstrap_env

        # Test "FALSE" (uppercase)
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "FALSE")
        assert use_public_bootstrap_env() is False

        # Test "False" (mixed case)
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "False")
        assert use_public_bootstrap_env() is False

        # Test "NO" (uppercase)
        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "NO")
        assert use_public_bootstrap_env() is False


class TestFetchBootstrapNodes:
    """Tests for fetch_bootstrap_nodes async function."""

    @pytest.mark.asyncio
    async def test_fetch_bootstrap_nodes_success(self):
        """Returns nodes from JSON response."""
        from wh.wns.dht import fetch_bootstrap_nodes

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "nodes": [
                {"host": "node1.example.com", "port": 6881},
                {"host": "node2.example.com", "port": 6882},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            nodes = await fetch_bootstrap_nodes(urls=["http://example.com/nodes.json"])

        assert nodes == [
            ("node1.example.com", 6881),
            ("node2.example.com", 6882),
        ]

    @pytest.mark.asyncio
    async def test_fetch_bootstrap_nodes_timeout(self):
        """Returns empty on timeout."""
        from wh.wns.dht import fetch_bootstrap_nodes

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            nodes = await fetch_bootstrap_nodes(urls=["http://example.com/nodes.json"], timeout=1.0)

        assert nodes == []

    @pytest.mark.asyncio
    async def test_fetch_bootstrap_nodes_invalid_json(self):
        """Returns empty on bad JSON."""
        from wh.wns.dht import fetch_bootstrap_nodes

        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            nodes = await fetch_bootstrap_nodes(urls=["http://example.com/nodes.json"])

        assert nodes == []

    @pytest.mark.asyncio
    async def test_fetch_bootstrap_nodes_empty_response(self):
        """Returns empty for empty array."""
        from wh.wns.dht import fetch_bootstrap_nodes

        mock_response = MagicMock()
        mock_response.json.return_value = {"nodes": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            nodes = await fetch_bootstrap_nodes(urls=["http://example.com/nodes.json"])

        assert nodes == []

    @pytest.mark.asyncio
    async def test_fetch_bootstrap_nodes_no_urls(self):
        """Returns empty when no URLs provided."""
        from wh.wns.dht import fetch_bootstrap_nodes

        nodes = await fetch_bootstrap_nodes(urls=[])
        assert nodes == []

        nodes = await fetch_bootstrap_nodes(urls=None)
        assert nodes == []

    @pytest.mark.asyncio
    async def test_fetch_bootstrap_nodes_http_error(self):
        """Returns empty on HTTP error."""
        from wh.wns.dht import fetch_bootstrap_nodes

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            nodes = await fetch_bootstrap_nodes(urls=["http://example.com/nodes.json"])

        assert nodes == []

    @pytest.mark.asyncio
    async def test_fetch_bootstrap_nodes_default_port(self):
        """Uses DEFAULT_DHT_PORT when port not specified."""
        from wh.wns.dht import fetch_bootstrap_nodes, DEFAULT_DHT_PORT

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "nodes": [
                {"host": "node1.example.com"},  # No port
                {"host": "node2.example.com", "port": 7000},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            nodes = await fetch_bootstrap_nodes(urls=["http://example.com/nodes.json"])

        assert nodes == [
            ("node1.example.com", DEFAULT_DHT_PORT),
            ("node2.example.com", 7000),
        ]

    @pytest.mark.asyncio
    async def test_fetch_bootstrap_nodes_multiple_urls_fallback(self):
        """Tries multiple URLs and returns first successful."""
        from wh.wns.dht import fetch_bootstrap_nodes

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {
            "nodes": [{"host": "node1.example.com", "port": 6881}]
        }
        mock_response_success.raise_for_status = MagicMock()

        call_count = 0

        async def mock_get(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First URL fails
                raise httpx.TimeoutException("Timeout")
            else:
                # Second URL succeeds
                return mock_response_success

        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            nodes = await fetch_bootstrap_nodes(
                urls=["http://bad.example.com/nodes.json", "http://good.example.com/nodes.json"]
            )

        assert nodes == [("node1.example.com", 6881)]


class TestGetAllBootstrapNodes:
    """Tests for get_all_bootstrap_nodes function."""

    def test_get_bootstrap_nodes_env_priority(self, monkeypatch):
        """Env nodes come before others."""
        from wh.wns.dht import get_all_bootstrap_nodes

        monkeypatch.setenv("WH_DHT_BOOTSTRAP_NODES", "env-node.example.com:6881")

        custom_nodes = [("custom-node.example.com", 6882)]

        nodes = get_all_bootstrap_nodes(custom_nodes=custom_nodes, use_public=False)

        # Env nodes should come first
        assert nodes[0] == ("env-node.example.com", 6881)
        assert ("custom-node.example.com", 6882) in nodes

    def test_get_bootstrap_nodes_deduplication(self, monkeypatch):
        """No duplicate nodes."""
        from wh.wns.dht import get_all_bootstrap_nodes

        # Set env to have duplicate with custom nodes
        monkeypatch.setenv("WH_DHT_BOOTSTRAP_NODES", "node1.example.com:6881,node2.example.com:6882")

        custom_nodes = [
            ("node2.example.com", 6882),  # Duplicate with env
            ("node3.example.com", 6883),
        ]

        nodes = get_all_bootstrap_nodes(custom_nodes=custom_nodes, use_public=False)

        # Should have no duplicates
        assert len(nodes) == len(set(nodes))
        assert ("node1.example.com", 6881) in nodes
        assert ("node2.example.com", 6882) in nodes
        assert ("node3.example.com", 6883) in nodes
        # Should only have node2 once
        assert nodes.count(("node2.example.com", 6882)) == 1

    def test_get_bootstrap_nodes_public_included(self, monkeypatch):
        """Public nodes included when use_public=True."""
        from wh.wns.dht import get_all_bootstrap_nodes, PUBLIC_BOOTSTRAP_NODES

        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)
        monkeypatch.delenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", raising=False)

        nodes = get_all_bootstrap_nodes(use_public=True)

        # Should include all public nodes
        for public_node in PUBLIC_BOOTSTRAP_NODES:
            assert public_node in nodes

    def test_get_bootstrap_nodes_public_excluded(self, monkeypatch):
        """Public nodes excluded when use_public=False."""
        from wh.wns.dht import get_all_bootstrap_nodes, PUBLIC_BOOTSTRAP_NODES

        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)

        nodes = get_all_bootstrap_nodes(use_public=False)

        # Should not include any public nodes
        for public_node in PUBLIC_BOOTSTRAP_NODES:
            assert public_node not in nodes

    def test_get_bootstrap_nodes_env_disables_public(self, monkeypatch):
        """WH_DHT_USE_PUBLIC_BOOTSTRAP=false disables public nodes."""
        from wh.wns.dht import get_all_bootstrap_nodes, PUBLIC_BOOTSTRAP_NODES

        monkeypatch.setenv("WH_DHT_USE_PUBLIC_BOOTSTRAP", "false")
        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)

        nodes = get_all_bootstrap_nodes(use_public=True)

        # Even though use_public=True, env var should override
        for public_node in PUBLIC_BOOTSTRAP_NODES:
            assert public_node not in nodes

    def test_get_bootstrap_nodes_empty(self, monkeypatch):
        """Returns empty list when no nodes available."""
        from wh.wns.dht import get_all_bootstrap_nodes

        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)

        nodes = get_all_bootstrap_nodes(custom_nodes=None, use_public=False)
        assert nodes == []

    def test_get_bootstrap_nodes_custom_only(self, monkeypatch):
        """Returns only custom nodes when provided."""
        from wh.wns.dht import get_all_bootstrap_nodes

        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)

        custom_nodes = [
            ("custom1.example.com", 6881),
            ("custom2.example.com", 6882),
        ]

        nodes = get_all_bootstrap_nodes(custom_nodes=custom_nodes, use_public=False)

        assert nodes == custom_nodes

    def test_get_bootstrap_nodes_deduplication_with_public(self, monkeypatch):
        """Deduplicates custom nodes that match public nodes."""
        from wh.wns.dht import get_all_bootstrap_nodes, PUBLIC_BOOTSTRAP_NODES

        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)

        # Include a duplicate of a public node
        custom_nodes = [
            PUBLIC_BOOTSTRAP_NODES[0],  # Duplicate
            ("custom.example.com", 6881),
        ]

        nodes = get_all_bootstrap_nodes(custom_nodes=custom_nodes, use_public=True)

        # Should not have duplicates
        assert len(nodes) == len(set(nodes))
        # Public node should appear only once
        assert nodes.count(PUBLIC_BOOTSTRAP_NODES[0]) == 1


class TestGetBootstrapNodes:
    """Tests for get_bootstrap_nodes async function."""

    @pytest.mark.asyncio
    async def test_get_bootstrap_nodes_combines_all_sources(self, monkeypatch):
        """Combines static, env, HTTP, mDNS, and public nodes."""
        from wh.wns.dht import get_bootstrap_nodes

        monkeypatch.setenv("WH_DHT_BOOTSTRAP_NODES", "env-node.example.com:6881")

        static_nodes = [("static-node.example.com", 6882)]

        # Mock HTTP fetch
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "nodes": [{"host": "http-node.example.com", "port": 6883}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Mock mDNS discovery
        async def mock_discover_local_nodes(timeout=2.0):
            return [("mdns-node.local", 6884)]

        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("wh.wns.dht.discover_local_nodes", mock_discover_local_nodes):
                nodes = await get_bootstrap_nodes(
                    static_nodes=static_nodes,
                    bootstrap_urls=["http://example.com/nodes.json"],
                    use_mdns=True,
                    use_public=True,
                )

        # Check all sources are included
        assert ("env-node.example.com", 6881) in nodes
        assert ("static-node.example.com", 6882) in nodes
        assert ("http-node.example.com", 6883) in nodes
        assert ("mdns-node.local", 6884) in nodes
        # Public nodes should be included too
        from wh.wns.dht import PUBLIC_BOOTSTRAP_NODES
        assert PUBLIC_BOOTSTRAP_NODES[0] in nodes

    @pytest.mark.asyncio
    async def test_get_bootstrap_nodes_deduplication_across_sources(self, monkeypatch):
        """Deduplicates nodes from all sources."""
        from wh.wns.dht import get_bootstrap_nodes

        duplicate_node = ("duplicate.example.com", 6881)

        monkeypatch.setenv("WH_DHT_BOOTSTRAP_NODES", f"{duplicate_node[0]}:{duplicate_node[1]}")

        static_nodes = [duplicate_node]  # Same node

        # Mock HTTP fetch returning same node
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "nodes": [{"host": duplicate_node[0], "port": duplicate_node[1]}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            nodes = await get_bootstrap_nodes(
                static_nodes=static_nodes,
                bootstrap_urls=["http://example.com/nodes.json"],
                use_mdns=False,
                use_public=False,
            )

        # Should only have the node once
        assert nodes.count(duplicate_node) == 1
        assert len(nodes) == 1

    @pytest.mark.asyncio
    async def test_get_bootstrap_nodes_mdns_disabled(self, monkeypatch):
        """Skips mDNS when use_mdns=False."""
        from wh.wns.dht import get_bootstrap_nodes

        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)

        static_nodes = [("static-node.example.com", 6881)]

        # Mock mDNS discovery - should not be called
        async def mock_discover_local_nodes(timeout=2.0):
            raise AssertionError("mDNS should not be called")

        with patch("wh.wns.dht.discover_local_nodes", mock_discover_local_nodes):
            nodes = await get_bootstrap_nodes(
                static_nodes=static_nodes,
                bootstrap_urls=None,
                use_mdns=False,
                use_public=False,
            )

        assert nodes == static_nodes

    @pytest.mark.asyncio
    async def test_get_bootstrap_nodes_http_failure_doesnt_break(self, monkeypatch):
        """HTTP failure doesn't break node collection."""
        from wh.wns.dht import get_bootstrap_nodes

        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)

        static_nodes = [("static-node.example.com", 6881)]

        # Mock HTTP failure
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("HTTP failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            nodes = await get_bootstrap_nodes(
                static_nodes=static_nodes,
                bootstrap_urls=["http://example.com/nodes.json"],
                use_mdns=False,
                use_public=False,
            )

        # Should still have static nodes
        assert nodes == static_nodes

    @pytest.mark.asyncio
    async def test_get_bootstrap_nodes_mdns_failure_doesnt_break(self, monkeypatch):
        """mDNS failure doesn't break node collection."""
        from wh.wns.dht import get_bootstrap_nodes

        monkeypatch.delenv("WH_DHT_BOOTSTRAP_NODES", raising=False)

        static_nodes = [("static-node.example.com", 6881)]

        # Mock mDNS failure
        async def mock_discover_local_nodes(timeout=2.0):
            raise Exception("mDNS failed")

        with patch("wh.wns.dht.discover_local_nodes", mock_discover_local_nodes):
            nodes = await get_bootstrap_nodes(
                static_nodes=static_nodes,
                bootstrap_urls=None,
                use_mdns=True,
                use_public=False,
            )

        # Should still have static nodes
        assert nodes == static_nodes
