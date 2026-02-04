"""Performance optimizations for large directory handling."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from ptdu.models import DirNode


@dataclass
class VirtualRange:
    """Represents a visible range for virtual scrolling."""

    start: int
    end: int
    total: int


class VirtualScroller:
    """Manages virtual scrolling for large directories."""

    # Default number of items to render
    DEFAULT_WINDOW_SIZE: int = 100
    # Buffer size for smooth scrolling
    BUFFER_SIZE: int = 20

    def __init__(
        self, total_items: int = 0, window_size: int = DEFAULT_WINDOW_SIZE
    ) -> None:
        """Initialize virtual scroller.

        Args:
            total_items: Total number of items
            window_size: Number of items to render at once
        """
        self._total: int = total_items
        self._window_size: int = window_size
        self._current_start: int = 0

    def set_total(self, total: int) -> None:
        """Update total item count.

        Args:
            total: New total number of items
        """
        self._total = total
        self._clamp_start()

    def get_visible_range(self) -> VirtualRange:
        """Get the currently visible range.

        Returns:
            VirtualRange with start, end, and total
        """
        end = min(self._current_start + self._window_size, self._total)
        return VirtualRange(
            start=self._current_start,
            end=end,
            total=self._total,
        )

    def scroll_to(self, position: int) -> VirtualRange:
        """Scroll to a specific position.

        Args:
            position: Target position (0-based)

        Returns:
            New visible range
        """
        self._current_start = max(0, min(position, self._total - 1))
        self._clamp_start()
        return self.get_visible_range()

    def scroll_down(self, amount: int = 1) -> VirtualRange:
        """Scroll down by amount.

        Args:
            amount: Number of items to scroll

        Returns:
            New visible range
        """
        self._current_start += amount
        self._clamp_start()
        return self.get_visible_range()

    def scroll_up(self, amount: int = 1) -> VirtualRange:
        """Scroll up by amount.

        Args:
            amount: Number of items to scroll

        Returns:
            New visible range
        """
        self._current_start -= amount
        self._clamp_start()
        return self.get_visible_range()

    def page_down(self) -> VirtualRange:
        """Scroll down by one page.

        Returns:
            New visible range
        """
        return self.scroll_down(self._window_size)

    def page_up(self) -> VirtualRange:
        """Scroll up by one page.

        Returns:
            New visible range
        """
        return self.scroll_up(self._window_size)

    def _clamp_start(self) -> None:
        """Clamp start position to valid range."""
        max_start = max(0, self._total - self._window_size)
        self._current_start = max(0, min(self._current_start, max_start))

    def is_visible(self, index: int) -> bool:
        """Check if an index is currently visible.

        Args:
            index: Item index to check

        Returns:
            True if visible
        """
        visible = self.get_visible_range()
        return visible.start <= index < visible.end

    def get_item_index_at(self, y_position: int, item_height: int) -> int:
        """Get item index at a Y position.

        Args:
            y_position: Y coordinate
            item_height: Height of each item in pixels

        Returns:
            Item index
        """
        return self._current_start + (y_position // item_height)


class MemoryOptimizer:
    """Optimizes memory usage for large directory trees."""

    # Maximum children to keep in memory per directory
    MAX_CACHED_CHILDREN: int = 1000
    # Maximum depth for initial scan
    MAX_INITIAL_DEPTH: int = 3

    def __init__(self) -> None:
        """Initialize memory optimizer."""
        self._unloaded_nodes: set[str] = set()
        self._max_depth_reached: int = 0

    def should_unload_children(self, node: DirNode) -> bool:
        """Check if a node's children should be unloaded.

        Args:
            node: Directory node to check

        Returns:
            True if children should be unloaded
        """
        if not node.is_dir:
            return False

        # Unload if too many children
        if len(node.children) > self.MAX_CACHED_CHILDREN:
            return True

        return False

    def unload_children(self, node: DirNode) -> list[str]:
        """Unload children from memory, returning names of unloaded children.

        Args:
            node: Directory node to unload

        Returns:
            List of unloaded child names
        """
        if not node.is_dir:
            return []

        unloaded: list[str] = []

        # Keep track of unloaded nodes
        for name, child in node.children.items():
            self._unloaded_nodes.add(str(child.path))
            unloaded.append(name)

        # Clear children but keep size info
        node.children.clear()
        node._is_loaded = False

        return unloaded

    def reload_children(
        self,
        node: DirNode,
        loader: Callable[[], list[DirNode]],
    ) -> None:
        """Reload children using a loader function.

        Args:
            node: Directory node to reload
            loader: Function that returns list of child nodes
        """
        if not node.is_dir:
            return

        children = loader()
        for child in children:
            node.add_child(child)

        node._is_loaded = True
        self._unloaded_nodes.discard(str(node.path))

    def get_initial_scan_depth(self, estimated_total_items: int) -> int:
        """Get recommended initial scan depth based on estimated size.

        Args:
            estimated_total_items: Estimated number of items

        Returns:
            Recommended scan depth
        """
        if estimated_total_items > 100000:
            return 2
        elif estimated_total_items > 10000:
            return 3
        else:
            return self.MAX_INITIAL_DEPTH

    def limit_recursion_depth(
        self, current_depth: int, max_depth: Optional[int]
    ) -> int:
        """Calculate effective max depth with limits.

        Args:
            current_depth: Current recursion depth
            max_depth: Requested max depth (None for unlimited)

        Returns:
            Effective max depth
        """
        if max_depth is None:
            # Apply safety limit for unlimited scans
            return current_depth + 10

        return max_depth


class LargeDirectoryHandler:
    """Handles special cases for very large directories."""

    # Threshold for considering a directory "large"
    LARGE_DIR_THRESHOLD: int = 10000

    def __init__(self) -> None:
        """Initialize large directory handler."""
        self._large_directories: set[str] = set()
        self._item_counts: dict[str, int] = {}

    def register_directory(self, path: str, item_count: int) -> None:
        """Register a directory with its item count.

        Args:
            path: Directory path
            item_count: Number of items
        """
        self._item_counts[path] = item_count

        if item_count > self.LARGE_DIR_THRESHOLD:
            self._large_directories.add(path)

    def is_large_directory(self, path: str) -> bool:
        """Check if a directory is considered large.

        Args:
            path: Directory path

        Returns:
            True if large
        """
        return path in self._large_directories

    def get_item_count(self, path: str) -> int:
        """Get cached item count for a directory.

        Args:
            path: Directory path

        Returns:
            Item count or 0
        """
        return self._item_counts.get(path, 0)

    def get_memory_usage_estimate(self) -> dict[str, int]:
        """Estimate current memory usage.

        Returns:
            Dictionary with memory stats in bytes
        """
        # Rough estimates
        node_overhead = sys.getsizeof(object()) + 200  # Base node size
        total_nodes = sum(self._item_counts.values())

        return {
            "estimated_bytes": total_nodes * node_overhead,
            "total_nodes": total_nodes,
            "large_directories": len(self._large_directories),
        }


def estimate_directory_size(path: str) -> int:
    """Quickly estimate number of items in a directory.

    Args:
        path: Directory path

    Returns:
        Estimated item count
    """
    import os
    from pathlib import Path

    count = 0
    try:
        # Quick scan - only first level
        with os.scandir(path) as entries:
            for entry in entries:
                count += 1
                # Limit quick scan
                if count >= 1000:
                    return 1000
    except (OSError, PermissionError):
        pass

    return count
