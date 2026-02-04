# PTDU Developer Documentation

## Architecture Overview

PTDU follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                         UI Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  MainWindow  │  │DirectoryTree │  │   Status Bar     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Threading Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ ScanThread   │  │ScanThreadMgr │  │  Message Queue   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Business Logic                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Scanner    │  │   DirNode    │  │  SizeCalculator  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Performance & Caching                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  ScanCache   │  │VirtualScroller│  │MemoryOptimizer   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### Core Modules

#### `models.py`
- **DirNode**: Tree node representing files/directories
- Maintains parent-child relationships
- Tracks expansion state and loading status

#### `scanner.py`
- **Scanner**: Filesystem scanning with `os.scandir()`
- **ScanResult**: Dataclass for scan entries
- **MemoryMonitor**: Memory usage tracking
- Pattern-based filtering (skip/exclude)

#### `threads.py`
- **ScanThread**: Background scanning thread
- **ScanThreadManager**: Thread lifecycle management
- Message passing via `Queue`

#### `ui.py`
- **MainWindow**: Main application window
- Event handling and keyboard shortcuts
- Integration with all other components

#### `treeview.py`
- **DirectoryTreeview**: Custom ttk.Treeview
- Size bars, color coding, icon display
- Node mapping for tree operations

### Supporting Modules

#### `cache.py`
- **ScanCache**: SQLite-based result caching
- Automatic invalidation via mtime
- Thread-safe operations

#### `performance.py`
- **VirtualScroller**: Efficient large list handling
- **MemoryOptimizer**: Memory usage optimization
- **LargeDirectoryHandler**: Special handling for huge dirs

#### `errors.py`
- **ErrorHandler**: Centralized error handling
- **PathValidator**: Path validation utilities
- User-friendly error dialogs

#### `fonts.py`
- **FontManager**: OS-aware font detection
- Dynamic font size adjustment
- Cross-platform font selection

#### `utils.py`
- **SizeCalculator**: Human-readable formatting
- Percentage calculations

## Data Flow

### Scanning Process

1. **Initiation**: `MainWindow.start_background_scan()`
2. **Thread Creation**: `ScanThreadManager.start_scan()`
3. **Scanning**: `Scanner.scan_recursive()` with callbacks
4. **Message Passing**: Results queued via `ScanMessage`
5. **UI Update**: `MainWindow._check_messages()` processes queue
6. **Tree Building**: `MainWindow._handle_scan_complete()` builds tree

### Caching Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Start   │────▶│  Check   │────▶│  Cache   │
│   Scan   │     │  Cache   │     │  Valid?  │
└──────────┘     └──────────┘     └────┬─────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │ Yes              │                  │ No
                    ▼                  │                  ▼
            ┌──────────┐               │          ┌──────────┐
            │  Load    │               │          │  Scan    │
            │  Cache   │               │          │  Fresh   │
            └──────────┘               │          └────┬─────┘
                    │                  │               │
                    │                  ▼               │
                    │          ┌──────────┐            │
                    └─────────▶│  Store   │◀───────────┘
                               │  Cache   │
                               └──────────┘
```

## Development Setup

### Prerequisites

```bash
# Python 3.8+
python --version

# Install development dependencies
pip install -e ".[dev]"
```

### Project Structure

```
ptdu/
├── ptdu/                   # Main package
│   ├── __init__.py        # Package exports
│   ├── cache.py           # SQLite caching
│   ├── errors.py          # Error handling
│   ├── fonts.py           # Font management
│   ├── main.py            # CLI entry point
│   ├── models.py          # Data models
│   ├── performance.py     # Performance optimizations
│   ├── scanner.py         # Directory scanning
│   ├── threads.py         # Background threading
│   ├── treeview.py        # Treeview widget
│   ├── ui.py              # Main UI
│   └── utils.py           # Utilities
├── tests/                 # Test suite
├── docs/                  # Documentation
└── pyproject.toml         # Project configuration
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ptdu --cov-report=html

# Run specific test file
pytest tests/test_scanner.py

# Run with verbose output
pytest -v
```

### Type Checking

```bash
# Run mypy
mypy --strict ptdu/

# Check specific file
mypy --strict ptdu/scanner.py
```

### Code Style

The project follows strict typing requirements:
- All functions must have return type annotations
- Avoid `Any` type - use specific types or Protocols
- Use Pydantic models where applicable
- All code must pass `mypy --strict`

## Key Design Decisions

### 1. Full Recursive Scan

Unlike some tools that scan on-demand, PTDU performs a full recursive scan upfront (like ncdu). This provides:
- Complete size information immediately
- Accurate percentage calculations
- Better sorting capabilities

Trade-off: Higher initial scan time for large directories.

### 2. Background Threading

All filesystem operations run in separate threads:
- UI remains responsive during scans
- Progress updates via message queue
- Cancellation support via threading.Event

### 3. Vim-like Navigation

Keyboard-first interface:
- `j/k` for navigation
- `h/l` for expand/collapse
- Consistent with terminal tools

### 4. SQLite Caching

Persistent caching for performance:
- Automatic invalidation via mtime
- Thread-safe with locks
- Graceful degradation on errors

### 5. OS-Aware Fonts

Automatic font detection:
- Linux: Ubuntu, Noto Sans, DejaVu
- macOS: .SF NS, Helvetica
- Windows: Segoe UI

## Adding New Features

### Adding a New Keyboard Shortcut

1. Add method in `MainWindow`:
```python
def _on_new_action(self, event: Optional[tk.Event] = None) -> None:
    """Handle new action."""
    # Implementation
    return None
