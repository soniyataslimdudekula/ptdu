"""Entry point for PTDU application."""

import argparse
import sys
from pathlib import Path

from ptdu.cache import ScanCache
from ptdu.scanner import Scanner
from ptdu.ui import MainWindow


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ptdu",
        description="Python Tkinter Disk Usage analyzer - A graphical disk usage tool",
        epilog="Keyboard shortcuts: j/k=navigate, h/l=expand/collapse, q=quit, r=rescan, d=delete",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        type=Path,
        help="Directory to analyze (default: current directory)",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symbolic links when scanning",
    )
    parser.add_argument(
        "--exclude",
        "-e",
        action="append",
        default=[],
        help="Additional patterns to exclude (can be used multiple times)",
    )
    parser.add_argument(
        "--max-depth",
        "-d",
        type=int,
        default=None,
        help="Maximum scan depth (default: unlimited)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable SQLite caching",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before starting",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser


def validate_path(path: Path) -> Path:
    """Validate that the provided path exists and is a directory."""
    if not path.exists():
        raise SystemExit(f"Error: Path does not exist: {path}")
    if not path.is_dir():
        raise SystemExit(f"Error: Path is not a directory: {path}")
    return path.resolve()


def main() -> int:
    """Main entry point for the PTDU application."""
    parser = create_argument_parser()
    args = parser.parse_args()

    try:
        target_path = validate_path(args.path)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 1

    # Handle cache
    cache: ScanCache | None = None
    if not args.no_cache:
        cache = ScanCache()
        if args.clear_cache:
            cache.clear()
            print("Cache cleared.")

    # Convert exclude list to tuple
    exclude_patterns = tuple(args.exclude) if args.exclude else None

    # Create scanner with all options
    scanner = Scanner(
        follow_symlinks=args.follow_symlinks,
        exclude_patterns=exclude_patterns,
        cache=cache,
    )

    # Create main window and set scanner
    window = MainWindow()
    window.set_scanner(scanner)

    # Set max depth if specified
    if args.max_depth is not None:
        window.set_max_depth(args.max_depth)

    # Start background scan of initial directory
    window.start_background_scan(target_path)

    # Run the application
    window.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
