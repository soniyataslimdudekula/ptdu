"""Tests for scanner module."""

import os
import tempfile
from pathlib import Path

import pytest

from ptdu.scanner import Scanner, ScanResult


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_create_scan_result(self) -> None:
        """Test creating a ScanResult."""
        result = ScanResult(
            path=Path("/test/file.txt"),
            name="file.txt",
            size=1024,
            is_dir=False,
        )

        assert result.path == Path("/test/file.txt")
        assert result.name == "file.txt"
        assert result.size == 1024
        assert result.is_dir is False
        assert result.error is None

    def test_create_scan_result_with_error(self) -> None:
        """Test creating a ScanResult with error."""
        result = ScanResult(
            path=Path("/test"),
            name="test",
            size=0,
            is_dir=True,
            error="Permission denied",
        )

        assert result.error == "Permission denied"


class TestScannerInitialization:
    """Tests for Scanner initialization."""

    def test_default_initialization(self) -> None:
        """Test scanner with default settings."""
        scanner = Scanner()

        assert scanner.follow_symlinks is False
        assert len(scanner.skip_patterns) > 0
        assert "/proc" in scanner.skip_patterns
        assert ".git" in scanner.skip_patterns

    def test_custom_skip_patterns(self) -> None:
        """Test scanner with custom skip patterns."""
        patterns = (".custom", "temp")
        scanner = Scanner(skip_patterns=patterns)

        assert scanner.skip_patterns == patterns

    def test_follow_symlinks_enabled(self) -> None:
        """Test scanner with symlink following enabled."""
        scanner = Scanner(follow_symlinks=True)

        assert scanner.follow_symlinks is True


class TestScannerShouldSkip:
    """Tests for should_skip method."""

    def test_skip_absolute_pattern(self) -> None:
        """Test skipping absolute path patterns."""
        scanner = Scanner()

        assert scanner.should_skip(Path("/proc")) is True
        assert scanner.should_skip(Path("/proc/123")) is True
        assert scanner.should_skip(Path("/sys/devices")) is True

    def test_skip_name_pattern(self) -> None:
        """Test skipping by name pattern."""
        scanner = Scanner()

        assert scanner.should_skip(Path("/path/.git")) is True
        assert scanner.should_skip(Path("/path/__pycache__")) is True

    def test_do_not_skip_regular_path(self) -> None:
        """Test that regular paths are not skipped."""
        scanner = Scanner()

        assert scanner.should_skip(Path("/home/user")) is False
        assert scanner.should_skip(Path("/tmp/test.txt")) is False

    def test_custom_skip_pattern(self) -> None:
        """Test custom skip patterns."""
        scanner = Scanner(skip_patterns=("node_modules",))

        assert scanner.should_skip(Path("/project/node_modules")) is True
        assert scanner.should_skip(Path("/project/node_modules/package")) is True
        assert scanner.should_skip(Path("/project/src")) is False