```

2. Bind in `_bind_events()`:
```python
self.root.bind("x", self._on_new_action)
```

3. Add menu item in `_create_menubar()`:
```python
action_menu.add_command(
    label="New Action",
    command=self._on_new_action,
    accelerator="x",
)
```

### Adding a New Sort Mode

1. Extend `SortMode` enum in `ui.py`:
```python
class SortMode(Enum):
    SIZE = auto()
    NAME = auto()
    COUNT = auto()
    NEW_MODE = auto()
```

2. Update `_get_sort_key()`:
```python
def _get_sort_key(self, node: DirNode) -> Any:
    if self._sort_mode == SortMode.NEW_MODE:
        return node.some_attribute
    # ...
```

3. Update display name mapping:
```python
SORT_MODE_NAMES: dict[SortMode, str] = {
    # ...
    SortMode.NEW_MODE: "New Mode",
}
```

### Adding Cache Support to Scanner

The scanner already supports caching. To use:

```python
from ptdu.cache import ScanCache
from ptdu.scanner import Scanner

cache = ScanCache()
scanner = Scanner(cache=cache)

# Try to load from cache
results = scanner.try_load_from_cache(path)
if results is None:
    # Scan fresh
    results = scanner.scan_directory(path)
    scanner.store_in_cache(path, results)
```

## Testing Guidelines

### Unit Tests

Test individual components in isolation:

```python
def test_size_calculator() -> None:
    assert SizeCalculator.format_size(1024) == "1.0 KB"
    assert SizeCalculator.format_size(0) == "0 B"
```

### Integration Tests

Test component interactions:

```python
def test_scan_thread() -> None:
    queue: Queue[ScanMessage] = Queue()
    scanner = Scanner()
    thread = ScanThread(path, scanner, queue)
    thread.start()
    thread.join()
    # Verify messages in queue
```

### UI Tests

Use tkinter test utilities:

```python
def test_main_window() -> None:
    root = tk.Tk()
    window = MainWindow(root)
    # Test UI operations
    root.destroy()
```

## Performance Considerations

### Memory Usage

- **DirNode objects**: ~200 bytes each
- **100k items**: ~20 MB
- **1M items**: ~200 MB

For very large directories:
- Use `--max-depth` to limit recursion
- Enable virtual scrolling (automatic for >10k items)
- Consider memory unloading (future enhancement)

### Scan Speed

Factors affecting scan speed:
- Filesystem type (SSD vs HDD)
- Number of files
- Symlink following
- Cache hit rate

Typical speeds:
- SSD: 50k-100k files/second
- HDD: 5k-10k files/second

### Cache Performance

Cache lookup is O(1) via SQLite index:
- Cache hit: ~1ms
- Cache miss (full scan): varies by directory size

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Common Issues

**UI Freezes**
- Check that all filesystem ops are in threads
- Verify message queue isn't blocking
- Ensure `window.after()` is used for updates

**Memory Leaks**
- Check DirNode parent references
- Verify treeview node_map cleanup
- Monitor cache size

**Thread Issues**
- Use locks for shared state
- Check for race conditions in message handling
- Verify thread cleanup on exit

## Contributing

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Ensure `mypy --strict` passes
5. Run full test suite
6. Submit PR with description

### Code Review Checklist

- [ ] Type annotations complete
- [ ] No `Any` types without justification
- [ ] Docstrings for public methods
- [ ] Tests added/updated
- [ ] Error handling appropriate
- [ ] Performance considerations addressed

## Future Enhancements

Potential areas for improvement:

1. **Async I/O**: Replace threads with asyncio for better scalability
2. **Remote Scanning**: Scan remote filesystems via SSH/SMB
3. **Visualization**: Add pie/bar charts for disk usage
4. **Search**: Filter files by name pattern
5. **Diff Mode**: Compare two scans to find changes
6. **Plugins**: Extension system for custom functionality

## Resources

- [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html)
- [ttk Widgets](https://docs.python.org/3/library/tkinter.ttk.html)
- [Python Threading](https://docs.python.org/3/library/threading.html)
- [SQLite Python](https://docs.python.org/3/library/sqlite3.html)
- [os.scandir()](https://docs.python.org/3/library/os.html#os.scandir)