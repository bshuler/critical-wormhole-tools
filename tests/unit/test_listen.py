"""Unit tests for wh listen command."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
from click.testing import CliRunner
import asyncio
import tempfile
from pathlib import Path
import click


class TestListenCommandHelp:
    """Test wh listen command help and documentation."""

    def test_listen_command_help(self):
        """Test that listen command help shows all modes and options."""
        from wh.cli.listen import listen

        runner = CliRunner()
        result = runner.invoke(listen, ["--help"])

        assert result.exit_code == 0
        # Check for basic modes
        assert "-p" in result.output or "--port" in result.output
        assert "--ssh" in result.output
        assert "--http" in result.output
        assert "--serve" in result.output
        # Check for enterprise features
        assert "--auth-method" in result.output
        assert "--authorized-keys" in result.output
        assert "--ldap-server" in result.output
        assert "--audit-log" in result.output
        # Check for dilation option
        assert "--dilate" in result.output or "--no-dilate" in result.output
        # Check for code option
        assert "--code" in result.output


class TestListenPortForwardMode:
    """Test listen command with port forwarding mode."""

    @pytest.mark.asyncio
    async def test_listen_port_forward_mode(self):
        """Test -p flag initializes port forward."""
        # Import and unwrap the listen function to get to the actual async function
        from wh.cli.listen import listen

        # Access the actual async function through __wrapped__ (twice: pass_context + async_command)
        # Unwrap: callback.__wrapped__ (from functools.wraps in async_command) -> __wrapped__ (from @pass_context)
        listen_callback = listen.callback.__wrapped__.__wrapped__

        # Create mock context
        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        # Mock WormholeManager
        with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
             patch("wh.core.forwarder.PortForwarder") as mock_forwarder_class:

            mock_manager = AsyncMock()
            mock_manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
            mock_manager.dilate = AsyncMock()
            mock_manager.close = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_forwarder = AsyncMock()
            mock_forwarder.run = AsyncMock(side_effect=KeyboardInterrupt())
            mock_forwarder_class.return_value = mock_forwarder

            # Call the async function directly
            try:
                await listen_callback(
                    ctx=mock_ctx,
                    port=8080,
                    ssh=False,
                    http=False,
                    serve=None,
                    dilate=True,
                    code=None,
                    auth_method='none',
                    authorized_keys=None,
                    ldap_server=None,
                    ldap_base_dn=None,
                    audit_log=None,
                )
            except KeyboardInterrupt:
                pass

            # Should have created WormholeManager
            mock_manager_class.assert_called_once()
            # Should have created code
            mock_manager.create_and_allocate_code.assert_called_once()
            # Should call dilate
            mock_manager.dilate.assert_called_once()
            # Should have created PortForwarder with port 8080
            mock_forwarder_class.assert_called_once()
            call_args = mock_forwarder_class.call_args
            assert call_args[1]["local_port"] == 8080


class TestListenSSHMode:
    """Test listen command with SSH server mode."""

    @pytest.mark.asyncio
    async def test_listen_ssh_mode(self):
        """Test --ssh flag uses SSH server handler."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
             patch("wh.ssh.server.SSHServerHandler") as mock_handler_class:

            mock_manager = AsyncMock()
            mock_manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
            mock_manager.dilate = AsyncMock()
            mock_manager.close = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_handler = AsyncMock()
            mock_handler.run = AsyncMock(side_effect=KeyboardInterrupt())
            mock_handler_class.return_value = mock_handler

            try:
                await listen_callback(
                    ctx=mock_ctx,
                    port=None,
                    ssh=True,
                    http=False,
                    serve=None,
                    dilate=True,
                    code=None,
                    auth_method='none',
                    authorized_keys=None,
                    ldap_server=None,
                    ldap_base_dn=None,
                    audit_log=None,
                )
            except KeyboardInterrupt:
                pass

            # Should have created SSHServerHandler
            mock_handler_class.assert_called_once()
            # Should call dilate before running handler
            mock_manager.dilate.assert_called_once()