class TestScannerScanDirectory:
    """Tests for scan_directory method."""

    def test_scan_empty_directory(self) -> None:
        """Test scanning an empty directory."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            results = scanner.scan_directory(Path(tmpdir))

            assert results == []

    def test_scan_directory_with_files(self) -> None:
        """Test scanning directory with files."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "file1.txt").write_text("content1")
            (Path(tmpdir) / "file2.txt").write_text("content2" * 100)

            results = scanner.scan_directory(Path(tmpdir))

            assert len(results) == 2

            names = {r.name for r in results}
            assert names == {"file1.txt", "file2.txt"}

            # Check sizes
            file1 = next(r for r in results if r.name == "file1.txt")
            file2 = next(r for r in results if r.name == "file2.txt")

            assert file1.size == 8  # "content1"
            assert file2.size == 800  # "content2" * 100
            assert file1.is_dir is False
            assert file2.is_dir is False

    def test_scan_directory_with_subdirectories(self) -> None:
        """Test scanning directory with subdirectories."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create subdirectory
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file.txt").write_text("content")

            results = scanner.scan_directory(Path(tmpdir))

            assert len(results) == 1

            subdir_result = results[0]
            assert subdir_result.name == "subdir"
            assert subdir_result.is_dir is True
            assert subdir_result.size == 0  # Directories have size 0 initially

    def test_scan_skips_patterns(self) -> None:
        """Test that scan skips pattern-matched entries."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create regular file and skipped directory
            (Path(tmpdir) / "file.txt").write_text("content")
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("config")

            results = scanner.scan_directory(Path(tmpdir))

            assert len(results) == 1
            assert results[0].name == "file.txt"

    def test_scan_nonexistent_directory(self) -> None:
        """Test scanning non-existent directory."""
        scanner = Scanner()

        results = scanner.scan_directory(Path("/nonexistent/path"))

        assert len(results) == 1
        assert results[0].error is not None
        assert (
            "not found" in results[0].error.lower()
            or "directory not found" in results[0].error.lower()
        )

    def test_progress_callback(self) -> None:
        """Test progress callback is called for each entry."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file1.txt").write_text("content1")
            (Path(tmpdir) / "file2.txt").write_text("content2")

            callback_results: list[ScanResult] = []

            def callback(result: ScanResult) -> None:
                callback_results.append(result)

            scanner.scan_directory(Path(tmpdir), progress_callback=callback)

            assert len(callback_results) == 2


class TestScannerProcessEntry:
    """Tests for _process_entry method."""

    def test_process_file_entry(self) -> None:
        """Test processing a file entry."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("test content")

            with os.scandir(tmpdir) as entries:
                entry = next(entries)
                result = scanner._process_entry(entry)

                assert result is not None
                assert result.name == "test.txt"
                assert result.size == 12  # "test content"
                assert result.is_dir is False

    def test_process_directory_entry(self) -> None:
        """Test processing a directory entry."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            with os.scandir(tmpdir) as entries:
                entry = next(entries)
                result = scanner._process_entry(entry)

                assert result is not None
                assert result.name == "subdir"
                assert result.is_dir is True
                assert result.size == 0

    def test_process_skipped_entry(self) -> None:
        """Test that skipped entries return None."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()

            with os.scandir(tmpdir) as entries:
                entry = next(entries)
                result = scanner._process_entry(entry)

                assert result is None

    def test_process_broken_symlink(self) -> None:
        """Test processing a broken symlink."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a broken symlink
            link_path = Path(tmpdir) / "broken_link"
            link_path.symlink_to("/nonexistent/path")

            with os.scandir(tmpdir) as entries:
                entry = next(entries)
                result = scanner._process_entry(entry)

                # Should return error result, not None
                assert result is not None
                assert result.error is not None or result.size == 0


class TestScannerScanRecursive:
    """Tests for scan_recursive method."""

    def test_scan_recursive_depth_0(self) -> None:
        """Test recursive scan with max_depth=0."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file.txt").write_text("content")

            results = scanner.scan_recursive(Path(tmpdir), max_depth=0)

            assert len(results) == 0

    def test_scan_recursive_depth_1(self) -> None:
        """Test recursive scan with max_depth=1."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file1.txt").write_text("content")
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file2.txt").write_text("content")

            results = scanner.scan_recursive(Path(tmpdir), max_depth=1)

            # Should only get top-level entries
            assert len(results) == 2
            names = {r.name for r in results}
            assert names == {"file1.txt", "subdir"}

    def test_scan_recursive_unlimited(self) -> None:
        """Test recursive scan with unlimited depth."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            (Path(tmpdir) / "file1.txt").write_text("content")
            subdir1 = Path(tmpdir) / "level1"
            subdir1.mkdir()
            (subdir1 / "file2.txt").write_text("content")
            subdir2 = subdir1 / "level2"
            subdir2.mkdir()
            (subdir2 / "file3.txt").write_text("content")

            results = scanner.scan_recursive(Path(tmpdir))

            # Should get all files and directories
            names = {r.name for r in results}
            assert "file1.txt" in names
            assert "file2.txt" in names
            assert "file3.txt" in names
            assert "level1" in names
            assert "level2" in names

    def test_scan_recursive_skips_patterns(self) -> None:
        """Test that recursive scan skips pattern-matched directories."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file1.txt").write_text("content")
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("config")

            results = scanner.scan_recursive(Path(tmpdir))

            names = {r.name for r in results}
            assert "file1.txt" in names
            assert ".git" not in names
            assert "config" not in names


class TestScannerGetDirectorySize:
    """Tests for get_directory_size method."""

    def test_get_directory_size_empty(self) -> None:
        """Test size of empty directory."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            size = scanner.get_directory_size(Path(tmpdir))

            assert size == 0

    def test_get_directory_size_with_files(self) -> None:
        """Test size calculation with files."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file1.txt").write_text("content1")  # 8 bytes
            (Path(tmpdir) / "file2.txt").write_text("content2" * 10)  # 80 bytes

            size = scanner.get_directory_size(Path(tmpdir))

            assert size == 88

    def test_get_directory_size_recursive(self) -> None:
        """Test recursive size calculation."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file1.txt").write_text("content1")  # 8 bytes
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file2.txt").write_text("content2")  # 8 bytes

            size = scanner.get_directory_size(Path(tmpdir))

            assert size == 16

    def test_get_directory_size_skips_patterns(self) -> None:
        """Test that size calculation skips pattern-matched directories."""
        scanner = Scanner()

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file1.txt").write_text("content1")  # 8 bytes
            git_dir = Path(tmpdir) / ".git"
            git_dir.mkdir()
            (git_dir / "config").write_text("large content" * 100)

            size = scanner.get_directory_size(Path(tmpdir))

            assert size == 8  # Only the regular file
