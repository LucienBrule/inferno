"""
Test geometry calculations for cabling.

Tests the calculation side of geometry handling to ensure shared helpers
work correctly and produce expected results for all fixture scenarios.
"""

from pathlib import Path

import pytest
from inferno_tools.cabling.common import (
    apply_slack,
    compute_rack_distance_m,
    select_length_bin,
)


class TestGeometryHelpers:
    """Test the shared geometry helper functions."""

    def test_compute_rack_distance_m(self):
        """Test Manhattan distance calculation."""
        # Same position
        assert compute_rack_distance_m((0, 0), (0, 0), 1.0) == 0.0

        # Horizontal distance
        assert compute_rack_distance_m((0, 0), (3, 0), 1.0) == 3.0

        # Vertical distance
        assert compute_rack_distance_m((0, 0), (0, 2), 1.0) == 2.0

        # Diagonal (Manhattan)
        assert compute_rack_distance_m((0, 0), (3, 2), 1.0) == 5.0

        # With custom tile size
        assert compute_rack_distance_m((0, 0), (2, 1), 1.5) == 4.5  # (2+1) * 1.5

    def test_apply_slack(self):
        """Test slack factor application."""
        assert apply_slack(10.0, 1.0) == 10.0
        assert apply_slack(10.0, 1.2) == 12.0
        assert apply_slack(5.0, 1.5) == 7.5

    def test_select_length_bin(self):
        """Test length bin selection."""
        bins = [1, 3, 5, 10, 30]

        # Exact match
        assert select_length_bin(3.0, bins) == 3

        # Just under
        assert select_length_bin(2.9, bins) == 3

        # Just over
        assert select_length_bin(3.1, bins) == 5

        # Exceeds all bins
        assert select_length_bin(50.0, bins) is None

        # Very small distance
        assert select_length_bin(0.5, bins) == 1


