"""Threading components for background directory scanning."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Callable, Optional

from ptdu.models import DirNode
from ptdu.scanner import Scanner, ScanResult


@dataclass
class ScanProgress:
    """Progress update from a scan operation."""

    current_path: Path
    items_scanned: int
    total_items: Optional[int] = None


@dataclass
class ScanEntry:
    """Single entry discovered during scan (for real-time updates)."""

    result: ScanResult


@dataclass
class ScanComplete:
    """Scan completion notification."""

    path: Path
    results: list[ScanResult]
    total_size: int


@dataclass
class ScanError:
    """Scan error notification."""

    path: Path
    error_message: str


# Union type for scan messages
ScanMessage = ScanProgress | ScanEntry | ScanComplete | ScanError


class ScanThread(threading.Thread):
    """Background thread for directory scanning."""

    def __init__(
        self,
        path: Path,
        scanner: Scanner,
        message_queue: Queue[ScanMessage],
        parent_node: Optional[DirNode] = None,
    ) -> None:
        """Initialize the scan thread.

        Args:
            path: Directory path to scan
            scanner: Scanner instance to use
            message_queue: Queue for sending progress/results back to main thread
            parent_node: Optional parent DirNode for tree structure
        """
        super().__init__(daemon=True)
        self.path: Path = path
        self.scanner: Scanner = scanner
        self.message_queue: Queue[ScanMessage] = message_queue
        self.parent_node: Optional[DirNode] = parent_node
        self._stop_event: threading.Event = threading.Event()
        self._items_scanned: int = 0
        self._results: list[ScanResult] = []

    def run(self) -> None:
        """Execute the scan operation in background."""
        try:
            if self._stop_event.is_set():
                return

            # Send initial progress
            self._send_progress()

            # Define progress callback - send entries in real-time
            def on_entry_scanned(result: ScanResult) -> None:
                if self._stop_event.is_set():
                    return
                self._items_scanned += 1
                self._results.append(result)
                # Send entry immediately for real-time display
                self.message_queue.put(ScanEntry(result=result))
                self._send_progress()

            # Perform recursive scan (like ncdu)
            results = self.scanner.scan_recursive(
                self.path,
                progress_callback=on_entry_scanned,
            )

            if self._stop_event.is_set():
                return

            # Calculate total size (all files recursively)
            total_size = sum(r.size for r in results if not r.is_dir)

            # Send completion message
            self.message_queue.put(
                ScanComplete(
                    path=self.path,
                    results=results,
                    total_size=total_size,
                )
            )

        except Exception as e:
            # Send error message
            self.message_queue.put(
                ScanError(
                    path=self.path,
                    error_message=str(e),
                )
            )

    def _send_progress(self) -> None:
        """Send a progress update to the main thread."""
        self.message_queue.put(
            ScanProgress(
                current_path=self.path,
                items_scanned=self._items_scanned,
            )
        )

    def stop(self) -> None:
        """Request the scan to stop."""
        self._stop_event.set()

    def is_stopped(self) -> bool:
        """Check if stop has been requested.

        Returns:
            True if stop has been requested
        """
        return self._stop_event.is_set()


class ScanThreadManager:
    """Manages active scan threads and coordinates UI updates."""

    def __init__(self) -> None:
        """Initialize the scan manager."""
        self._active_threads: dict[Path, ScanThread] = {}
        self._message_queue: Queue[ScanMessage] = Queue()
        self._lock: threading.Lock = threading.Lock()

    def start_scan(
        self,
        path: Path,
        scanner: Scanner,
        parent_node: Optional[DirNode] = None,
    ) -> ScanThread:
        """Start a new scan thread.

        Args:
            path: Directory path to scan
            scanner: Scanner instance
            parent_node: Optional parent node

        Returns:
            The started ScanThread
        """
        with self._lock:
            # Cancel any existing scan for this path
            if path in self._active_threads:
                self._active_threads[path].stop()

            # Create and start new thread
            thread = ScanThread(
                path=path,
                scanner=scanner,
                message_queue=self._message_queue,
                parent_node=parent_node,
            )
            self._active_threads[path] = thread
            thread.start()
            return thread

    def get_messages(self) -> list[ScanMessage]:
        """Retrieve all pending messages from the queue.

        Returns:
            List of messages (non-blocking)
        """
        messages: list[ScanMessage] = []
        while not self._message_queue.empty():
            try:
                msg = self._message_queue.get_nowait()
                messages.append(msg)
            except Exception:
                break
        return messages

    def stop_scan(self, path: Path) -> None:
        """Stop a specific scan.

        Args:
            path: Path of the scan to stop
        """
        with self._lock:
            if path in self._active_threads:
                self._active_threads[path].stop()

    def stop_all(self) -> None:
        """Stop all active scans."""
        with self._lock:
            for thread in self._active_threads.values():
                thread.stop()

    def cleanup_finished(self) -> None:
        """Remove finished threads from tracking."""
        finished = [
            path
            for path, thread in self._active_threads.items()
            if not thread.is_alive()
        ]
        for path in finished:
            del self._active_threads[path]

    def has_active_scans(self) -> bool:
        """Check if any scans are currently running.

        Returns:
            True if active scans exist
        """
        with self._lock:
            self.cleanup_finished()
            return len(self._active_threads) > 0

    def get_active_paths(self) -> list[Path]:
        """Get list of paths currently being scanned.

        Returns:
            List of paths
        """
        with self._lock:
            self.cleanup_finished()
            return list(self._active_threads.keys())
