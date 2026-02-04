"""Tests for treeview module."""

import tkinter as tk
from collections.abc import Generator
from pathlib import Path
from tkinter import ttk

import pytest

from ptdu.models import DirNode
from ptdu.treeview import DirectoryTreeview


@pytest.fixture
def root_window() -> Generator[tk.Tk, None, None]:
    """Create a root window for testing."""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def treeview(root_window: tk.Tk) -> DirectoryTreeview:
    """Create a DirectoryTreeview instance for testing."""
    frame = ttk.Frame(root_window)
    tree = DirectoryTreeview(frame)
    return tree


@pytest.fixture
def sample_file_node() -> DirNode:
    """Create a sample file node."""
    return DirNode(
        path=Path("/home/user/file.txt"),
        name="file.txt",
        is_dir=False,
    )


@pytest.fixture
def sample_dir_node() -> DirNode:
    """Create a sample directory node."""
    return DirNode(
        path=Path("/home/user/docs"),
        name="docs",
        is_dir=True,
    )


class TestDirectoryTreeview:
    """Tests for DirectoryTreeview class."""

    def test_initialization(self, treeview: DirectoryTreeview) -> None:
        """Test treeview initialization."""
        assert treeview is not None
        assert treeview._current_max_size == 0
        assert treeview._node_map == {}

    def test_column_setup(self, treeview: DirectoryTreeview) -> None:
        """Test that columns are configured correctly."""
        columns = treeview["columns"]
        assert DirectoryTreeview.COL_SIZE in columns
        assert DirectoryTreeview.COL_PERCENT in columns
        assert DirectoryTreeview.COL_ITEMS in columns

    def test_tags_configured(self, treeview: DirectoryTreeview) -> None:
        """Test that tags are configured."""
        # Tags should be configured without errors
        treeview.tag_configure(DirectoryTreeview.TAG_DIRECTORY, foreground="blue")
        treeview.tag_configure(DirectoryTreeview.TAG_FILE, foreground="black")

    def test_insert_file_node(
        self, treeview: DirectoryTreeview, sample_file_node: DirNode
    ) -> None:
        """Test inserting a file node."""
        iid = treeview.insert_node("", sample_file_node)

        assert iid == str(sample_file_node.path)
        assert iid in treeview._node_map
        assert treeview._node_map[iid] == sample_file_node

    def test_insert_directory_node(
        self, treeview: DirectoryTreeview, sample_dir_node: DirNode
    ) -> None:
        """Test inserting a directory node."""
        iid = treeview.insert_node("", sample_dir_node)

        assert iid == str(sample_dir_node.path)
        assert treeview._node_map[iid] == sample_dir_node

    def test_insert_node_with_size(
        self, treeview: DirectoryTreeview, sample_file_node: DirNode
    ) -> None:
        """Test that node size is displayed correctly."""
        sample_file_node.set_size(1024)
        iid = treeview.insert_node("", sample_file_node)

        values = treeview.item(iid, "values")
        assert "1.0 KB" in values

    def test_get_node(
        self, treeview: DirectoryTreeview, sample_file_node: DirNode
    ) -> None:
        """Test retrieving a node by iid."""
        iid = treeview.insert_node("", sample_file_node)

        retrieved = treeview.get_node(iid)
        assert retrieved == sample_file_node

    def test_get_node_not_found(self, treeview: DirectoryTreeview) -> None:
        """Test retrieving a non-existent node."""
        result = treeview.get_node("nonexistent")
        assert result is None

    def test_delete_node(
        self, treeview: DirectoryTreeview, sample_file_node: DirNode
    ) -> None:
        """Test deleting a node."""
        iid = treeview.insert_node("", sample_file_node)

        treeview.delete_node(iid)

        assert iid not in treeview._node_map
        assert iid not in treeview.get_children()

    def test_clear(
        self, treeview: DirectoryTreeview, sample_file_node: DirNode
    ) -> None:
        """Test clearing all nodes."""
        treeview.insert_node("", sample_file_node)
        treeview.set_max_size(1000)

        treeview.clear()

        assert treeview._node_map == {}
        assert treeview._current_max_size == 0
        assert treeview.get_children() == ()

    def test_set_max_size(self, treeview: DirectoryTreeview) -> None:
        """Test setting max size for percentages."""
        treeview.set_max_size(1000000)
        assert treeview._current_max_size == 1000000

    def test_get_selected_node_none(self, treeview: DirectoryTreeview) -> None:
        """Test getting selected node when nothing selected."""
        result = treeview.get_selected_node()
        assert result is None

    def test_select_node(
        self, treeview: DirectoryTreeview, sample_file_node: DirNode
    ) -> None:
        """Test selecting a node."""
        iid = treeview.insert_node("", sample_file_node)

        treeview.select_node(iid)

        selection = treeview.selection()
        assert iid in selection

    def test_expand_node(
        self, treeview: DirectoryTreeview, sample_dir_node: DirNode
    ) -> None:
        """Test expanding a directory node."""
        iid = treeview.insert_node("", sample_dir_node)

        treeview.expand_node(iid)

        assert sample_dir_node.is_expanded is True
        assert treeview.item(iid, "open") == 1

    def test_collapse_node(
        self, treeview: DirectoryTreeview, sample_dir_node: DirNode
    ) -> None:
        """Test collapsing a directory node."""
        iid = treeview.insert_node("", sample_dir_node)
        sample_dir_node.is_expanded = True

        treeview.collapse_node(iid)

        assert sample_dir_node.is_expanded is False
        assert treeview.item(iid, "open") == 0

    def test_get_tags_for_file(self, treeview: DirectoryTreeview) -> None:
        """Test tag determination for regular file."""
        node = DirNode(path=Path("/file.txt"), name="file.txt", is_dir=False)
        tags = treeview._get_tags_for_node(node)

        assert DirectoryTreeview.TAG_FILE in tags

    def test_get_tags_for_directory(self, treeview: DirectoryTreeview) -> None:
        """Test tag determination for directory."""
        node = DirNode(path=Path("/dir"), name="dir", is_dir=True)
        tags = treeview._get_tags_for_node(node)

        assert DirectoryTreeview.TAG_DIRECTORY in tags

    def test_get_tags_for_hidden_file(self, treeview: DirectoryTreeview) -> None:
        """Test tag determination for hidden file."""
        node = DirNode(path=Path("/.hidden"), name=".hidden", is_dir=False)
        tags = treeview._get_tags_for_node(node)

        assert DirectoryTreeview.TAG_HIDDEN in tags

    def test_get_tags_for_large_file(self, treeview: DirectoryTreeview) -> None:
        """Test tag determination for large file (>100MB)."""
        node = DirNode(path=Path("/large.bin"), name="large.bin", is_dir=False)
        node.set_size(150 * 1024 * 1024)  # 150MB
        tags = treeview._get_tags_for_node(node)

        assert DirectoryTreeview.TAG_LARGE_FILE in tags

    def test_get_tags_for_medium_file(self, treeview: DirectoryTreeview) -> None:
        """Test tag determination for medium file (10-100MB)."""
        node = DirNode(path=Path("/medium.bin"), name="medium.bin", is_dir=False)
        node.set_size(50 * 1024 * 1024)  # 50MB
        tags = treeview._get_tags_for_node(node)

        assert DirectoryTreeview.TAG_MEDIUM_FILE in tags

    def test_update_node(
        self, treeview: DirectoryTreeview, sample_file_node: DirNode
    ) -> None:
        """Test updating a node's display values."""
        iid = treeview.insert_node("", sample_file_node)

        sample_file_node.set_size(2048)
        treeview.update_node(iid)

        values = treeview.item(iid, "values")
        assert "2.0 KB" in values

    def test_insert_duplicate_updates(
        self, treeview: DirectoryTreeview, sample_file_node: DirNode
    ) -> None:
        """Test that inserting duplicate iid updates existing item."""
        sample_file_node.set_size(1024)
        iid1 = treeview.insert_node("", sample_file_node)

        sample_file_node.set_size(2048)
        iid2 = treeview.insert_node("", sample_file_node)

        assert iid1 == iid2
        values = treeview.item(iid1, "values")
        assert "2.0 KB" in values
