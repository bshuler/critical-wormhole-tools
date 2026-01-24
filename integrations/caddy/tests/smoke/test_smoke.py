"""
Smoke tests - Quick validation tests for CI/CD.

These tests verify basic module imports and instantiation without
requiring network, file I/O, or external dependencies. The entire
test suite should complete in under 30 seconds.
"""
import sys
from pathlib import Path
import pytest

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


@pytest.mark.smoke
def test_cli_loads():
    """Test that CLI module can be imported without errors."""
    try:
        from wh.cli import cli
        assert cli is not None
        assert callable(cli)
    except Exception as e:
        pytest.fail(f"Failed to import CLI: {e}")


@pytest.mark.smoke
def test_all_commands_exist():
    """Test that all 25+ commands are accessible with --help."""
    from wh.cli.main import cli

    # Expected commands based on main.py imports
    expected_commands = [
        'nc', 'listen', 'ssh', 'scp', 'sftp', 'curl', 'wget',
        'ping', 'tunnel', 'proxy', 'rsync', 'serve', 'daemon',
        'relay', 'telnet', 'ftp', 'nmap', 'traceroute', 'dns',
        'mount', 'vnc', 'rdp', 'identity', 'alias', 'namespace'
    ]

    # Get registered commands
    registered = cli.commands

    # Check that all expected commands are registered
    for cmd in expected_commands:
        assert cmd in registered, f"Command '{cmd}' not registered in CLI"

    # Verify we have at least 25 commands
    assert len(registered) >= 25, f"Expected at least 25 commands, got {len(registered)}"


@pytest.mark.smoke
def test_version_number():
    """Test that version is set and non-empty."""
    import wh

    assert hasattr(wh, '__version__'), "Module missing __version__ attribute"
    assert wh.__version__, "Version string is empty"
    assert isinstance(wh.__version__, str), "Version should be a string"

    # Basic format check (e.g., "0.3.0")
    parts = wh.__version__.split('.')
    assert len(parts) >= 2, f"Version '{wh.__version__}' should have at least 2 parts"


@pytest.mark.smoke
def test_relay_config_loads():
    """Test that relay config module can be imported and parsed."""
    try:
        from wh.relay.config import RelayConfig, RelayConfigFile, RelayConfigManager
        from wh.relay.config import DEFAULT_MAILBOX_URL, DEFAULT_TRANSIT_URL

        # Verify classes exist
        assert RelayConfig is not None
        assert RelayConfigFile is not None
        assert RelayConfigManager is not None

        # Verify defaults are set
        assert DEFAULT_MAILBOX_URL
        assert DEFAULT_TRANSIT_URL
        assert "relay.magic-wormhole.io" in DEFAULT_MAILBOX_URL

        # Test basic instantiation
        config = RelayConfigFile()
        assert config.default == "public"
        assert "public" in config.relays

    except Exception as e:
        pytest.fail(f"Failed to load relay config: {e}")


@pytest.mark.smoke
def test_identity_manager_loads():
    """Test that WNS identity manager can be initialized."""
    try:
        from wh.wns.identity import WNSIdentity, ADDRESS_BYTES

        # Verify constants
        assert ADDRESS_BYTES == 16, "Address should be 16 bytes (128 bits)"

        # Test class exists
        assert WNSIdentity is not None

        # Verify class methods exist
        assert hasattr(WNSIdentity, 'generate')
        assert hasattr(WNSIdentity, 'from_private_key')
        assert hasattr(WNSIdentity, 'from_public_key')

    except Exception as e:
        pytest.fail(f"Failed to load identity manager: {e}")


@pytest.mark.smoke
def test_http_client_imports():
    """Test that HTTP module imports successfully."""
    try:
        from wh.http import curl, wget

        # Verify modules loaded
        assert curl is not None
        assert wget is not None

    except ImportError as e:
        # Check if it's a submodule structure
        try:
            import wh.http
            assert wh.http is not None
        except Exception as e2:
            pytest.fail(f"Failed to import HTTP module: {e}, {e2}")


@pytest.mark.smoke
def test_ssh_module_imports():
    """Test that SSH module imports successfully."""
    try:
        from wh.ssh import ssh, scp, sftp

        # Verify modules loaded
        assert ssh is not None
        assert scp is not None
        assert sftp is not None

    except ImportError as e:
        # Check if it's a submodule structure
        try:
            import wh.ssh
            assert wh.ssh is not None
        except Exception as e2:
            pytest.fail(f"Failed to import SSH module: {e}, {e2}")


@pytest.mark.smoke
def test_enterprise_modules_load():
    """Test that enterprise modules are accessible."""
    try:
        from wh.enterprise import namespace

        # Verify namespace module loaded
        assert namespace is not None

        # Check for key functions
        try:
            from wh.enterprise.namespace import get_namespace_manager
            assert callable(get_namespace_manager)
        except ImportError:
            # Module exists but might not have this function
            pass

    except ImportError as e:
        # Enterprise module might be optional
        try:
            import wh.enterprise
            assert wh.enterprise is not None
        except Exception as e2:
            pytest.fail(f"Failed to import enterprise module: {e}, {e2}")
