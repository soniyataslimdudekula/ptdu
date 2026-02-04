"""Tests for utils module."""

import pytest

from ptdu.utils import SizeCalculator


class TestSizeCalculator:
    """Test cases for SizeCalculator class."""

    class TestFormatSize:
        """Test cases for format_size method."""

        def test_format_zero_bytes(self) -> None:
            """Test formatting zero bytes."""
            assert SizeCalculator.format_size(0) == "0 B"

        def test_format_bytes(self) -> None:
            """Test formatting small byte values."""
            assert SizeCalculator.format_size(1) == "1 B"
            assert SizeCalculator.format_size(512) == "512 B"
            assert SizeCalculator.format_size(1023) == "1023 B"

        def test_format_kilobytes(self) -> None:
            """Test formatting kilobyte values."""
            assert SizeCalculator.format_size(1024) == "1.0 KB"
            assert SizeCalculator.format_size(1536) == "1.5 KB"
            assert SizeCalculator.format_size(10240) == "10.0 KB"

        def test_format_megabytes(self) -> None:
            """Test formatting megabyte values."""
            assert SizeCalculator.format_size(1024**2) == "1.00 MB"
            assert SizeCalculator.format_size(5 * 1024**2) == "5.00 MB"
            assert SizeCalculator.format_size(1536 * 1024) == "1.50 MB"

        def test_format_gigabytes(self) -> None:
            """Test formatting gigabyte values."""
            assert SizeCalculator.format_size(1024**3) == "1.00 GB"
            assert SizeCalculator.format_size(int(1.5 * 1024**3)) == "1.50 GB"

        def test_format_terabytes(self) -> None:
            """Test formatting terabyte values."""
            assert SizeCalculator.format_size(1024**4) == "1.00 TB"

        def test_format_petabytes(self) -> None:
            """Test formatting petabyte values."""
            assert SizeCalculator.format_size(1024**5) == "1.00 PB"

        def test_format_negative_raises(self) -> None:
            """Test that negative size raises ValueError."""
            with pytest.raises(ValueError, match="Size cannot be negative"):
                SizeCalculator.format_size(-1)

    class TestFormatPercentage:
        """Test cases for format_percentage method."""

        def test_format_zero_total(self) -> None:
            """Test percentage with zero total."""
            assert SizeCalculator.format_percentage(100, 0) == "0.0%"
            assert SizeCalculator.format_percentage(0, 0) == "0.0%"

        def test_format_full_percentage(self) -> None:
            """Test 100% formatting."""
            assert SizeCalculator.format_percentage(100, 100) == "100.0%"

        def test_format_partial_percentage(self) -> None:
            """Test partial percentage formatting."""
            assert SizeCalculator.format_percentage(25, 100) == "25.0%"
            assert SizeCalculator.format_percentage(33, 100) == "33.0%"
            assert SizeCalculator.format_percentage(1, 3) == "33.3%"

        def test_format_small_percentage(self) -> None:
            """Test small percentage values."""
            assert SizeCalculator.format_percentage(1, 1000) == "0.1%"

    class TestCalculatePercentage:
        """Test cases for calculate_percentage method."""

        def test_calculate_zero_total(self) -> None:
            """Test percentage calculation with zero total."""
            assert SizeCalculator.calculate_percentage(100, 0) == 0.0
            assert SizeCalculator.calculate_percentage(0, 0) == 0.0

        def test_calculate_full_percentage(self) -> None:
            """Test 100% calculation."""
            assert SizeCalculator.calculate_percentage(100, 100) == 100.0

        def test_calculate_partial_percentage(self) -> None:
            """Test partial percentage calculation."""
            assert SizeCalculator.calculate_percentage(25, 100) == 25.0
            assert SizeCalculator.calculate_percentage(1, 4) == 25.0

        def test_calculate_returns_float(self) -> None:
            """Test that calculate_percentage returns float."""
            result = SizeCalculator.calculate_percentage(50, 100)
            assert isinstance(result, float)
