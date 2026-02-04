"""Font configuration utility for PTDU.

Provides OS-aware font detection and configuration.
"""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import font as tkfont
from typing import Literal, Optional


class FontManager:
    """Manages font detection and configuration for different operating systems."""

    # Font size recommendations (increased for better readability)
    BASE_SIZE: int = 13
    HEADING_SIZE: int = 12
    STATUS_SIZE: int = 12

    # Font size adjustment
    SIZE_STEP: int = 1
    MIN_SIZE: int = 8
    MAX_SIZE: int = 20

    # OS-specific font preferences (prioritize cleaner, more modern fonts)
    LINUX_FONTS: tuple[str, ...] = (
        "Ubuntu",  # Clean, modern, highly readable
        "Noto Sans",  # Google's unified font, very readable
        "DejaVu Sans",  # Widely available, clean
        "Cantarell",  # GNOME's default, modern
        "Liberation Sans",  # Metric-compatible with Arial
    )
    MACOS_FONTS: tuple[str, ...] = (".SF NS", "Helvetica Neue", "Helvetica", "Arial")
    WINDOWS_FONTS: tuple[str, ...] = ("Segoe UI", "Tahoma", "Arial")

    def __init__(self, root: Optional[tk.Tk] = None) -> None:
        """Initialize the font manager.

        Args:
            root: Tk root window for font querying
        """
        self._root: Optional[tk.Tk] = root
        self._family: Optional[str] = None
        self._fonts: dict[str, tkfont.Font] = {}

    def _get_available_fonts(self) -> set[str]:
        """Get set of available font families on the system.

        Returns:
            Set of available font family names
        """
        if self._root is None:
            # Create temporary root for font querying if needed
            temp_root = tk.Tk()
            temp_root.withdraw()
            families = set(tkfont.families(temp_root))
            temp_root.destroy()
        else:
            families = set(tkfont.families(self._root))

        return families

    def detect_font_family(self) -> str:
        """Detect the best available font family for the current OS.

        Returns:
            Font family name
        """
        available = self._get_available_fonts()
        system = sys.platform

        if system == "darwin":  # macOS
            preferences = self.MACOS_FONTS
        elif system == "win32":  # Windows
            preferences = self.WINDOWS_FONTS
        else:  # Linux and others
            preferences = self.LINUX_FONTS

        # Find first available preferred font
        for family in preferences:
            if family in available:
                self._family = family
                return family

        # Fallback to TkDefaultFont
        self._family = "TkDefaultFont"
        return self._family

    def get_family(self) -> str:
        """Get the detected or default font family.

        Returns:
            Font family name
        """
        if self._family is None:
            return self.detect_font_family()
        return self._family

    def get_font(
        self,
        name: str,
        size: Optional[int] = None,
        weight: Literal["normal", "bold"] = "normal",
        slant: Literal["roman", "italic"] = "roman",
    ) -> tkfont.Font:
        """Get or create a named font configuration.

        Args:
            name: Font configuration name (e.g., 'treeview', 'heading', 'status')
            size: Font size in points (uses default if None)
            weight: Font weight ('normal', 'bold')
            slant: Font slant ('roman', 'italic')

        Returns:
            Configured tkinter Font object
        """
        if name in self._fonts:
            return self._fonts[name]

        family = self.get_family()
        actual_size = size if size is not None else self.BASE_SIZE

        font = tkfont.Font(family=family, size=actual_size, weight=weight, slant=slant)
        self._fonts[name] = font

        return font

    def get_treeview_font(self) -> tkfont.Font:
        """Get font for treeview items.

        Returns:
            Font for treeview content
        """
        return self.get_font("treeview", size=self.BASE_SIZE)

    def get_heading_font(self) -> tkfont.Font:
        """Get font for treeview headings.

        Returns:
            Font for column headings
        """
        return self.get_font("heading", size=self.HEADING_SIZE, weight="bold")

    def get_status_font(self) -> tkfont.Font:
        """Get font for status bar.

        Returns:
            Font for status bar text
        """
        return self.get_font("status", size=self.STATUS_SIZE)

    def get_directory_font(self) -> tkfont.Font:
        """Get font for directory entries (bold).

        Returns:
            Font for directory names
        """
        return self.get_font("directory", size=self.BASE_SIZE, weight="bold")

    def get_file_font(self) -> tkfont.Font:
        """Get font for file entries.

        Returns:
            Font for file names
        """
        return self.get_font("file", size=self.BASE_SIZE)

    def update_font_sizes(self, base_size: int) -> None:
        """Update all font sizes relative to new base size.

        Args:
            base_size: New base font size
        """
        self.BASE_SIZE = base_size
        self.HEADING_SIZE = base_size - 1
        self.STATUS_SIZE = base_size - 1

        # Recreate fonts with new sizes
        for name, font in self._fonts.items():
            if name == "heading":
                font.configure(size=self.HEADING_SIZE)
            elif name == "status":
                font.configure(size=self.STATUS_SIZE)
            else:
                font.configure(size=self.BASE_SIZE)

    def measure_text_width(self, text: str, font_name: str = "treeview") -> int:
        """Measure the pixel width of text.

        Args:
            text: Text to measure
            font_name: Name of font to use

        Returns:
            Width in pixels
        """
        font = self.get_font(font_name)
        return font.measure(text)

    def increase_font_size(self) -> int:
        """Increase all font sizes by SIZE_STEP.

        Returns:
            New base font size
        """
        new_size = min(self.BASE_SIZE + self.SIZE_STEP, self.MAX_SIZE)
        self.update_font_sizes(new_size)
        return new_size

    def decrease_font_size(self) -> int:
        """Decrease all font sizes by SIZE_STEP.

        Returns:
            New base font size
        """
        new_size = max(self.BASE_SIZE - self.SIZE_STEP, self.MIN_SIZE)
        self.update_font_sizes(new_size)
        return new_size

    def reset_font_size(self) -> int:
        """Reset font sizes to default.

        Returns:
            New base font size
        """
        self.update_font_sizes(13)
        return 13

    def get_font_size(self) -> int:
        """Get current base font size.

        Returns:
            Current base font size
        """
        return self.BASE_SIZE
