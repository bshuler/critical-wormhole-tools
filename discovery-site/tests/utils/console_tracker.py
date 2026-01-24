"""Console message tracking for Playwright tests."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page, ConsoleMessage


@dataclass
class TrackedMessage:
    """A tracked console message."""

    type: str  # log, warn, error, info, debug
    text: str
    location: str = ""


class ConsoleTracker:
    """Tracks console messages and errors from a Playwright page.

    Attaches to a Playwright page and captures all console output,
    separating errors for easy assertion checking.

    Usage:
        tracker = ConsoleTracker(page)
        # ... interact with page ...
        assert tracker.has_message("[Test] loaded")
        tracker.assert_no_errors()
    """

    def __init__(self, page: "Page"):
        """Initialize and attach to a Playwright page.

        Args:
            page: Playwright page to track
        """
        self.page = page
        self.messages: list[TrackedMessage] = []
        self.errors: list[TrackedMessage] = []
        self._attached = False
        self._attach()

    def _attach(self):
        """Attach console listener to the page."""
        if self._attached:
            return

        def on_console(msg: "ConsoleMessage"):
            tracked = TrackedMessage(
                type=msg.type,
                text=msg.text,
                location=str(msg.location) if msg.location else "",
            )
            self.messages.append(tracked)

            # Also track errors separately
            if msg.type in ("error", "warning"):
                self.errors.append(tracked)

            # Print for debugging
            prefix = "ERROR" if msg.type == "error" else msg.type.upper()
            print(f"[Console {prefix}] {msg.text}")

        def on_page_error(error):
            tracked = TrackedMessage(
                type="pageerror",
                text=str(error),
            )
            self.messages.append(tracked)
            self.errors.append(tracked)
            print(f"[Page ERROR] {error}")

        self.page.on("console", on_console)
        self.page.on("pageerror", on_page_error)
        self._attached = True

    def has_message(self, substring: str, msg_type: str | None = None) -> bool:
        """Check if any message contains the substring.

        Args:
            substring: Text to search for in messages
            msg_type: Optional filter by message type (log, warn, error, etc.)

        Returns:
            True if a matching message was found
        """
        for msg in self.messages:
            if msg_type and msg.type != msg_type:
                continue
            if substring in msg.text:
                return True
        return False

    def has_error(self) -> bool:
        """Check if any errors were recorded.

        Returns:
            True if there are any errors
        """
        return len(self.errors) > 0

    def get_errors(self) -> list[str]:
        """Get all error messages.

        Returns:
            List of error message texts
        """
        return [e.text for e in self.errors]

    def get_messages(self, msg_type: str | None = None) -> list[str]:
        """Get all messages, optionally filtered by type.

        Args:
            msg_type: Optional filter by message type

        Returns:
            List of message texts
        """
        if msg_type:
            return [m.text for m in self.messages if m.type == msg_type]
        return [m.text for m in self.messages]

    def assert_no_errors(self, ignore_patterns: list[str] | None = None):
        """Assert that no errors were recorded.

        Args:
            ignore_patterns: List of substrings to ignore in error messages

        Raises:
            AssertionError: If there are unignored errors
        """
        ignore_patterns = ignore_patterns or []

        unignored_errors = []
        for error in self.errors:
            # Check if this error should be ignored
            should_ignore = False
            for pattern in ignore_patterns:
                if pattern in error.text:
                    should_ignore = True
                    break
            if not should_ignore:
                unignored_errors.append(error.text)

        if unignored_errors:
            error_list = "\n  - ".join(unignored_errors)
            raise AssertionError(f"Found {len(unignored_errors)} JS error(s):\n  - {error_list}")

    def clear(self):
        """Clear all tracked messages and errors."""
        self.messages.clear()
        self.errors.clear()

    def __repr__(self) -> str:
        return f"ConsoleTracker(messages={len(self.messages)}, errors={len(self.errors)})"
