"""Shared geometry utilities for cabling calculations and validation.

This module provides common functions for distance calculations, slack application,
and length bin selection to ensure consistency between calculation and validation paths.
"""

from typing import Sequence

U_PITCH_M = 0.04445  # 1.75 in per U


def compute_rack_distance_m(grid_a: tuple[int, int], grid_b: tuple[int, int], tile_m: float) -> float:
    """Compute Manhattan distance between two rack grid positions in meters.

    Args:
        grid_a: Grid position (x, y) of first rack
        grid_b: Grid position (x, y) of second rack
        tile_m: Size of each grid tile in meters

    Returns:
        Manhattan distance in meters
    """
    dx = abs(grid_a[0] - grid_b[0])
    dy = abs(grid_a[1] - grid_b[1])
    return (dx + dy) * tile_m


def apply_slack(distance_m: float, slack_factor: float) -> float:
    """Apply slack factor to physical distance.

    Args:
        distance_m: Physical distance in meters
        slack_factor: Slack multiplier (must be >= 1.0)

    Returns:
        Distance with slack applied in meters
    """
    return distance_m * slack_factor


def select_length_bin(distance_m: float, bins_m: Sequence[int]) -> int | None:
    """Select the smallest bin that can accommodate the given distance.

    Args:
        distance_m: Required cable length in meters
        bins_m: Available length bins in meters

    Returns:
        Selected bin length in meters, or None if no suitable bin found
    """
    for b in sorted(bins_m):
        if distance_m <= b:
            return b
    return None
