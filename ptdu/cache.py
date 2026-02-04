"""SQLite caching for directory scan results."""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ptdu.models import DirNode

from ptdu.scanner import ScanResult


@dataclass
class CacheEntry:
    """A cached directory entry."""

    path: str
    name: str
    size: int
    is_dir: bool
    mtime: float
    scan_time: float


class ScanCache:
    """SQLite-based cache for directory scan results."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize the scan cache.

        Args:
            db_path: Path to SQLite database (default: ~/.cache/ptdu/cache.db)
        """
        if db_path is None:
            cache_dir = Path.home() / ".cache" / "ptdu"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = cache_dir / "cache.db"

        self._db_path: Path = db_path
        self._lock: threading.Lock = threading.Lock()
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(self._db_path))
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scan_cache (
                        path TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        size INTEGER NOT NULL,
                        is_dir INTEGER NOT NULL,
                        mtime REAL NOT NULL,
                        scan_time REAL NOT NULL,
                        parent_path TEXT,
                        FOREIGN KEY (parent_path) REFERENCES scan_cache(path)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_parent_path
                    ON scan_cache(parent_path)
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_scan_time
                    ON scan_cache(scan_time)
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def _get_mtime(self, path: Path) -> float:
        """Get modification time of a path.

        Args:
            path: Path to check

        Returns:
            Modification time as float, or 0 if unavailable
        """
        try:
            return os.path.getmtime(path)
        except (OSError, PermissionError):
            return 0.0

    def is_valid(self, path: Path) -> bool:
        """Check if cached data is still valid (mtime unchanged).

        Args:
            path: Directory path to check

        Returns:
            True if cache is valid, False otherwise
        """
        path_str = str(path.resolve())
        current_mtime = self._get_mtime(path)

        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT mtime FROM scan_cache WHERE path = ?",
                (path_str,),
            )
            row = cursor.fetchone()

            if row is None:
                return False

            cached_mtime = row["mtime"]
            return cached_mtime == current_mtime

    def get(self, path: Path) -> Optional[list[CacheEntry]]:
        """Get cached entries for a directory.

        Args:
            path: Directory path

        Returns:
            List of cached entries or None if not cached/invalid
        """
        path_str = str(path.resolve())

        if not self.is_valid(path):
            return None

        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT path, name, size, is_dir, mtime, scan_time "
                "FROM scan_cache WHERE parent_path = ?",
                (path_str,),
            )
            rows = cursor.fetchall()

            if not rows:
                return None

            return [
                CacheEntry(
                    path=row["path"],
                    name=row["name"],
                    size=row["size"],
                    is_dir=bool(row["is_dir"]),
                    mtime=row["mtime"],
                    scan_time=row["scan_time"],
                )
                for row in rows
            ]

    def get_recursive(self, path: Path) -> Optional[list[CacheEntry]]:
        """Get all cached entries recursively for a directory.

        Args:
            path: Directory path

        Returns:
            List of cached entries or None if root not cached/invalid
        """
        path_str = str(path.resolve())

        if not self.is_valid(path):
            return None

        with self._lock:
            conn = self._get_connection()
            # Get all entries where path starts with the given path
            cursor = conn.execute(
                "SELECT path, name, size, is_dir, mtime, scan_time "
                "FROM scan_cache WHERE path LIKE ?",
                (f"{path_str}%",),
            )
            rows = cursor.fetchall()

            if not rows:
                return None

            return [
                CacheEntry(
                    path=row["path"],
                    name=row["name"],
                    size=row["size"],
                    is_dir=bool(row["is_dir"]),
                    mtime=row["mtime"],
                    scan_time=row["scan_time"],
                )
                for row in rows
            ]

    def store(
        self,
        parent_path: Path,
        results: list[ScanResult],
    ) -> None:
        """Store scan results in cache.

        Args:
            parent_path: Parent directory path
            results: Scan results to cache
        """
        parent_str = str(parent_path.resolve())
        parent_mtime = self._get_mtime(parent_path)
        scan_time = time.time()

        with self._lock:
            conn = self._get_connection()
            try:
                # Store parent entry
                conn.execute(
                    """
                    INSERT OR REPLACE INTO scan_cache
                    (path, name, size, is_dir, mtime, scan_time, parent_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        parent_str,
                        parent_path.name,
                        0,
                        1,
                        parent_mtime,
                        scan_time,
                        str(parent_path.parent.resolve())
                        if parent_path.parent != parent_path
                        else None,
                    ),
                )

                # Store child entries
                for result in results:
                    path_str = str(result.path.resolve())
                    entry_mtime = (
                        parent_mtime if result.is_dir else self._get_mtime(result.path)
                    )

                    conn.execute(
                        """
                        INSERT OR REPLACE INTO scan_cache
                        (path, name, size, is_dir, mtime, scan_time, parent_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            path_str,
                            result.name,
                            result.size,
                            1 if result.is_dir else 0,
                            entry_mtime,
                            scan_time,
                            parent_str,
                        ),
                    )

                conn.commit()
            except sqlite3.Error:
                # If cache storage fails, continue without caching
                pass

    def store_entry(self, parent_path: Path, result: ScanResult) -> None:
        """Store a single scan result in cache.

        Args:
            parent_path: Parent directory path
            result: Scan result to cache
        """
        parent_str = str(parent_path.resolve())
        parent_mtime = self._get_mtime(parent_path)
        scan_time = time.time()
        path_str = str(result.path.resolve())
        entry_mtime = parent_mtime if result.is_dir else self._get_mtime(result.path)

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO scan_cache
                    (path, name, size, is_dir, mtime, scan_time, parent_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        path_str,
                        result.name,
                        result.size,
                        1 if result.is_dir else 0,
                        entry_mtime,
                        scan_time,
                        parent_str,
                    ),
                )
                conn.commit()
            except sqlite3.Error:
                pass

    def invalidate(self, path: Path) -> None:
        """Invalidate cache for a path and its children.

        Args:
            path: Path to invalidate
        """
        path_str = str(path.resolve())

        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    "DELETE FROM scan_cache WHERE path LIKE ?",
                    (f"{path_str}%",),
                )
                conn.commit()
            except sqlite3.Error:
                pass

    def clear(self) -> None:
        """Clear all cached data."""
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("DELETE FROM scan_cache")
                conn.commit()
            except sqlite3.Error:
                pass

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            conn = self._get_connection()
            try:
                cursor = conn.execute("SELECT COUNT(*) as count FROM scan_cache")
                count = cursor.fetchone()["count"]

                cursor = conn.execute(
                    "SELECT MAX(scan_time) as last_scan FROM scan_cache"
                )
                row = cursor.fetchone()
                last_scan = row["last_scan"] if row else 0.0

                return {
                    "entry_count": count,
                    "last_scan": last_scan,
                }
            except sqlite3.Error:
                return {
                    "entry_count": 0,
                    "last_scan": 0.0,
                }

    def close(self) -> None:
        """Close database connections."""
        with self._lock:
            if hasattr(self._local, "connection") and self._local.connection:
                self._local.connection.close()
                self._local.connection = None
