# PTDU User Guide

## Overview

PTDU (Python Tkinter Disk Usage) is a graphical disk usage analyzer inspired by ncdu. It provides an interactive, navigable tree view of directory sizes with vim-like keyboard navigation.

## Installation

### From Source

```bash
git clone <repository>
cd ptdu
pip install -e .
```

### Requirements

- Python 3.8+
- Tkinter (usually included with Python)
- send2trash (optional, for safer file deletion)

## Quick Start

```bash
# Analyze current directory
ptdu

# Analyze specific directory
ptdu /path/to/directory

# Follow symbolic links
ptdu --follow-symlinks /path/to/directory

# Exclude patterns
ptdu -e "*.log" -e "temp" /path/to/directory
```

## Command-Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `path` | - | Directory to analyze (default: current directory) |
| `--follow-symlinks` | - | Follow symbolic links when scanning |
| `--exclude PATTERN` | `-e` | Exclude pattern (can be used multiple times) |
| `--max-depth N` | `-d` | Maximum scan depth |
| `--no-cache` | - | Disable SQLite caching |
| `--clear-cache` | - | Clear cache before starting |
| `--version` | - | Show version information |
| `--help` | `-h` | Show help message |

## Keyboard Shortcuts

### Navigation

| Key | Action |
|-----|--------|
| `j` or `↓` | Move down |
| `k` or `↑` | Move up |
| `h` or `←` | Collapse directory |
| `l` or `→` | Expand directory |
| `Enter` | Toggle expand/collapse |
| `g` | Jump to top |
| `G` | Jump to bottom |

### Actions

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `r` | Rescan current directory |
| `d` | Delete selected item (with confirmation) |
| `b` | Toggle breadcrumb/path bar |
| `u` | Go to parent directory |
| `o` | Open folder (file manager) |

### Sorting

| Key | Action |
|-----|--------|
| `s` | Cycle sort mode (Size → Name → Items) |

### View Options

| Key | Action |
|-----|--------|
| `.` | Toggle hidden files (dotfiles) |

### Export

| Key | Action |
|-----|--------|
| `e` | Export scan results (JSON/CSV) |

### Font Size

| Key | Action |
|-----|--------|
| `Ctrl + Plus` | Increase font size |
| `Ctrl + Minus` | Decrease font size |
| `Ctrl + 0` | Reset font size |

## Display Columns

1. **Name** - File or directory name with icon
2. **Size** - Human-readable size (B, KB, MB, GB, TB)
3. **Size Bar** - Visual representation of size
4. **Percent** - Percentage of parent directory
5. **Items** - Number of items (directories only)

## Color Coding

- **Blue** - Directories
- **Black** - Regular files
- **Gray** - Hidden files (starting with `.`)
- **Yellow/Orange** - Medium files (10-100 MB)
- **Red** - Large files (>100 MB)

## Menubar

The menubar provides discoverable access to all features:

- **File** - Open folder, Export, Quit
- **View** - Toggle hidden files, Toggle breadcrumb, Font size controls
- **Sort** - Sort by size, name, or item count
- **Navigation** - Expand/collapse, Jump to top/bottom, Parent directory
- **Actions** - Rescan, Delete

## Features

### SQLite Caching

PTDU automatically caches scan results to speed up subsequent scans. The cache is stored in `~/.cache/ptdu/cache.db` and is invalidated when directories are modified.

To disable caching:
```bash
ptdu --no-cache
```

To clear the cache:
```bash
ptdu --clear-cache
```

### Performance Optimizations

For large directories (100k+ items), PTDU includes:
- Virtual scrolling for smooth navigation
- Memory optimization with automatic unloading
- Configurable maximum scan depth

### Error Handling

PTDU provides user-friendly error dialogs for:
- Permission denied errors
- Long path warnings
- Scan errors with continue/skip options

## Tips

1. **Start with a specific directory** rather than `/` for faster initial scans
2. **Use `--max-depth`** to limit scanning on very large directories
3. **Use `--exclude`** to skip unnecessary directories (e.g., `node_modules`, `.git`)
4. **Press `r`** to rescan after making changes
5. **Use breadcrumbs (`b`)** for easy navigation in deep hierarchies

## Troubleshooting

### Permission Denied

If you see permission denied errors:
- Run with `sudo` for system directories
- Use `--exclude` to skip problematic directories
- Check file permissions with `ls -la`

### Slow Scanning

For slow scans:
- Use `--max-depth` to limit recursion
- Use `--exclude` for large unnecessary directories
- Ensure cache is enabled (default)

### Memory Issues

For directories with millions of files:
- Use `--max-depth 2` or `--max-depth 3`
- Close other applications
- Consider scanning subdirectories individually

## Keyboard Shortcut Reference Card

```
Navigation:     j/↓=down  k/↑=up  h/←=collapse  l/→=expand  Enter=toggle
Jumping:        g=top  G=bottom  u=parent
Actions:        q=quit  r=rescan  d=delete  o=open  e=export
View:           .=hidden  b=breadcrumb  s=sort
Font:           Ctrl++=bigger  Ctrl+-=smaller  Ctrl+0=reset
```

## Support

For issues, feature requests, or contributions, please visit the project repository.