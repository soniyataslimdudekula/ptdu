"""Directory scanning functionality for PTDU."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from ptdu.cache import ScanCache


@dataclass
class ScanResult:
    """Result of scanning a single file or directory entry."""

    path: Path
    name: str
    size: int
    is_dir: bool
    error: Optional[str] = None


class Scanner:
    """Directory scanner using os.scandir() for optimal performance."""

    # Default patterns to skip (system directories and common VCS)
    DEFAULT_SKIP_PATTERNS: tuple[str, ...] = (
        "/proc",
        "/sys",
        "/dev",
        "/run",
        "/boot",
        ".git",
        ".svn",
        ".hg",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".egg-info",
        ".tox",
        "node_modules",
        ".aider*",
    )

    def __init__(
        self,
        skip_patterns: Optional[tuple[str, ...]] = None,
        follow_symlinks: bool = False,
        show_hidden: bool = True,
        exclude_patterns: Optional[tuple[str, ...]] = None,
        cache: Optional[ScanCache] = None,
    ) -> None:
        """Initialize scanner with configuration.

        Args:
            skip_patterns: Tuple of path patterns to skip (uses DEFAULT_SKIP_PATTERNS if None)
            follow_symlinks: Whether to follow symbolic links
            show_hidden: Whether to show hidden files (dotfiles)
            exclude_patterns: Additional patterns to exclude from scans
            cache: Optional ScanCache for caching results
        """
        self.skip_patterns: tuple[str, ...] = (
            skip_patterns or self.DEFAULT_SKIP_PATTERNS
        )
        self.follow_symlinks: bool = follow_symlinks
        self._show_hidden: bool = show_hidden
        self._exclude_patterns: tuple[str, ...] = exclude_patterns or ()
        self._cache: Optional[ScanCache] = cache
        self._use_cache: bool = cache is not None

    def should_skip(self, path: Path) -> bool:
        """Check if a path should be skipped based on skip patterns.

        Args:
            path: Path to check

        Returns:
            True if path should be skipped
        """
        path_str = str(path)
        name = path.name

        # Check skip patterns
        for pattern in self.skip_patterns:
            # Check if path matches pattern at any level
            if pattern.startswith("/"):
                # Absolute path pattern - check if path starts with it
                if path_str.startswith(pattern):
                    return True
            else:
                # Relative/name pattern - check if any path component matches
                if name == pattern or pattern in path_str:
                    return True

        # Check exclude patterns
        for pattern in self._exclude_patterns:
            if pattern.startswith("/"):
                if path_str.startswith(pattern):
                    return True
            else:
                if name == pattern or pattern in path_str:
                    return True

        return False

    def set_exclude_patterns(self, patterns: tuple[str, ...]) -> None:
        """Set exclude patterns.

        Args:
            patterns: Patterns to exclude
        """
        self._exclude_patterns = patterns

    def add_exclude_pattern(self, pattern: str) -> None:
        """Add an exclude pattern.

        Args:
            pattern: Pattern to add
        """
        self._exclude_patterns = self._exclude_patterns + (pattern,)

    def set_cache(self, cache: Optional[ScanCache]) -> None:
        """Set cache for scan results.

        Args:
            cache: ScanCache instance or None
        """
        self._cache = cache
        self._use_cache = cache is not None

    def try_load_from_cache(self, path: Path) -> Optional[list[ScanResult]]:
        """Try to load scan results from cache.

        Args:
            path: Directory path

        Returns:
            List of ScanResult or None if not cached/invalid
        """
        if not self._use_cache or self._cache is None:
            return None

        try:
            entries = self._cache.get(path)
            if entries is None:
                return None

            return [
                ScanResult(
                    path=Path(e.path),
                    name=e.name,
                    size=e.size,
                    is_dir=e.is_dir,
                )
                for e in entries
            ]
        except Exception:
            return None

    def store_in_cache(self, path: Path, results: list[ScanResult]) -> None:
        """Store scan results in cache.

        Args:
            path: Directory path
            results: Scan results to store
        """
        if not self._use_cache or self._cache is None:
            return

        try:
            self._cache.store(path, results)
        except Exception:
            # Cache errors are non-critical
            pass

    def is_hidden(self, path: Path) -> bool:
        """Check if a path is a hidden file (starts with .).

        Args:
            path: Path to check

        Returns:
            True if path is hidden
        """
        return path.name.startswith(".")

    def set_show_hidden(self, show_hidden: bool) -> None:
        """Set whether to show hidden files.

        Args:
            show_hidden: True to show hidden files, False to hide them
        """
        self._show_hidden = show_hidden

    def should_show(self, path: Path) -> bool:
        """Check if a path should be shown based on filters.

        Args:
            path: Path to check

        Returns:
            True if path should be shown
        """
        if not self._show_hidden and self.is_hidden(path):
            return False
        return not self.should_skip(path)

    def scan_directory(
        self,
        path: Path,
        progress_callback: Optional[Callable[[ScanResult], None]] = None,
    ) -> list[ScanResult]:
        """Scan a directory and return results.

        Args:
            path: Directory path to scan
            progress_callback: Optional callback called for each entry found

        Returns:
            List of ScanResult objects
        """
        results: list[ScanResult] = []

        if self.should_skip(path) or not self.should_show(path):
            return results

        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    # Skip hidden files if not showing them
                    if not self._show_hidden and entry.name.startswith("."):
                        continue
                    try:
                        result = self._process_entry(entry)
                        if result is not None:
                            results.append(result)
                            if progress_callback is not None:
                                progress_callback(result)
                    except (OSError, PermissionError) as e:
                        # Log error but continue scanning
                        error_result = ScanResult(
                            path=Path(entry.path),
                            name=entry.name,
                            size=0,
                            is_dir=False,
                            error=str(e),
                        )
                        results.append(error_result)
                        if progress_callback is not None:
                            progress_callback(error_result)

        except PermissionError:
            # Cannot access directory
            results.append(
                ScanResult(
                    path=path,
                    name=path.name,
                    size=0,
                    is_dir=True,
                    error="Permission denied",
                )
            )
        except FileNotFoundError:
            # Directory was deleted during scan
            results.append(
                ScanResult(
                    path=path,
                    name=path.name,
                    size=0,
                    is_dir=True,
                    error="Directory not found",
                )
            )
        except OSError as e:
            # Other OS errors
            results.append(
                ScanResult(
                    path=path,
                    name=path.name,
                    size=0,
                    is_dir=True,
                    error=str(e),
                )
            )

        return results

    def _process_entry(self, entry: os.DirEntry[str]) -> Optional[ScanResult]:
        """Process a single directory entry.

        Args:
            entry: os.DirEntry object

        Returns:
            ScanResult or None if entry should be skipped
        """
        path = Path(entry.path)

        # Check skip patterns
        if self.should_skip(path):
            return None

        # Check hidden files
        if not self._show_hidden and entry.name.startswith("."):
            return None

        try:
            # Get entry info - use stat() for symlinks if not following
            if entry.is_symlink() and not self.follow_symlinks:
                return ScanResult(
                    path=path,
                    name=entry.name,
                    size=0,
                    is_dir=False,  # Symlinks treated as files for size purposes
                )

            # Use entry.stat() which is cached and faster than Path.stat()
            stat_info = entry.stat(follow_symlinks=self.follow_symlinks)

            # Check if it's a directory
            is_dir = entry.is_dir(follow_symlinks=self.follow_symlinks)

            # For directories, size is calculated from children (will be 0 here)
            # For files, use the actual file size
            size = 0 if is_dir else stat_info.st_size

            return ScanResult(
                path=path,
                name=entry.name,
                size=size,
                is_dir=is_dir,
            )

        except (OSError, PermissionError):
            # Broken symlink or permission issue
            return ScanResult(
                path=path,
                name=entry.name,
                size=0,
                is_dir=False,
                error="Cannot access entry",
            )

    def scan_recursive(
        self,
        path: Path,
        max_depth: Optional[int] = None,
        current_depth: int = 0,
        progress_callback: Optional[Callable[[ScanResult], None]] = None,
    ) -> list[ScanResult]:
        """Recursively scan a directory.

        Args:
            path: Directory path to scan
            max_depth: Maximum recursion depth (None for unlimited)
            current_depth: Current depth (used internally)
            progress_callback: Optional callback for progress updates

        Returns:
            List of all ScanResult objects
        """
        if max_depth is not None and current_depth >= max_depth:
            return []

        if self.should_skip(path):
            return []

        results = self.scan_directory(path, progress_callback)

        # Recursively scan subdirectories
        subdirs = [r for r in results if r.is_dir and r.error is None]
        for subdir in subdirs:
            sub_results = self.scan_recursive(
                subdir.path,
                max_depth=max_depth,
                current_depth=current_depth + 1,
                progress_callback=progress_callback,
            )
            results.extend(sub_results)

        return results

    def get_directory_size(self, path: Path) -> int:
        """Calculate total size of a directory recursively.

        Args:
            path: Directory path

        Returns:
            Total size in bytes
        """
        if self.should_skip(path):
            return 0

        total_size = 0

        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink() and not self.follow_symlinks:
                            continue

                        if entry.is_dir(follow_symlinks=self.follow_symlinks):
                            total_size += self.get_directory_size(Path(entry.path))
                        else:
                            stat_info = entry.stat(follow_symlinks=self.follow_symlinks)
                            total_size += stat_info.st_size
                    except (OSError, PermissionError):
                        # Skip inaccessible entries
                        continue

        except (OSError, PermissionError):
            # Cannot access directory
            pass

        return total_size


class MemoryMonitor:
    """Monitors memory usage and provides warnings."""

    def __init__(self, warning_threshold_mb: int = 500) -> None:
        """Initialize memory monitor.

        Args:
            warning_threshold_mb: Memory threshold for warnings (MB)
        """
        self._warning_threshold: int = warning_threshold_mb * 1024 * 1024
        self._critical_threshold: int = warning_threshold_mb * 2 * 1024 * 1024

    def get_memory_usage(self) -> dict[str, int]:
        """Get current memory usage.

        Returns:
            Dictionary with memory stats in bytes
        """
        try:
            import resource

            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "rss": usage.ru_maxrss * 1024,  # Convert KB to bytes
                "vms": 0,  # Not available on all platforms
            }
        except ImportError:
            # Fallback for non-Unix systems
            return {"rss": 0, "vms": 0}

    def check_memory(self) -> tuple[bool, bool]:
        """Check memory usage against thresholds.

        Returns:
            Tuple of (warning_triggered, critical_triggered)
        """
        usage = self.get_memory_usage()
        rss = usage.get("rss", 0)

        warning = rss > self._warning_threshold
        critical = rss > self._critical_threshold

        return warning, critical


def get_system_info() -> dict[str, str | int]:
    """Get system information for debugging.

    Returns:
        Dictionary with system info
    """
    info: dict[str, str | int] = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "processor": platform.processor(),
        "machine": platform.machine(),
    }

    try:
        import resource

        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        info["max_open_files_soft"] = soft
        info["max_open_files_hard"] = hard
    except (ImportError, OSError):
        pass

    return info