class TestListenHTTPMode:
    """Test listen command with HTTP proxy mode."""

    @pytest.mark.asyncio
    async def test_listen_http_mode(self):
        """Test --http flag uses HTTP proxy handler."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
             patch("wh.http.client.HTTPProxyHandler") as mock_handler_class:

            mock_manager = AsyncMock()
            mock_manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
            mock_manager.dilate = AsyncMock()
            mock_manager.close = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_handler = AsyncMock()
            mock_handler.run = AsyncMock(side_effect=KeyboardInterrupt())
            mock_handler_class.return_value = mock_handler

            try:
                await listen_callback(
                    ctx=mock_ctx,
                    port=None,
                    ssh=False,
                    http=True,
                    serve=None,
                    dilate=True,
                    code=None,
                    auth_method='none',
                    authorized_keys=None,
                    ldap_server=None,
                    ldap_base_dn=None,
                    audit_log=None,
                )
            except KeyboardInterrupt:
                pass

            # Should have created HTTPProxyHandler
            mock_handler_class.assert_called_once()
            # Should call dilate before running handler
            mock_manager.dilate.assert_called_once()


class TestListenServeMode:
    """Test listen command with file server mode."""

    @pytest.mark.asyncio
    async def test_listen_serve_mode(self):
        """Test --serve flag initializes file server."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
                 patch("wh.http.server.HTTPFileServer") as mock_server_class, \
                 patch("asyncio.wait_for") as mock_wait_for:

                mock_manager = AsyncMock()
                mock_manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
                mock_manager.dilate = AsyncMock()
                mock_manager.close = AsyncMock()
                mock_manager_class.return_value = mock_manager

                # Mock wait_for to succeed immediately
                mock_wait_for.return_value = None

                mock_server = AsyncMock()
                mock_server.run = AsyncMock(side_effect=KeyboardInterrupt())
                mock_server_class.return_value = mock_server

                try:
                    await listen_callback(
                        ctx=mock_ctx,
                        port=None,
                        ssh=False,
                        http=False,
                        serve=tmpdir,
                        dilate=True,
                        code=None,
                        auth_method='none',
                        authorized_keys=None,
                        ldap_server=None,
                        ldap_base_dn=None,
                        audit_log=None,
                    )
                except KeyboardInterrupt:
                    pass

                # Should have created HTTPFileServer with directory
                mock_server_class.assert_called_once()
                call_args = mock_server_class.call_args
                assert tmpdir in str(call_args[0])


class TestListenCustomCode:
    """Test listen command with custom code."""

    @pytest.mark.asyncio
    async def test_listen_custom_code(self):
        """Test --code flag uses provided code."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
             patch("asyncio.Event") as mock_event_class:

            mock_manager = AsyncMock()
            mock_manager.create_and_set_code = AsyncMock()
            mock_manager.close = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_event = AsyncMock()
            mock_event.wait = AsyncMock(side_effect=KeyboardInterrupt())
            mock_event_class.return_value = mock_event

            try:
                await listen_callback(
                    ctx=mock_ctx,
                    port=None,
                    ssh=False,
                    http=False,
                    serve=None,
                    dilate=True,
                    code="7-custom-code",
                    auth_method='none',
                    authorized_keys=None,
                    ldap_server=None,
                    ldap_base_dn=None,
                    audit_log=None,
                )
            except KeyboardInterrupt:
                pass

            # Should use create_and_set_code instead of allocate
            mock_manager.create_and_set_code.assert_called_once_with("7-custom-code")


class TestListenAuthPubkey:
    """Test listen command with pubkey authentication."""

    @pytest.mark.asyncio
    async def test_listen_auth_pubkey(self):
        """Test --auth-method=pubkey creates authenticator."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        with tempfile.NamedTemporaryFile(mode='w', suffix='_authorized_keys', delete=False) as f:
            authorized_keys_file = f.name
            f.write("abc123 test-key\n")

        try:
            with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
                 patch("wh.enterprise.auth.create_authenticator") as mock_create_auth, \
                 patch("asyncio.Event") as mock_event_class:

                mock_manager = AsyncMock()
                mock_manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
                mock_manager.close = AsyncMock()
                mock_manager_class.return_value = mock_manager

                mock_authenticator = MagicMock()
                mock_create_auth.return_value = mock_authenticator

                mock_event = AsyncMock()
                mock_event.wait = AsyncMock(side_effect=KeyboardInterrupt())
                mock_event_class.return_value = mock_event

                try:
                    await listen_callback(
                        ctx=mock_ctx,
                        port=None,
                        ssh=False,
                        http=False,
                        serve=None,
                        dilate=True,
                        code=None,
                        auth_method='pubkey',
                        authorized_keys=authorized_keys_file,
                        ldap_server=None,
                        ldap_base_dn=None,
                        audit_log=None,
                    )
                except KeyboardInterrupt:
                    pass

                # Should have created pubkey authenticator
                mock_create_auth.assert_called_once()
                call_args, call_kwargs = mock_create_auth.call_args
                assert call_kwargs["authorized_keys"] == authorized_keys_file
        finally:
            Path(authorized_keys_file).unlink()


