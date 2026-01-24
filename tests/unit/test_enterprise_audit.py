"""Unit tests for enterprise audit logging module."""

import json
import os
import tempfile
from datetime import datetime

import pytest

from wh.enterprise.audit import (
    AuditEvent,
    AuditEventType,
    AuditConfig,
    AuditLogger,
    configure_audit_logging,
    get_audit_logger,
)


class TestAuditEventType:
    """Tests for AuditEventType enum."""

    def test_values(self):
        """Test enum values."""
        assert AuditEventType.CONNECTION_START.value == "connection_start"
        assert AuditEventType.CONNECTION_END.value == "connection_end"
        assert AuditEventType.AUTH_SUCCESS.value == "auth_success"
        assert AuditEventType.AUTH_FAILURE.value == "auth_failure"
        assert AuditEventType.FILE_TRANSFER.value == "file_transfer"
        assert AuditEventType.COMMAND_EXEC.value == "command_exec"
        assert AuditEventType.POLICY_VIOLATION.value == "policy_violation"
        assert AuditEventType.NAMESPACE_CHANGE.value == "namespace_change"


class TestAuditEvent:
    """Tests for AuditEvent dataclass."""

    def test_basic_event(self):
        """Test creating basic event."""
        event = AuditEvent(event_type=AuditEventType.CONNECTION_START)

        assert event.event_type == AuditEventType.CONNECTION_START
        assert event.success is True
        assert event.identity is None
        assert event.timestamp is not None

    def test_full_event(self):
        """Test creating event with all fields."""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_FAILURE,
            identity="jdoe",
            namespace="engineering",
            source_ip="192.168.1.100",
            session_id="abc123",
            success=False,
            details={"reason": "Invalid password"},
        )

        assert event.event_type == AuditEventType.AUTH_FAILURE
        assert event.identity == "jdoe"
        assert event.namespace == "engineering"
        assert event.source_ip == "192.168.1.100"
        assert event.success is False

    def test_to_dict(self):
        """Test converting to dictionary."""
        event = AuditEvent(
            event_type=AuditEventType.FILE_TRANSFER,
            identity="jdoe",
            details={"filename": "test.txt", "size": 1024},
        )

        d = event.to_dict()

        assert d["event"] == "file_transfer"
        assert d["identity"] == "jdoe"
        assert d["success"] is True
        assert d["details"]["filename"] == "test.txt"
        assert "timestamp" in d

    def test_to_json(self):
        """Test converting to JSON."""
        event = AuditEvent(
            event_type=AuditEventType.CONNECTION_START,
            identity="jdoe",
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["event"] == "connection_start"
        assert parsed["identity"] == "jdoe"

    def test_timestamp_format(self):
        """Test timestamp is ISO format."""
        event = AuditEvent(event_type=AuditEventType.CONNECTION_START)

        # Should be parseable as ISO format
        parsed = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        assert parsed is not None


class TestAuditConfig:
    """Tests for AuditConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = AuditConfig()

        assert config.log_file is None
        assert config.log_to_stdout is False
        assert config.max_file_size == 10 * 1024 * 1024
        assert config.backup_count == 5
        assert config.filter_events is None
        assert config.include_success_only is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = AuditConfig(
            log_file="/var/log/wh/audit.log",
            log_to_stdout=True,
            max_file_size=5 * 1024 * 1024,
            backup_count=10,
            filter_events=[AuditEventType.AUTH_FAILURE],
            include_success_only=True,
        )

        assert config.log_file == "/var/log/wh/audit.log"
        assert config.log_to_stdout is True
        assert config.max_file_size == 5 * 1024 * 1024


class TestAuditLogger:
    """Tests for AuditLogger class."""

    @pytest.fixture
    def temp_log_file(self):
        """Create a temporary log file."""
        fd, path = tempfile.mkstemp(suffix=".log")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_init_with_file(self, temp_log_file):
        """Test initialization with log file."""
        logger = AuditLogger(log_file=temp_log_file)
        assert logger.config.log_file == temp_log_file
        logger.close()

    def test_log_event(self, temp_log_file):
        """Test logging an event."""
        logger = AuditLogger(log_file=temp_log_file)

        event = AuditEvent(
            event_type=AuditEventType.CONNECTION_START,
            identity="jdoe",
        )
        logger.log_event(event)
        logger.close()

        # Verify log file contents
        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "connection_start" in content
            assert "jdoe" in content

    def test_log_convenience_method(self, temp_log_file):
        """Test log() convenience method."""
        logger = AuditLogger(log_file=temp_log_file)

        logger.log(
            AuditEventType.AUTH_SUCCESS,
            identity="jdoe",
            details={"method": "pubkey"},
        )
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "auth_success" in content
            assert "pubkey" in content

    def test_connection_start(self, temp_log_file):
        """Test connection_start convenience method."""
        logger = AuditLogger(log_file=temp_log_file)

        logger.connection_start(
            code="7-guitar-sunset",
            peer_address="192.168.1.100",
            identity="jdoe",
        )
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "connection_start" in content
            assert "7-guitar-sunset" in content

    def test_connection_end(self, temp_log_file):
        """Test connection_end convenience method."""
        logger = AuditLogger(log_file=temp_log_file)

        logger.connection_end(
            code="7-guitar-sunset",
            duration_seconds=120.5,
            bytes_sent=1024,
            bytes_received=2048,
        )
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "connection_end" in content
            assert "120.5" in content

    def test_auth_success(self, temp_log_file):
        """Test auth_success convenience method."""
        logger = AuditLogger(log_file=temp_log_file)

        logger.auth_success(
            method="ldap",
            identity="jdoe",
            source_ip="192.168.1.100",
        )
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "auth_success" in content
            assert "ldap" in content

    def test_auth_failure(self, temp_log_file):
        """Test auth_failure convenience method."""
        logger = AuditLogger(log_file=temp_log_file)

        logger.auth_failure(
            method="password",
            attempted_identity="jdoe",
            reason="Invalid password",
            source_ip="192.168.1.100",
        )
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "auth_failure" in content
            assert "Invalid password" in content

    def test_file_transfer(self, temp_log_file):
        """Test file_transfer convenience method."""
        logger = AuditLogger(log_file=temp_log_file)

        logger.file_transfer(
            filename="document.pdf",
            direction="upload",
            size_bytes=102400,
            identity="jdoe",
        )
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "file_transfer" in content
            assert "document.pdf" in content
            assert "upload" in content

    def test_command_exec(self, temp_log_file):
        """Test command_exec convenience method."""
        logger = AuditLogger(log_file=temp_log_file)

        logger.command_exec(
            command="ls -la",
            exit_code=0,
            identity="jdoe",
        )
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "command_exec" in content
            assert "ls -la" in content

    def test_policy_violation(self, temp_log_file):
        """Test policy_violation convenience method."""
        logger = AuditLogger(log_file=temp_log_file)

        logger.policy_violation(
            policy_type="rate_limit",
            violation="Exceeded 10 connections per minute",
            source_ip="192.168.1.100",
        )
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "policy_violation" in content
            assert "rate_limit" in content

    def test_namespace_change(self, temp_log_file):
        """Test namespace_change convenience method."""
        logger = AuditLogger(log_file=temp_log_file)

        logger.namespace_change(
            action="create",
            namespace="engineering",
            identity="admin",
        )
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "namespace_change" in content
            assert "create" in content

    def test_event_filtering(self, temp_log_file):
        """Test event type filtering."""
        config = AuditConfig(
            log_file=temp_log_file,
            filter_events=[AuditEventType.AUTH_FAILURE],
        )
        logger = AuditLogger(config=config)

        # This should be filtered out
        logger.auth_success(method="ldap", identity="jdoe")

        # This should be logged
        logger.auth_failure(method="ldap", reason="Invalid password")

        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "auth_failure" in content
            # auth_success should not be present
            lines = [line for line in content.strip().split("\n") if line]
            assert len(lines) == 1

    def test_success_only_filtering(self, temp_log_file):
        """Test success-only filtering."""
        config = AuditConfig(
            log_file=temp_log_file,
            include_success_only=True,
        )
        logger = AuditLogger(config=config)

        # This should be logged
        logger.auth_success(method="ldap", identity="jdoe")

        # This should be filtered out (success=False)
        logger.auth_failure(method="ldap", reason="Invalid password")

        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            assert "auth_success" in content
            assert "auth_failure" not in content

    def test_callback(self, temp_log_file):
        """Test event callback."""
        logger = AuditLogger(log_file=temp_log_file)

        received_events = []

        def callback(event):
            received_events.append(event)

        logger.add_callback(callback)

        logger.connection_start(code="7-guitar-sunset")
        logger.connection_end(code="7-guitar-sunset")

        assert len(received_events) == 2
        assert received_events[0].event_type == AuditEventType.CONNECTION_START
        assert received_events[1].event_type == AuditEventType.CONNECTION_END

        logger.close()

    def test_remove_callback(self, temp_log_file):
        """Test removing callback."""
        logger = AuditLogger(log_file=temp_log_file)

        received_events = []

        def callback(event):
            received_events.append(event)

        logger.add_callback(callback)
        logger.connection_start(code="7-guitar-sunset")

        logger.remove_callback(callback)
        logger.connection_end(code="7-guitar-sunset")

        assert len(received_events) == 1

        logger.close()

    def test_stdout_logging(self, capsys):
        """Test logging to stdout."""
        config = AuditConfig(log_to_stdout=True)
        logger = AuditLogger(config=config)

        logger.connection_start(code="7-guitar-sunset")
        logger.close()

        captured = capsys.readouterr()
        assert "connection_start" in captured.out

    def test_json_pretty(self, temp_log_file):
        """Test pretty JSON output."""
        config = AuditConfig(
            log_file=temp_log_file,
            json_pretty=True,
        )
        logger = AuditLogger(config=config)

        logger.connection_start(code="7-guitar-sunset")
        logger.close()

        with open(temp_log_file, "r") as f:
            content = f.read()
            # Pretty JSON should have newlines
            assert "\n" in content
            assert "  " in content  # Indentation


class TestGlobalAuditLogger:
    """Tests for global audit logger functions."""

    @pytest.fixture
    def temp_log_file(self):
        """Create a temporary log file."""
        fd, path = tempfile.mkstemp(suffix=".log")
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_configure_and_get(self, temp_log_file):
        """Test configuring and getting global logger."""
        logger = configure_audit_logging(log_file=temp_log_file)
        assert logger is not None

        retrieved = get_audit_logger()
        assert retrieved is logger

        logger.close()

    def test_get_without_configure(self):
        """Test getting logger before configuration."""
        # Reset global state
        import wh.enterprise.audit as audit_module
        audit_module._global_audit_logger = None

        get_audit_logger()
        # May be None if not configured
        # This is expected behavior
