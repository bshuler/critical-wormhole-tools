"""
Enterprise Audit Logging Module.

Provides structured audit logging for SIEM integration:
- JSON log format for easy parsing
- Log rotation support
- Configurable event filtering
- Async-safe logging

Event types:
- connection_start: Wormhole connection established
- connection_end: Wormhole connection closed
- auth_success: Successful authentication
- auth_failure: Failed authentication attempt
- file_transfer: File uploaded or downloaded
- command_exec: Command executed (SSH)
- policy_violation: Rate limit or policy exceeded
- namespace_change: Namespace created/deleted

Usage:
    logger = AuditLogger("/var/log/wh/audit.log")
    logger.log_event(AuditEventType.CONNECTION_START, {
        "code": "7-guitar-sunset",
        "peer_address": "192.168.1.100",
    })
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    CONNECTION_START = "connection_start"
    CONNECTION_END = "connection_end"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    FILE_TRANSFER = "file_transfer"
    COMMAND_EXEC = "command_exec"
    POLICY_VIOLATION = "policy_violation"
    NAMESPACE_CHANGE = "namespace_change"
    CONFIG_CHANGE = "config_change"
    ERROR = "error"


@dataclass
class AuditEvent:
    """
    Represents an audit event.

    Attributes:
        event_type: Type of event
        timestamp: When the event occurred
        identity: User/identity associated with event
        namespace: Namespace where event occurred
        source_ip: Source IP address if known
        details: Additional event-specific details
        session_id: Session or connection identifier
        success: Whether the action succeeded (for auth, transfers)
    """
    event_type: AuditEventType
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    identity: Optional[str] = None
    namespace: Optional[str] = None
    source_ip: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        result = {
            "event": self.event_type.value,
            "timestamp": self.timestamp,
            "success": self.success,
        }

        if self.identity:
            result["identity"] = self.identity
        if self.namespace:
            result["namespace"] = self.namespace
        if self.source_ip:
            result["source_ip"] = self.source_ip
        if self.session_id:
            result["session_id"] = self.session_id
        if self.details:
            result["details"] = self.details

        return result

    def to_json(self) -> str:
        """Convert event to JSON string."""
        return json.dumps(self.to_dict())


@dataclass
class AuditConfig:
    """Configuration for audit logging."""
    log_file: Optional[str] = None
    log_to_stdout: bool = False
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 5
    filter_events: Optional[List[AuditEventType]] = None  # None = log all
    include_success_only: bool = False
    json_pretty: bool = False


class AuditLogger:
    """
    Audit logger for enterprise security logging.

    Writes structured JSON logs suitable for SIEM systems like:
    - Splunk
    - Elasticsearch/ELK
    - Datadog
    - Azure Sentinel
    """

    def __init__(
        self,
        log_file: Optional[str] = None,
        config: Optional[AuditConfig] = None,
    ):
        """
        Initialize audit logger.

        Args:
            log_file: Path to audit log file (overrides config)
            config: Full configuration object
        """
        self.config = config or AuditConfig()
        if log_file:
            self.config.log_file = log_file

        self._logger: Optional[logging.Logger] = None
        self._handlers: List[logging.Handler] = []
        self._callbacks: List[Callable[[AuditEvent], None]] = []
        self._lock = asyncio.Lock()

        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up the logging infrastructure."""
        # Create a dedicated logger
        self._logger = logging.getLogger(f"wh.audit.{id(self)}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        # Clear existing handlers
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)

        # File handler with rotation
        if self.config.log_file:
            log_path = Path(self.config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                str(log_path),
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(file_handler)
            self._handlers.append(file_handler)

        # Stdout handler
        if self.config.log_to_stdout:
            stdout_handler = logging.StreamHandler(sys.stdout)
            stdout_handler.setLevel(logging.INFO)
            stdout_handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(stdout_handler)
            self._handlers.append(stdout_handler)

    def add_callback(self, callback: Callable[[AuditEvent], None]) -> None:
        """
        Add a callback to be called for each audit event.

        Useful for real-time processing, alerting, or custom logging.
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[AuditEvent], None]) -> None:
        """Remove a previously added callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _should_log(self, event: AuditEvent) -> bool:
        """Check if event should be logged based on filters."""
        # Filter by event type
        if self.config.filter_events:
            if event.event_type not in self.config.filter_events:
                return False

        # Filter by success
        if self.config.include_success_only and not event.success:
            return False

        return True

    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: The AuditEvent to log
        """
        if not self._should_log(event):
            return

        # Write to log
        if self._logger:
            if self.config.json_pretty:
                log_line = json.dumps(event.to_dict(), indent=2)
            else:
                log_line = event.to_json()
            self._logger.info(log_line)

        # Call callbacks
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.warning(f"Audit callback error: {e}")

    def log(
        self,
        event_type: AuditEventType,
        details: Optional[Dict[str, Any]] = None,
        identity: Optional[str] = None,
        namespace: Optional[str] = None,
        source_ip: Optional[str] = None,
        session_id: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """
        Log an audit event with the given parameters.

        Convenience method that creates AuditEvent internally.
        """
        event = AuditEvent(
            event_type=event_type,
            identity=identity,
            namespace=namespace,
            source_ip=source_ip,
            details=details or {},
            session_id=session_id,
            success=success,
        )
        self.log_event(event)

    # Convenience methods for common event types

    def connection_start(
        self,
        code: str,
        peer_address: Optional[str] = None,
        identity: Optional[str] = None,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a connection start event."""
        self.log(
            AuditEventType.CONNECTION_START,
            details={"code": code, "peer_address": peer_address},
            identity=identity,
            namespace=namespace,
            source_ip=peer_address,
            session_id=session_id,
        )

    def connection_end(
        self,
        code: str,
        duration_seconds: Optional[float] = None,
        bytes_sent: Optional[int] = None,
        bytes_received: Optional[int] = None,
        identity: Optional[str] = None,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a connection end event."""
        details = {"code": code}
        if duration_seconds is not None:
            details["duration_seconds"] = duration_seconds
        if bytes_sent is not None:
            details["bytes_sent"] = bytes_sent
        if bytes_received is not None:
            details["bytes_received"] = bytes_received

        self.log(
            AuditEventType.CONNECTION_END,
            details=details,
            identity=identity,
            namespace=namespace,
            session_id=session_id,
        )

    def auth_success(
        self,
        method: str,
        identity: str,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a successful authentication."""
        self.log(
            AuditEventType.AUTH_SUCCESS,
            details={"method": method},
            identity=identity,
            source_ip=source_ip,
            namespace=namespace,
            session_id=session_id,
            success=True,
        )

    def auth_failure(
        self,
        method: str,
        attempted_identity: Optional[str] = None,
        reason: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a failed authentication."""
        details = {"method": method}
        if reason:
            details["reason"] = reason
        if attempted_identity:
            details["attempted_identity"] = attempted_identity

        self.log(
            AuditEventType.AUTH_FAILURE,
            details=details,
            source_ip=source_ip,
            namespace=namespace,
            session_id=session_id,
            success=False,
        )

    def file_transfer(
        self,
        filename: str,
        direction: str,  # "upload" or "download"
        size_bytes: int,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
        success: bool = True,
    ) -> None:
        """Log a file transfer event."""
        self.log(
            AuditEventType.FILE_TRANSFER,
            details={
                "filename": filename,
                "direction": direction,
                "size_bytes": size_bytes,
            },
            identity=identity,
            source_ip=source_ip,
            namespace=namespace,
            session_id=session_id,
            success=success,
        )

    def command_exec(
        self,
        command: str,
        exit_code: Optional[int] = None,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a command execution event."""
        details = {"command": command}
        if exit_code is not None:
            details["exit_code"] = exit_code

        self.log(
            AuditEventType.COMMAND_EXEC,
            details=details,
            identity=identity,
            source_ip=source_ip,
            namespace=namespace,
            session_id=session_id,
            success=(exit_code == 0 if exit_code is not None else True),
        )

    def policy_violation(
        self,
        policy_type: str,
        violation: str,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        namespace: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a policy violation event."""
        self.log(
            AuditEventType.POLICY_VIOLATION,
            details={
                "policy_type": policy_type,
                "violation": violation,
            },
            identity=identity,
            source_ip=source_ip,
            namespace=namespace,
            session_id=session_id,
            success=False,
        )

    def namespace_change(
        self,
        action: str,  # "create", "delete", "modify"
        namespace: str,
        identity: Optional[str] = None,
        source_ip: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a namespace change event."""
        self.log(
            AuditEventType.NAMESPACE_CHANGE,
            details={"action": action},
            namespace=namespace,
            identity=identity,
            source_ip=source_ip,
            session_id=session_id,
        )

    def close(self) -> None:
        """Close the audit logger and flush all handlers."""
        for handler in self._handlers:
            handler.flush()
            handler.close()
        self._handlers.clear()


# Global audit logger instance
_global_audit_logger: Optional[AuditLogger] = None


def configure_audit_logging(
    log_file: Optional[str] = None,
    log_to_stdout: bool = False,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> AuditLogger:
    """
    Configure the global audit logger.

    Args:
        log_file: Path to audit log file
        log_to_stdout: Also log to stdout
        max_file_size: Max size before rotation
        backup_count: Number of backup files to keep

    Returns:
        The configured AuditLogger
    """
    global _global_audit_logger

    config = AuditConfig(
        log_file=log_file,
        log_to_stdout=log_to_stdout,
        max_file_size=max_file_size,
        backup_count=backup_count,
    )

    _global_audit_logger = AuditLogger(config=config)
    return _global_audit_logger


def get_audit_logger() -> Optional[AuditLogger]:
    """Get the global audit logger, if configured."""
    return _global_audit_logger