class TestGeometryFixtures:
    """Test geometry calculations using the test fixtures."""

    @pytest.fixture
    def fixtures_path(self):
        """Path to geometry test fixtures."""
        return Path(__file__).parent / "fixtures" / "cabling" / "geometry"

    def test_boundary_equal_calculation(self, fixtures_path):
        """Test boundary_equal fixture - distance exactly at dac_max_m."""
        # Load policy to get parameters
        import yaml

        policy_path = fixtures_path / "boundary_equal" / "cabling-policy.yaml"
        with open(policy_path) as f:
            policy = yaml.safe_load(f)

        # Extract parameters
        tile_m = policy["heuristics"]["tile_m"]  # 1.25
        slack_factor = policy["heuristics"]["slack_factor"]  # 1.2
        dac_max_m = policy["media_rules"]["qsfp28_100g"]["dac_max_m"]  # 3.0

        # Calculate distance: 2 tiles * 1.25 * 1.2 = 3.0m exactly
        base_distance = compute_rack_distance_m((0, 0), (2, 0), tile_m)
        assert base_distance == 2.5  # 2 tiles * 1.25

        cable_length = apply_slack(base_distance, slack_factor)
        assert cable_length == 3.0  # Exactly at DAC threshold

        # Should select DAC (distance <= dac_max_m)
        assert cable_length <= dac_max_m

        # Should select appropriate bin
        bins = policy["media_rules"]["qsfp28_100g"]["bins_m"]
        selected_bin = select_length_bin(cable_length, bins)
        assert selected_bin == 3  # Should select 3m bin

    def test_just_over_threshold_calculation(self, fixtures_path):
        """Test just_over_threshold fixture - distance slightly over dac_max_m."""
        import yaml

        policy_path = fixtures_path / "just_over_threshold" / "cabling-policy.yaml"
        with open(policy_path) as f:
            policy = yaml.safe_load(f)

        # Extract parameters
        tile_m = policy["heuristics"]["tile_m"]  # 1.3
        slack_factor = policy["heuristics"]["slack_factor"]  # 1.2
        dac_max_m = policy["media_rules"]["qsfp28_100g"]["dac_max_m"]  # 3.0

        # Calculate distance: 2 tiles * 1.3 * 1.2 = 3.12m (just over 3.0m)
        base_distance = compute_rack_distance_m((0, 0), (2, 0), tile_m)
        assert base_distance == 2.6  # 2 tiles * 1.3

        cable_length = apply_slack(base_distance, slack_factor)
        assert cable_length == 3.12  # Just over DAC threshold

        # Should require AOC/fiber (distance > dac_max_m)
        assert cable_length > dac_max_m

        # Should still find a suitable bin
        bins = policy["media_rules"]["qsfp28_100g"]["bins_m"]
        selected_bin = select_length_bin(cable_length, bins)
        assert selected_bin == 5  # Should select 5m bin

    def test_far_racks_calculation(self, fixtures_path):
        """Test far_racks fixture - distance exceeding max bin."""
        import yaml

        policy_path = fixtures_path / "far_racks" / "cabling-policy.yaml"
        with open(policy_path) as f:
            policy = yaml.safe_load(f)

        # Extract parameters
        tile_m = policy["heuristics"]["tile_m"]  # 1.0
        slack_factor = policy["heuristics"]["slack_factor"]  # 1.2

        # Calculate distance: 9 tiles * 1.0 * 1.2 = 10.8m
        base_distance = compute_rack_distance_m((0, 0), (9, 0), tile_m)
        assert base_distance == 9.0  # 9 tiles * 1.0

        cable_length = apply_slack(base_distance, slack_factor)
        assert abs(cable_length - 10.8) < 0.001  # Exceeds max bin of 10m (floating point tolerance)

        # Should exceed maximum bin
        bins = policy["media_rules"]["qsfp28_100g"]["bins_m"]
        max_bin = max(bins)
        assert max_bin == 10
        assert cable_length > max_bin

        # select_length_bin should return None
        selected_bin = select_length_bin(cable_length, bins)
        assert selected_bin is None

    def test_slack_variants_calculation(self, fixtures_path):
        """Test slack_variants fixtures - different slack_factor values."""
        import yaml

        # Test slack_factor = 1.0
        policy_path_1_0 = fixtures_path / "slack_variants" / "slack_1_0" / "cabling-policy.yaml"
        with open(policy_path_1_0) as f:
            yaml.safe_load(f)

        # Test slack_factor = 1.5
        policy_path_1_5 = fixtures_path / "slack_variants" / "slack_1_5" / "cabling-policy.yaml"
        with open(policy_path_1_5) as f:
            yaml.safe_load(f)

        # Same base distance, different slack factors
        base_distance = 2.0  # Same rack connection

        cable_length_1_0 = apply_slack(base_distance, 1.0)
        cable_length_1_5 = apply_slack(base_distance, 1.5)

        assert cable_length_1_0 == 2.0
        assert cable_length_1_5 == 3.0

        # Should select different bins
        bins = [1, 3, 5, 10]
        bin_1_0 = select_length_bin(cable_length_1_0, bins)
        bin_1_5 = select_length_bin(cable_length_1_5, bins)

        assert bin_1_0 == 3  # 2.0m -> 3m bin
        assert bin_1_5 == 3  # 3.0m -> 3m bin (exact match)

    def test_tile_variants_calculation(self, fixtures_path):
        """Test tile_variants fixture - different tile_m values."""
        import yaml

        policy_path = fixtures_path / "tile_variants" / "cabling-policy.yaml"
        with open(policy_path) as f:
            policy = yaml.safe_load(f)

        # Extract parameters
        tile_m = policy["heuristics"]["tile_m"]  # 2.0
        slack_factor = policy["heuristics"]["slack_factor"]  # 1.2

        # Calculate distance: 2 tiles * 2.0 * 1.2 = 4.8m
        base_distance = compute_rack_distance_m((0, 0), (2, 0), tile_m)
        assert base_distance == 4.0  # 2 tiles * 2.0

        cable_length = apply_slack(base_distance, slack_factor)
        assert cable_length == 4.8

        # Should select 5m bin
        bins = policy["media_rules"]["qsfp28_100g"]["bins_m"]
        selected_bin = select_length_bin(cable_length, bins)
        assert selected_bin == 5

    def test_rj45_long_calculation(self, fixtures_path):
        """Test rj45_long fixture - RJ45 bins > 100m."""
        import yaml

        policy_path = fixtures_path / "rj45_long" / "cabling-policy.yaml"
        with open(policy_path) as f:
            policy = yaml.safe_load(f)

        # Extract parameters for RJ45 management connections
        mgmt_distance = policy["heuristics"]["same_rack_leaf_to_node_m"]  # 90.0
        slack_factor = policy["heuristics"]["slack_factor"]  # 1.2

        # Calculate RJ45 connection length: 90.0 * 1.2 = 108.0m
        cable_length = apply_slack(mgmt_distance, slack_factor)
        assert cable_length == 108.0

        # Should select 150m bin (> 100m)
        rj45_bins = policy["media_rules"]["rj45_cat6a"]["bins_m"]
        selected_bin = select_length_bin(cable_length, rj45_bins)
        assert selected_bin == 150
        assert selected_bin > 100  # Should trigger RJ45_BIN_GT_100M warning
