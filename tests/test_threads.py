"""Tests for threads module."""

from pathlib import Path
from queue import Queue
from typing import cast

import pytest

from ptdu.models import DirNode
from ptdu.scanner import Scanner, ScanResult
from ptdu.threads import (
    ScanComplete,
    ScanError,
    ScanMessage,
    ScanProgress,
    ScanThread,
    ScanThreadManager,
)


class TestScanProgress:
    """Tests for ScanProgress dataclass."""

    def test_create_scan_progress(self) -> None:
        """Test creating a ScanProgress."""
        progress = ScanProgress(
            current_path=Path("/test"),
            items_scanned=5,
            total_items=10,
        )

        assert progress.current_path == Path("/test")
        assert progress.items_scanned == 5
        assert progress.total_items == 10


class TestScanComplete:
    """Tests for ScanComplete dataclass."""

    def test_create_scan_complete(self) -> None:
        """Test creating a ScanComplete."""
        results = [
            ScanResult(
                path=Path("/test/file.txt"), name="file.txt", size=100, is_dir=False
            )
        ]
        complete = ScanComplete(
            path=Path("/test"),
            results=results,
            total_size=100,
        )

        assert complete.path == Path("/test")
        assert complete.results == results
        assert complete.total_size == 100


class TestScanError:
    """Tests for ScanError dataclass."""

    def test_create_scan_error(self) -> None:
        """Test creating a ScanError."""
        error = ScanError(
            path=Path("/test"),
            error_message="Permission denied",
        )

        assert error.path == Path("/test")
        assert error.error_message == "Permission denied"


class TestScanThread:
    """Tests for ScanThread class."""

    def test_thread_initialization(self) -> None:
        """Test ScanThread initialization."""
        queue: Queue[ScanMessage] = Queue()
        scanner = Scanner()
        path = Path("/tmp")

        thread = ScanThread(
            path=path,
            scanner=scanner,
            message_queue=queue,
        )

        assert thread.path == path
        assert thread.scanner == scanner
        assert thread.message_queue == queue
        assert thread.parent_node is None
        assert thread.is_stopped() is False

    def test_thread_with_parent_node(self) -> None:
        """Test ScanThread with parent node."""
        queue: Queue[ScanMessage] = Queue()
        scanner = Scanner()
        parent = DirNode(path=Path("/parent"), name="parent", is_dir=True)

        thread = ScanThread(
            path=Path("/parent/child"),
            scanner=scanner,
            message_queue=queue,
            parent_node=parent,
        )

        assert thread.parent_node == parent

    def test_stop_request(self) -> None:
        """Test stop request sets stop event."""
        queue: Queue[ScanMessage] = Queue()
        scanner = Scanner()

        thread = ScanThread(
            path=Path("/tmp"),
            scanner=scanner,
            message_queue=queue,
        )

        assert thread.is_stopped() is False
        thread.stop()
        assert thread.is_stopped() is True


class TestScanThreadManager:
    """Tests for ScanThreadManager class."""

    def test_manager_initialization(self) -> None:
        """Test ScanThreadManager initialization."""
        from ptdu.threads import ScanThreadManager

        manager = ScanThreadManager()

        # Just verify it was created
        assert manager is not None
