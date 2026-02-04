"""Treeview widget for displaying directory structure."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ptdu.fonts import FontManager
from ptdu.models import DirNode
from ptdu.utils import SizeCalculator


class DirectoryTreeview(ttk.Treeview):
    """Custom Treeview for displaying directory contents with size information."""

    # Column identifiers
    COL_NAME = "name"
    COL_SIZE = "size"
    COL_PERCENT = "percent"
    COL_SIZE_BAR = "size_bar"
    COL_ITEMS = "items"

    # Tag names for styling
    TAG_DIRECTORY = "directory"
    TAG_FILE = "file"
    TAG_HIDDEN = "hidden"
    TAG_LARGE_FILE = "large_file"
    TAG_MEDIUM_FILE = "medium_file"
    TAG_SELECTED = "selected"

    # Size bar characters
    SIZE_BAR_FULL = "█"
    SIZE_BAR_EMPTY = "░"
    SIZE_BAR_WIDTH = 10

    # Size thresholds
    LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB
    MEDIUM_FILE_THRESHOLD = 10 * 1024 * 1024  # 10MB

    def __init__(
        self, parent: tk.Widget, font_manager: Optional[FontManager] = None
    ) -> None:
        """Initialize the directory treeview.

        Args:
            parent: Parent widget
            font_manager: Optional font manager for styling
        """
        # Define columns
        columns = (self.COL_SIZE, self.COL_SIZE_BAR, self.COL_PERCENT, self.COL_ITEMS)

        super().__init__(
            parent,
            columns=columns,
            show="tree headings",
            selectmode="browse",
        )

        # Font manager
        self._font_manager: FontManager = (
            font_manager if font_manager is not None else FontManager()
        )

        # Node reference storage: iid -> DirNode
        self._node_map: dict[str, DirNode] = {}

        # Track current max size for percentage bars
        self._current_max_size: int = 0

        self._setup_style()
        self._setup_columns()
        self._setup_tags()

    def _setup_columns(self) -> None:
        """Configure column headings and widths."""
        # Tree column (Name) - displays the file/directory name with icon
        self.heading("#0", text="Name", anchor="w")
        self.column("#0", width=400, minwidth=200, stretch=True)

        # Size column
        self.heading(self.COL_SIZE, text="Size", anchor="e")
        self.column(self.COL_SIZE, width=90, minwidth=70, stretch=False, anchor="e")

        # Size bar column (visual representation)
        self.heading(self.COL_SIZE_BAR, text="", anchor="w")
        self.column(
            self.COL_SIZE_BAR, width=100, minwidth=80, stretch=False, anchor="w"
        )

        # Percent column
        self.heading(self.COL_PERCENT, text="Percent", anchor="e")
        self.column(self.COL_PERCENT, width=70, minwidth=60, stretch=False, anchor="e")

        # Items column
        self.heading(self.COL_ITEMS, text="Items", anchor="e")
        self.column(self.COL_ITEMS, width=60, minwidth=50, stretch=False, anchor="e")

    def _setup_tags(self) -> None:
        """Configure tag styles for different item types."""
        dir_font = self._font_manager.get_directory_font()
        file_font = self._font_manager.get_file_font()

        # Directory styling - blue text, bold
        self.tag_configure(
            self.TAG_DIRECTORY,
            foreground="#0066cc",
            font=dir_font,
        )

        # File styling - default text
        self.tag_configure(
            self.TAG_FILE,
            foreground="#000000",
            font=file_font,
        )

        # Hidden file/directory styling - gray text
        self.tag_configure(
            self.TAG_HIDDEN,
            foreground="#888888",
        )

        # Large files (>100MB) - red text
        self.tag_configure(
            self.TAG_LARGE_FILE,
            foreground="#cc0000",
        )

        # Medium files (10-100MB) - yellow/orange text
        self.tag_configure(
            self.TAG_MEDIUM_FILE,
            foreground="#cc6600",
        )

        # Selected item styling
        self.tag_configure(
            self.TAG_SELECTED,
            background="#d0e8ff",
        )

    def _setup_style(self) -> None:
        """Set up ttk style for treeview with proper row height."""
        style = ttk.Style()
        treeview_font = self._font_manager.get_treeview_font()

        # Calculate row height based on font metrics
        metrics = treeview_font.metrics()
        row_height = metrics["ascent"] + metrics["descent"] + 8

        # Configure treeview style with row height
        style.configure(
            "DirectoryTreeview.Treeview",
            rowheight=row_height,
            font=treeview_font,
        )
        style.configure(
            "DirectoryTreeview.Treeview.Heading",
            font=self._font_manager.get_heading_font(),
        )

        # Apply the custom style
        self.configure(style="DirectoryTreeview.Treeview")

    def _update_style(self) -> None:
        """Update ttk style after font size change."""
        self._setup_style()

    def _format_size_bar(self, size: int) -> str:
        """Format a visual size bar using Unicode blocks.

        Args:
            size: Size in bytes

        Returns:
            Visual bar string (e.g., "████░░░░░")
        """
        if self._current_max_size <= 0 or size <= 0:
            return self.SIZE_BAR_EMPTY * self.SIZE_BAR_WIDTH

        # Calculate filled portion
        ratio = size / self._current_max_size
        filled = int(ratio * self.SIZE_BAR_WIDTH)
        filled = max(0, min(filled, self.SIZE_BAR_WIDTH))  # Clamp to valid range

        empty = self.SIZE_BAR_WIDTH - filled
        return self.SIZE_BAR_FULL * filled + self.SIZE_BAR_EMPTY * empty

    def insert_node(
        self,
        parent_iid: str,
        node: DirNode,
    ) -> str:
        """Insert a DirNode into the treeview.

        Args:
            parent_iid: Parent item ID (empty string for root)
            node: The DirNode to insert

        Returns:
            The item ID (iid) of the inserted node
        """
        # Generate unique iid based on path
        iid = str(node.path)

        # Determine display name and icon
        display_name = node.name
        if node.is_dir:
            # Add folder indicator for collapsed directories
            if not node.is_expanded:
                display_name = f"📁 {node.name}"
            else:
                display_name = f"📂 {node.name}"
        else:
            display_name = f"📄 {node.name}"

        # Calculate percentage if we have a max size
        percent_str = ""
        size_bar = ""
        if self._current_max_size > 0 and node.size > 0:
            percent = SizeCalculator.calculate_percentage(
                node.size, self._current_max_size
            )
            percent_str = f"{percent:.0f}%"
            size_bar = self._format_size_bar(node.size)

        # Format values
        values = (
            SizeCalculator.format_size(node.size),
            size_bar,
            percent_str,
            str(node.get_item_count()) if node.is_dir else "",
        )

        # Determine tags
        tags = self._get_tags_for_node(node)

        # Insert the item
        try:
            self.insert(
                parent=parent_iid,
                index="end",
                iid=iid,
                text=display_name,
                values=values,
                tags=tags,
                open=node.is_expanded,
            )
        except tk.TclError:
            # Item already exists, update it
            self.item(
                iid, text=display_name, values=values, tags=tags, open=node.is_expanded
            )

        # Store node reference
        self._node_map[iid] = node

        return iid

    def _get_tags_for_node(self, node: DirNode) -> tuple[str, ...]:
        """Determine appropriate tags for a node based on its properties.

        Args:
            node: The DirNode to get tags for

        Returns:
            Tuple of tag names
        """
        tags: list[str] = []

        if node.is_dir:
            tags.append(self.TAG_DIRECTORY)
        else:
            tags.append(self.TAG_FILE)

            # Size-based coloring
            if node.size > self.LARGE_FILE_THRESHOLD:  # > 100MB
                tags.append(self.TAG_LARGE_FILE)
            elif node.size > self.MEDIUM_FILE_THRESHOLD:  # > 10MB
                tags.append(self.TAG_MEDIUM_FILE)

        # Hidden files/directories (start with .)
        if node.name.startswith("."):
            tags.append(self.TAG_HIDDEN)

        return tuple(tags)

    def get_node(self, iid: str) -> Optional[DirNode]:
        """Get the DirNode associated with an item ID.

        Args:
            iid: The item ID

        Returns:
            The DirNode or None if not found
        """
        return self._node_map.get(iid)

    def delete_node(self, iid: str) -> None:
        """Delete a node and remove from internal map.

        Args:
            iid: The item ID to delete
        """
        self.delete(iid)
        self._node_map.pop(iid, None)

    def clear(self) -> None:
        """Clear all items from the treeview."""
        for item in self.get_children():
            self.delete(item)
        self._node_map.clear()
        self._current_max_size = 0

    def update_node(self, iid: str) -> None:
        """Update the display values for a node.

        Args:
            iid: The item ID to update
        """
        node = self._node_map.get(iid)
        if node is None:
            return

        # Recalculate display values
        display_name = node.name
        if node.is_dir:
            if not node.is_expanded:
                display_name = f"📁 {node.name}"
            else:
                display_name = f"📂 {node.name}"
        else:
            display_name = f"📄 {node.name}"

        # Calculate percentage and size bar
        percent_str = ""
        size_bar = ""
        if self._current_max_size > 0 and node.size > 0:
            percent = SizeCalculator.calculate_percentage(
                node.size, self._current_max_size
            )
            percent_str = f"{percent:.0f}%"
            size_bar = self._format_size_bar(node.size)

        values = (
            SizeCalculator.format_size(node.size),
            size_bar,
            percent_str,
            str(node.get_item_count()) if node.is_dir else "",
        )

        tags = self._get_tags_for_node(node)

        self.item(
            iid, text=display_name, values=values, tags=tags, open=node.is_expanded
        )

    def set_max_size(self, max_size: int) -> None:
        """Set the maximum size for percentage calculations.

        Args:
            max_size: Maximum size in bytes
        """
        self._current_max_size = max_size

    def get_selected_node(self) -> Optional[DirNode]:
        """Get the currently selected DirNode.

        Returns:
            The selected DirNode or None
        """
        selection = self.selection()
        if not selection:
            return None
        return self._node_map.get(selection[0])

    def select_node(self, iid: str) -> None:
        """Select a node by its ID.

        Args:
            iid: The item ID to select
        """
        self.selection_set(iid)
        self.focus(iid)
        self.see(iid)

    def expand_node(self, iid: str) -> None:
        """Expand a node and update its display.

        Args:
            iid: The item ID to expand
        """
        node = self._node_map.get(iid)
        if node and node.is_dir:
            node.is_expanded = True
            self.item(iid, open=True)
            self.update_node(iid)

    def collapse_node(self, iid: str) -> None:
        """Collapse a node and update its display.

        Args:
            iid: The item ID to collapse
        """
        node = self._node_map.get(iid)
        if node and node.is_dir:
            node.is_expanded = False
            self.item(iid, open=False)
            self.update_node(iid)

    def set_font_manager(self, font_manager: FontManager) -> None:
        """Set a new font manager and update styling.

        Args:
            font_manager: New font manager to use
        """
        self._font_manager = font_manager
        self._setup_tags()
        self._update_style()

    def refresh_fonts(self) -> None:
        """Refresh all fonts after font size change."""
        self._setup_tags()
        self._update_style()
        # Force redraw to apply new fonts
        self.update()