class TestListenAuthLDAP:
    """Test listen command with LDAP authentication."""

    @pytest.mark.asyncio
    async def test_listen_auth_ldap(self):
        """Test --auth-method=ldap creates LDAP authenticator."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
             patch("wh.enterprise.auth.create_authenticator") as mock_create_auth, \
             patch("asyncio.Event") as mock_event_class:

            mock_manager = AsyncMock()
            mock_manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
            mock_manager.close = AsyncMock()
            mock_manager_class.return_value = mock_manager

            mock_authenticator = MagicMock()
            mock_create_auth.return_value = mock_authenticator

            mock_event = AsyncMock()
            mock_event.wait = AsyncMock(side_effect=KeyboardInterrupt())
            mock_event_class.return_value = mock_event

            try:
                await listen_callback(
                    ctx=mock_ctx,
                    port=None,
                    ssh=False,
                    http=False,
                    serve=None,
                    dilate=True,
                    code=None,
                    auth_method='ldap',
                    authorized_keys=None,
                    ldap_server="ldap://ad.company.com",
                    ldap_base_dn="dc=company,dc=com",
                    audit_log=None,
                )
            except KeyboardInterrupt:
                pass

            # Should have created LDAP authenticator
            mock_create_auth.assert_called_once()
            call_args, call_kwargs = mock_create_auth.call_args
            assert call_kwargs["ldap_server"] == "ldap://ad.company.com"
            assert call_kwargs["ldap_base_dn"] == "dc=company,dc=com"


class TestListenAuthPubkeyNoKeys:
    """Test listen command with pubkey auth but missing authorized-keys."""

    @pytest.mark.asyncio
    async def test_listen_auth_pubkey_no_keys(self):
        """Test missing --authorized-keys raises ClickException."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        with pytest.raises(click.ClickException) as exc_info:
            await listen_callback(
                ctx=mock_ctx,
                port=None,
                ssh=False,
                http=False,
                serve=None,
                dilate=True,
                code=None,
                auth_method='pubkey',
                authorized_keys=None,
                ldap_server=None,
                ldap_base_dn=None,
                audit_log=None,
            )

        # Should fail with error message
        assert "authorized-keys required" in str(exc_info.value).lower()


