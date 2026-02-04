"""Utility classes for PTDU."""

from __future__ import annotations


class SizeCalculator:
    """Utility class for size calculations and formatting."""

    # Size units in bytes
    UNITS: list[tuple[str, int]] = [
        ("B", 1),
        ("KB", 1024),
        ("MB", 1024**2),
        ("GB", 1024**3),
        ("TB", 1024**4),
        ("PB", 1024**5),
    ]

    @classmethod
    def format_size(cls, size_bytes: int) -> str:
        """Format byte size to human-readable string.

        Args:
            size_bytes: Size in bytes

        Returns:
            Human-readable size string (e.g., "1.5 MB", "512 B")
        """
        if size_bytes < 0:
            raise ValueError("Size cannot be negative")

        if size_bytes == 0:
            return "0 B"

        # Find appropriate unit
        for unit_name, unit_bytes in reversed(cls.UNITS):
            if size_bytes >= unit_bytes:
                value = size_bytes / unit_bytes
                # Use integer for bytes, one decimal for KB, two for larger
                if unit_name == "B":
                    return f"{int(value)} {unit_name}"
                elif unit_name == "KB":
                    return f"{value:.1f} {unit_name}"
                else:
                    return f"{value:.2f} {unit_name}"

        return f"{size_bytes} B"

    @classmethod
    def format_percentage(cls, part: int, total: int) -> str:
        """Calculate and format percentage.

        Args:
            part: The partial size
            total: The total size

        Returns:
            Percentage string (e.g., "45.2%")
        """
        if total <= 0:
            return "0.0%"

        percentage = (part / total) * 100
        return f"{percentage:.1f}%"

    @classmethod
    def calculate_percentage(cls, part: int, total: int) -> float:
        """Calculate percentage as float.

        Args:
            part: The partial size
            total: The total size

        Returns:
            Percentage value (0-100)
        """
        if total <= 0:
            return 0.0

        return (part / total) * 100
