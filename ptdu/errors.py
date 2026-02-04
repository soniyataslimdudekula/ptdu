"""Error handling and user feedback for PTDU."""

from __future__ import annotations

import os
import tkinter as tk
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from tkinter import messagebox
from typing import Callable, Optional


class ErrorSeverity(Enum):
    """Error severity levels."""

    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


@dataclass
class PTDUError:
    """Structured error information."""

    message: str
    severity: ErrorSeverity
    path: Optional[Path] = None
    suggestion: Optional[str] = None
    recoverable: bool = True


class ErrorHandler:
    """Centralized error handling with user-friendly dialogs."""

    def __init__(self, parent: Optional[tk.Tk] = None) -> None:
        """Initialize error handler.

        Args:
            parent: Parent Tk window for dialogs
        """
        self._parent: Optional[tk.Tk] = parent
        self._error_history: list[PTDUError] = []
        self._max_history: int = 100
        self._silent_mode: bool = False

    def set_parent(self, parent: tk.Tk) -> None:
        """Set parent window for dialogs.

        Args:
            parent: Tk root window
        """
        self._parent = parent

    def set_silent_mode(self, silent: bool) -> bool:
        """Set silent mode (suppress dialogs).

        Args:
            silent: True to suppress dialogs

        Returns:
            Previous silent mode state
        """
        previous = self._silent_mode
        self._silent_mode = silent
        return previous

    def handle_permission_denied(
        self,
        path: Path,
        operation: str = "access",
        callback: Optional[Callable[[], None]] = None,
    ) -> bool:
        """Handle permission denied error with user dialog.

        Args:
            path: Path that caused permission error
            operation: Operation being attempted (access, read, delete, etc.)
            callback: Optional callback for retry

        Returns:
            True if user wants to continue, False to abort
        """
        error = PTDUError(
            message=f"Permission denied: Cannot {operation} {path.name}",
            severity=ErrorSeverity.ERROR,
            path=path,
            suggestion="Try running with elevated permissions or check file permissions",
            recoverable=True,
        )

        self._log_error(error)

        if self._silent_mode:
            return True

        # Build dialog message
        msg = f"Permission denied\n\n"
        msg += f"Cannot {operation}:\n{path}\n\n"

        # Add helpful context
        if path.exists():
            try:
                stat = os.stat(path)
                msg += f"Owner: {stat.st_uid}, Group: {stat.st_gid}\n"
                msg += f"Permissions: {oct(stat.st_mode)[-3:]}\n\n"
            except (OSError, PermissionError):
                pass

        msg += "You may need to run with sudo or check file permissions."

        # Show dialog with retry option if callback provided
        if callback is not None:
            result = messagebox.askretrycancel(
                "Permission Denied",
                msg,
                icon=messagebox.ERROR,
                parent=self._parent,
            )
            if result:
                callback()
                return True
            return False
        else:
            messagebox.showerror(
                "Permission Denied",
                msg,
                parent=self._parent,
            )
            return True

    def handle_path_too_long(self, path: Path) -> bool:
        """Handle long path error.

        Args:
            path: Path that exceeds length limits

        Returns:
            True if handled, False if critical
        """
        # Check actual path length
        path_str = str(path)
        path_len = len(path_str)

        error = PTDUError(
            message=f"Path too long ({path_len} characters)",
            severity=ErrorSeverity.WARNING,
            path=path,
            suggestion="Consider using a shorter path or enabling long path support",
            recoverable=True,
        )

        self._log_error(error)

        if self._silent_mode:
            return True

        msg = f"Path is very long ({path_len} characters)\n\n"
        msg += f"{path_str[:100]}...\n\n"

        if path_len > 4096:
            msg += "This path exceeds typical filesystem limits and may cause issues."
            severity = messagebox.ERROR
        else:
            msg += "This path may cause issues on some systems."
            severity = messagebox.WARNING

        messagebox.showwarning(
            "Long Path Warning",
            msg,
            parent=self._parent,
        )
        return True

    def handle_scan_error(
        self,
        path: Path,
        error: Exception,
        continue_scan: bool = True,
    ) -> bool:
        """Handle scanning error.

        Args:
            path: Path being scanned
            error: Exception that occurred
            continue_scan: Whether to offer continue option

        Returns:
            True to continue, False to abort
        """
        error_msg = str(error)
        severity = ErrorSeverity.WARNING if continue_scan else ErrorSeverity.ERROR

        # Categorize common errors
        if "permission" in error_msg.lower():
            return self.handle_permission_denied(path, "scan")
        elif "too long" in error_msg.lower() or len(str(path)) > 4000:
            return self.handle_path_too_long(path)

        ptdu_error = PTDUError(
            message=f"Scan error: {error_msg}",
            severity=severity,
            path=path,
            suggestion="Check if the path exists and is accessible",
            recoverable=continue_scan,
        )

        self._log_error(ptdu_error)

        if self._silent_mode:
            return continue_scan

        msg = f"Error scanning:\n{path}\n\n"
        msg += f"Error: {error_msg}\n\n"

        if continue_scan:
            msg += "Continue scanning other directories?"
            result = messagebox.askyesno(
                "Scan Error",
                msg,
                icon=messagebox.WARNING,
                parent=self._parent,
            )
            return result
        else:
            messagebox.showerror(
                "Scan Error",
                msg,
                parent=self._parent,
            )
            return False

    def handle_delete_error(
        self,
        path: Path,
        error: Exception,
    ) -> tuple[bool, bool]:
        """Handle delete operation error.

        Args:
            path: Path being deleted
            error: Exception that occurred

        Returns:
            Tuple of (retry, abort_all)
        """
        error_msg = str(error)

        if "permission" in error_msg.lower():
            return self._handle_delete_permission_denied(path)
        elif "not empty" in error_msg.lower():
            return self._handle_delete_not_empty(path)

        ptdu_error = PTDUError(
            message=f"Delete error: {error_msg}",
            severity=ErrorSeverity.ERROR,
            path=path,
            suggestion="Check file permissions and if file is in use",
            recoverable=True,
        )

        self._log_error(ptdu_error)

        if self._silent_mode:
            return False, False

        msg = f"Could not delete:\n{path}\n\n"
        msg += f"Error: {error_msg}"

        result = messagebox.askyesnocancel(
            "Delete Error",
            msg + "\n\nYes = Retry, No = Skip, Cancel = Abort all",
            icon=messagebox.ERROR,
            parent=self._parent,
        )

        if result is True:  # Retry
            return True, False
        elif result is False:  # Skip
            return False, False
        else:  # Cancel
            return False, True

    def _handle_delete_permission_denied(
        self,
        path: Path,
    ) -> tuple[bool, bool]:
        """Handle delete permission error.

        Args:
            path: Path being deleted

        Returns:
            Tuple of (retry, abort_all)
        """
        if self._silent_mode:
            return False, False

        msg = f"Permission denied when deleting:\n{path}\n\n"
        msg += "You may need elevated permissions to delete this item."

        result = messagebox.askyesnocancel(
            "Delete Permission Denied",
            msg + "\n\nYes = Retry, No = Skip, Cancel = Abort all",
            icon=messagebox.ERROR,
            parent=self._parent,
        )

        if result is True:
            return True, False
        elif result is False:
            return False, False
        else:
            return False, True

    def _handle_delete_not_empty(self, path: Path) -> tuple[bool, bool]:
        """Handle directory not empty error.

        Args:
            path: Path being deleted

        Returns:
            Tuple of (retry, abort_all)
        """
        if self._silent_mode:
            return False, False

        msg = f"Directory not empty:\n{path}\n\n"
        msg += "The directory contains items that couldn't be removed."

        result = messagebox.askyesnocancel(
            "Directory Not Empty",
            msg + "\n\nYes = Retry, No = Skip, Cancel = Abort all",
            icon=messagebox.WARNING,
            parent=self._parent,
        )

        if result is True:
            return True, False
        elif result is False:
            return False, False
        else:
            return False, True

    def handle_export_error(
        self,
        path: Path,
        error: Exception,
    ) -> None:
        """Handle export operation error.

        Args:
            path: Export path
            error: Exception that occurred
        """
        error_msg = str(error)

        ptdu_error = PTDUError(
            message=f"Export error: {error_msg}",
            severity=ErrorSeverity.ERROR,
            path=path,
            suggestion="Check if destination is writable and has available space",
            recoverable=True,
        )

        self._log_error(ptdu_error)

        if self._silent_mode:
            return

        msg = f"Could not export to:\n{path}\n\n"
        msg += f"Error: {error_msg}"

        messagebox.showerror(
            "Export Error",
            msg,
            parent=self._parent,
        )

    def handle_cache_error(
        self,
        error: Exception,
        operation: str = "access",
    ) -> None:
        """Handle cache operation error (non-critical).

        Args:
            error: Exception that occurred
            operation: Cache operation being performed
        """
        # Cache errors are non-critical, just log them
        error_msg = str(error)

        ptdu_error = PTDUError(
            message=f"Cache {operation} error: {error_msg}",
            severity=ErrorSeverity.WARNING,
            suggestion="Cache will be disabled for this session",
            recoverable=True,
        )

        self._log_error(ptdu_error)

        # Only show in non-silent mode and if parent exists
        if not self._silent_mode and self._parent is not None:
            # Don't show dialog for cache errors, just log
            pass

    def show_info(self, title: str, message: str) -> None:
        """Show info dialog.

        Args:
            title: Dialog title
            message: Message to display
        """
        if self._silent_mode:
            return

        messagebox.showinfo(
            title,
            message,
            parent=self._parent,
        )

    def show_warning(self, title: str, message: str) -> None:
        """Show warning dialog.

        Args:
            title: Dialog title
            message: Message to display
        """
        if self._silent_mode:
            return

        messagebox.showwarning(
            title,
            message,
            parent=self._parent,
        )

    def show_error(self, title: str, message: str) -> None:
        """Show error dialog.

        Args:
            title: Dialog title
            message: Message to display
        """
        if self._silent_mode:
            return

        messagebox.showerror(
            title,
            message,
            parent=self._parent,
        )

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Ask yes/no question.

        Args:
            title: Dialog title
            message: Question to ask

        Returns:
            True if yes, False if no
        """
        if self._silent_mode:
            return True

        return messagebox.askyesno(
            title,
            message,
            parent=self._parent,
        )

    def _log_error(self, error: PTDUError) -> None:
        """Log error to history.

        Args:
            error: Error to log
        """
        self._error_history.append(error)

        # Trim history if needed
        while len(self._error_history) > self._max_history:
            self._error_history.pop(0)

    def get_error_history(
        self,
        severity: Optional[ErrorSeverity] = None,
    ) -> list[PTDUError]:
        """Get error history.

        Args:
            severity: Filter by severity (None for all)

        Returns:
            List of errors
        """
        if severity is None:
            return self._error_history.copy()

        return [e for e in self._error_history if e.severity == severity]

    def clear_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()

    def get_error_count(self, severity: Optional[ErrorSeverity] = None) -> int:
        """Get count of errors.

        Args:
            severity: Filter by severity (None for all)

        Returns:
            Error count
        """
        if severity is None:
            return len(self._error_history)

        return sum(1 for e in self._error_history if e.severity == severity)


class PathValidator:
    """Utility for validating and handling paths."""

    # Maximum safe path length
    MAX_SAFE_PATH_LENGTH: int = 4000

    @classmethod
    def validate_path(cls, path: Path) -> tuple[bool, Optional[str]]:
        """Validate a path for operations.

        Args:
            path: Path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        path_str = str(path)

        # Check path length
        if len(path_str) > cls.MAX_SAFE_PATH_LENGTH:
            return (
                False,
                f"Path exceeds maximum length ({len(path_str)} > {cls.MAX_SAFE_PATH_LENGTH})",
            )

        # Check if path exists
        if not path.exists():
            return False, f"Path does not exist: {path}"

        # Check for null bytes
        if "\x00" in path_str:
            return False, "Path contains null bytes"

        return True, None

    @classmethod
    def sanitize_filename(cls, name: str) -> str:
        """Sanitize a filename for safe operations.

        Args:
            name: Filename to sanitize

        Returns:
            Sanitized filename
        """
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*\x00-\x1f'
        for char in unsafe_chars:
            name = name.replace(char, "_")

        # Limit length
        max_len = 255
        if len(name) > max_len:
            name = name[:max_len]

        return name

    @classmethod
    def get_path_display_name(cls, path: Path, max_length: int = 60) -> str:
        """Get display name for a path, truncated if necessary.

        Args:
            path: Path to display
            max_length: Maximum length

        Returns:
            Display string
        """
        path_str = str(path)

        if len(path_str) <= max_length:
            return path_str

        # Truncate middle
        prefix_len = max_length // 3
        suffix_len = max_length - prefix_len - 3

        return f"{path_str[:prefix_len]}...{path_str[-suffix_len:]}"


# Global error handler instance
_global_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance.

    Returns:
        ErrorHandler instance
    """
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def set_error_handler(handler: ErrorHandler) -> None:
    """Set global error handler.

    Args:
        handler: ErrorHandler to use
    """
    global _global_error_handler
    _global_error_handler = handler