class TestListenAuditLogging:
    """Test listen command with audit logging."""

    @pytest.mark.asyncio
    async def test_listen_audit_logging(self):
        """Test --audit-log flag initializes AuditLogger."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            audit_log_file = f.name

        try:
            with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
                 patch("wh.enterprise.audit.AuditLogger") as mock_audit_class, \
                 patch("asyncio.Event") as mock_event_class:

                mock_manager = AsyncMock()
                mock_manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
                mock_manager.close = AsyncMock()
                mock_manager_class.return_value = mock_manager

                mock_audit_logger = MagicMock()
                mock_audit_logger.connection_start = MagicMock()
                mock_audit_logger.connection_end = MagicMock()
                mock_audit_logger.close = MagicMock()
                mock_audit_class.return_value = mock_audit_logger

                mock_event = AsyncMock()
                mock_event.wait = AsyncMock(side_effect=KeyboardInterrupt())
                mock_event_class.return_value = mock_event

                try:
                    await listen_callback(
                        ctx=mock_ctx,
                        port=None,
                        ssh=False,
                        http=False,
                        serve=None,
                        dilate=True,
                        code=None,
                        auth_method='none',
                        authorized_keys=None,
                        ldap_server=None,
                        ldap_base_dn=None,
                        audit_log=audit_log_file,
                    )
                except KeyboardInterrupt:
                    pass

                # Should have created AuditLogger with log file
                mock_audit_class.assert_called_once_with(log_file=audit_log_file)
                # Should log connection start
                mock_audit_logger.connection_start.assert_called_once()
                # Should log connection end in finally block
                mock_audit_logger.connection_end.assert_called_once()
                # Should close logger
                mock_audit_logger.close.assert_called_once()
        finally:
            Path(audit_log_file).unlink()


class TestListenDilationTimeout:
    """Test listen command with dilation timeout."""

    @pytest.mark.asyncio
    async def test_listen_dilation_timeout(self):
        """Test dilation fallback after timeout."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 1, 'namespace': None}  # verbose for timeout message

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
                 patch("wh.http.server.HTTPFileServer") as mock_server_class, \
                 patch("asyncio.wait_for") as mock_wait_for:

                mock_manager = AsyncMock()
                mock_manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
                mock_manager.dilate = AsyncMock()
                mock_manager.close = AsyncMock()
                mock_manager_class.return_value = mock_manager

                # Simulate dilation timeout
                mock_wait_for.side_effect = asyncio.TimeoutError()

                mock_server = AsyncMock()
                mock_server.run = AsyncMock(side_effect=KeyboardInterrupt())
                mock_server_class.return_value = mock_server

                try:
                    await listen_callback(
                        ctx=mock_ctx,
                        port=None,
                        ssh=False,
                        http=False,
                        serve=tmpdir,
                        dilate=True,
                        code=None,
                        auth_method='none',
                        authorized_keys=None,
                        ldap_server=None,
                        ldap_base_dn=None,
                        audit_log=None,
                    )
                except KeyboardInterrupt:
                    pass

                # Should continue after timeout - server should still be created
                mock_server_class.assert_called_once()


class TestListenNoDilation:
    """Test listen command with --no-dilate flag."""

    @pytest.mark.asyncio
    async def test_listen_no_dilation(self):
        """Test --no-dilate flag skips dilation."""
        from wh.cli.listen import listen
        listen_callback = listen.callback.__wrapped__.__wrapped__

        mock_ctx = MagicMock()
        mock_ctx.obj = {'verbose': 0, 'namespace': None}

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("wh.cli.listen.WormholeManager") as mock_manager_class, \
                 patch("wh.http.server.HTTPFileServer") as mock_server_class, \
                 patch("asyncio.wait_for") as mock_wait_for:

                mock_manager = AsyncMock()
                mock_manager.create_and_allocate_code = AsyncMock(return_value="7-guitar-sunset")
                mock_manager.verify_connection = AsyncMock()
                mock_manager.close = AsyncMock()
                mock_manager_class.return_value = mock_manager

                mock_server = AsyncMock()
                mock_server.run = AsyncMock(side_effect=KeyboardInterrupt())
                mock_server_class.return_value = mock_server

                try:
                    await listen_callback(
                        ctx=mock_ctx,
                        port=None,
                        ssh=False,
                        http=False,
                        serve=tmpdir,
                        dilate=False,  # no-dilate
                        code=None,
                        auth_method='none',
                        authorized_keys=None,
                        ldap_server=None,
                        ldap_base_dn=None,
                        audit_log=None,
                    )
                except KeyboardInterrupt:
                    pass

                # Should NOT call asyncio.wait_for (which wraps dilate)
                mock_wait_for.assert_not_called()
                # Should call verify_connection instead
                mock_manager.verify_connection.assert_called_once()
