"""
Tests for cabling calculation functionality.

This module tests the cabling calculation engine including:
- Distance calculations
- Cable type selection
- BOM aggregation
- Policy loading
- Export functions
- Validation
"""

import csv
from unittest.mock import patch

import yaml

# Import the functions we want to test
from inferno_tools.cabling import (
    _aggregate_cable_bom,
    _build_network_links,
    _calculate_manhattan_distance,
    _export_bom,
    _select_cable_type_and_bin,
    _validate_bom,
    _with_spares,
    calculate_cabling_bom,
)
from inferno_core.data.cabling_policy import load_cabling_policy


class TestManhattanDistance:
    """Test Manhattan distance calculations."""

    def test_same_position(self):
        """Test distance calculation for same rack position."""
        distance = _calculate_manhattan_distance([0, 0], [0, 0])
        assert distance == 0.0

    def test_adjacent_horizontal(self):
        """Test distance calculation for horizontally adjacent racks."""
        distance = _calculate_manhattan_distance([0, 0], [1, 0])
        assert distance == 1.0  # 1 tile * 1 meter per tile (default)

    def test_adjacent_vertical(self):
        """Test distance calculation for vertically adjacent racks."""
        distance = _calculate_manhattan_distance([0, 0], [0, 1])
        assert distance == 1.0  # 1 tile * 1 meter per tile (default)

    def test_diagonal_distance(self):
        """Test distance calculation for diagonal rack positions."""
        distance = _calculate_manhattan_distance([0, 0], [1, 1])
        assert distance == 2.0  # (1 + 1) * 1 meter per tile (default)

    def test_custom_tile_size(self):
        """Test distance calculation with custom tile size."""
        distance = _calculate_manhattan_distance([0, 0], [2, 1], tile_m=4.0)
        assert distance == 12.0  # (2 + 1) * 4 meters per tile

    def test_negative_coordinates(self):
        """Test distance calculation with negative coordinates."""
        distance = _calculate_manhattan_distance([-1, -1], [1, 1])
        assert distance == 4.0  # (2 + 2) * 1 meter per tile (default)


class TestCableTypeSelection:
    """Test cable type and length bin selection."""

    def setup_method(self):
        """Set up test policy data."""
        self.policy = {
            "defaults": {"slack_factor": 1.2},
            "media_rules": {
                "sfp28_25g": {
                    "dac_max_m": 3,
                    "labels": {"dac": "SFP28 25G DAC", "aoc": "SFP28 25G AOC", "fiber": "SFP28 25G MMF + SR"},
                },
                "qsfp28_100g": {
                    "dac_max_m": 3,
                    "labels": {"dac": "QSFP28 100G DAC", "aoc": "QSFP28 100G AOC", "fiber": "QSFP28 100G MMF + SR4"},
                },
                "rj45_cat6a": {"label": "RJ45 Cat6A"},
            },
        }
        self.length_bins = [1, 2, 3, 5, 7, 10]

    def test_25g_dac_selection(self):
        """Test 25G DAC cable selection for short distances."""
        cable_type, length_bin = _select_cable_type_and_bin(2.0, "25G", self.policy, self.length_bins)
        assert cable_type == "SFP28 25G DAC"
        assert length_bin == 3  # 2.0 * 1.2 = 2.4, rounds up to 3m bin

    def test_25g_aoc_selection(self):
        """Test 25G AOC cable selection for medium distances."""
        cable_type, length_bin = _select_cable_type_and_bin(5.0, "25G", self.policy, self.length_bins)
        assert cable_type == "SFP28 25G AOC"
        assert length_bin == 7  # 5.0 * 1.2 = 6.0, rounds up to 7m bin

    def test_25g_fiber_selection(self):
        """Test 25G fiber cable selection for long distances."""
        cable_type, length_bin = _select_cable_type_and_bin(15.0, "25G", self.policy, self.length_bins)
        assert cable_type == "SFP28 25G MMF + SR"
        assert length_bin == 10  # Uses largest bin for distances exceeding all bins

    def test_100g_dac_selection(self):
        """Test 100G DAC cable selection."""
        cable_type, length_bin = _select_cable_type_and_bin(1.5, "100G", self.policy, self.length_bins)
        assert cable_type == "QSFP28 100G DAC"
        assert length_bin == 2  # 1.5 * 1.2 = 1.8, rounds up to 2m bin

    def test_rj45_selection(self):
        """Test RJ45 cable selection."""
        cable_type, length_bin = _select_cable_type_and_bin(3.0, "RJ45", self.policy, self.length_bins)
        assert cable_type == "RJ45 Cat6A"
        assert length_bin == 5  # 3.0 * 1.2 = 3.6, rounds up to 5m bin

    def test_unknown_link_type(self):
        """Test handling of unknown link types."""
        cable_type, length_bin = _select_cable_type_and_bin(2.0, "UNKNOWN", self.policy, self.length_bins)
        assert cable_type == "Unknown UNKNOWN"
        assert length_bin == 3


class TestSparesCalculation:
    """Test spares calculation functionality."""

    def test_with_spares_basic(self):
        """Test basic spares calculation."""
        result = _with_spares(10, 0.10)
        assert result == 11  # 10 * 1.1 = 11

    def test_with_spares_rounding_up(self):
        """Test spares calculation rounds up."""
        result = _with_spares(9, 0.10)
        assert result == 10  # 9 * 1.1 = 9.9, rounds up to 10

    def test_with_spares_zero_count(self):
        """Test spares calculation with zero count."""
        result = _with_spares(0, 0.10)
        assert result == 0

    def test_with_spares_high_percentage(self):
        """Test spares calculation with high percentage."""
        result = _with_spares(5, 0.50)
        assert result == 8  # 5 * 1.5 = 7.5, rounds up to 8


class TestBOMAggregation:
    """Test BOM aggregation functionality."""

    def test_aggregate_single_cable_type(self):
        """Test aggregation with single cable type."""
        links = [
            {"cable_type": "QSFP28 100G DAC", "length_bin": 1},
            {"cable_type": "QSFP28 100G DAC", "length_bin": 1},
            {"cable_type": "QSFP28 100G DAC", "length_bin": 2},
        ]
        policy = {"defaults": {"spares_fraction": 0.10}}

        bom = _aggregate_cable_bom(links, policy, 0.10, [1, 2, 3])

        expected = {"QSFP28 100G DAC": {1: 3, 2: 2}}  # 2 * 1.1 = 2.2, rounds up to 3  # 1 * 1.1 = 1.1, rounds up to 2
        assert bom == expected

    def test_aggregate_multiple_cable_types(self):
        """Test aggregation with multiple cable types."""
        links = [
            {"cable_type": "QSFP28 100G DAC", "length_bin": 1},
            {"cable_type": "RJ45 Cat6A", "length_bin": 3},
            {"cable_type": "RJ45 Cat6A", "length_bin": 3},
        ]
        policy = {"defaults": {"spares_fraction": 0.10}}

        bom = _aggregate_cable_bom(links, policy, 0.10, [1, 2, 3])

        expected = {
            "QSFP28 100G DAC": {1: 2},  # 1 * 1.1 = 1.1, rounds up to 2
            "RJ45 Cat6A": {3: 3},  # 2 * 1.1 = 2.2, rounds up to 3
        }
        assert bom == expected


class TestPolicyLoading:
    """Test cabling policy loading."""

    def test_load_policy_with_valid_file(self, tmp_path):
        """Test loading a valid policy file."""
        policy_content = """
version: 1
defaults:
  nodes_25g_per_node: 2
  spares_fraction: 0.15
media_rules:
  sfp28_25g:
    dac_max_m: 3
    bins_m: [1, 2, 3, 5]
"""
        policy_file = tmp_path / "policy.yaml"
        policy_file.write_text(policy_content)

        policy = load_cabling_policy(str(policy_file))

        assert policy["defaults"]["nodes_25g_per_node"] == 2
        assert policy["defaults"]["spares_fraction"] == 0.15
        assert policy["bins"]["sfp28"] == [1, 2, 3, 5]

    def test_load_policy_missing_file(self):
        """Test loading policy with missing file uses defaults."""
        policy = load_cabling_policy("nonexistent.yaml")

        # Should return defaults
        assert policy["defaults"]["nodes_25g_per_node"] == 1
        assert policy["defaults"]["spares_fraction"] == 0.10
        assert policy["bins"]["sfp28"] == [1, 2, 3, 5, 7, 10]

    def test_load_policy_invalid_yaml(self, tmp_path):
        """Test loading policy with invalid YAML uses defaults."""
        policy_file = tmp_path / "invalid.yaml"
        policy_file.write_text("invalid: yaml: content: [")

        policy = load_cabling_policy(str(policy_file))

        # Should return defaults when YAML is invalid
        assert policy["defaults"]["nodes_25g_per_node"] == 1


class TestValidation:
    """Test BOM validation functionality."""

    def test_validate_missing_spines(self):
        """Test validation with missing spines."""
        topology = {"leafs": [{"id": "leaf1"}]}
        warnings = _validate_bom(topology, {}, {}, [], {})

        assert "No spines defined in topology" in warnings

    def test_validate_missing_leafs(self):
        """Test validation with missing leafs."""
        topology = {"spines": [{"id": "spine1"}]}
        warnings = _validate_bom(topology, {}, {}, [], {})

        assert "No leafs defined in topology" in warnings

    def test_validate_dac_distance_warning(self):
        """Test validation warning for long DAC cables."""
        topology = {"spines": [{"id": "spine1"}], "leafs": [{"id": "leaf1"}]}
        links = [{"distance_m": 15.0, "cable_type": "QSFP28 100G DAC"}]

        warnings = _validate_bom(topology, {}, {}, links, {})

        assert any("DAC cable selected for 15.0m link" in w for w in warnings)

    def test_validate_very_long_link(self):
        """Test validation warning for very long links."""
        topology = {"spines": [{"id": "spine1"}], "leafs": [{"id": "leaf1"}]}
        links = [{"distance_m": 150.0, "cable_type": "SFP28 25G AOC"}]

        warnings = _validate_bom(topology, {}, {}, links, {})

        assert any("Very long link: 150.0m" in w for w in warnings)


class TestExportFunctions:
    """Test BOM export functionality."""

    def test_export_yaml(self, tmp_path):
        """Test YAML export functionality."""
        bom = {"QSFP28 100G DAC": {1: 2, 2: 3}, "RJ45 Cat6A": {3: 1}}
        warnings = ["Test warning"]
        policy = {"version": "test", "defaults": {"spares_fraction": 0.10, "slack_factor": 1.2}}

        export_path = tmp_path / "test_bom.yaml"
        _export_bom(bom, warnings, str(export_path), "yaml", policy)

        # Verify file was created
        assert export_path.exists()

        # Verify content
        with open(export_path) as f:
            data = yaml.safe_load(f)

        assert "bom" in data
        assert "metadata" in data
        assert data["bom"] == bom
        assert data["metadata"]["warnings"] == warnings
        assert data["metadata"]["spares_fraction"] == 0.10

    def test_export_csv(self, tmp_path):
        """Test CSV export functionality."""
        bom = {"QSFP28 100G DAC": {1: 2, 2: 3}, "RJ45 Cat6A": {3: 1}}
        warnings = []
        policy = {"defaults": {"spares_fraction": 0.10}}

        export_path = tmp_path / "test_bom.csv"
        _export_bom(bom, warnings, str(export_path), "csv", policy)

        # Verify file was created
        assert export_path.exists()

        # Verify content
        with open(export_path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Check header
        assert rows[0] == ["Cable Type", "Length Bin (m)", "Quantity"]

        # Check data rows (sorted)
        expected_rows = [["QSFP28 100G DAC", "1", "2"], ["QSFP28 100G DAC", "2", "3"], ["RJ45 Cat6A", "3", "1"]]
        assert rows[1:] == expected_rows


class TestNetworkLinkBuilding:
    """Test network link building functionality."""

    def test_build_links_with_site_data(self):
        """Test building links with site geometry data."""
        topology = {
            "spines": [
                {"id": "spine-1", "interfaces": [{"name": "eth1/1", "type": "100G", "connects_to": "tor-1:qsfp28-1"}]}
            ],
            "leafs": [{"id": "tor-1", "rack_id": "rack-1"}],
        }

        site = {
            "racks": [{"id": "rack-1", "grid": [0, 0]}, {"id": "rack-2", "grid": [1, 0]}],
            "spine": {"rack_id": "rack-2"},
        }

        policy = {
            "defaults": {"slack_factor": 1.2},
            "media_rules": {"qsfp28_100g": {"dac_max_m": 3, "labels": {"dac": "QSFP28 100G DAC"}}},
        }

        links = _build_network_links(topology, site, policy)

        assert len(links) == 1
        assert links[0]["from"] == "spine-1:eth1/1"
        assert links[0]["to"] == "tor-1:qsfp28-1"
        assert links[0]["type"] == "100G"
        assert links[0]["cable_type"] == "QSFP28 100G DAC"
        assert links[0]["category"] == "spine_to_leaf"

    def test_build_links_with_wan_handoff(self):
        """Test building links with WAN handoff."""
        topology = {"spines": [], "leafs": []}

        site = {"spine": {"wan_handoff": {"type": "RJ45", "count": 2}}}

        policy = {"defaults": {"slack_factor": 1.2}, "media_rules": {"rj45_cat6a": {"label": "RJ45 Cat6A"}}}

        links = _build_network_links(topology, site, policy)

        assert len(links) == 2
        assert all(link["category"] == "wan" for link in links)
        assert all(link["cable_type"] == "RJ45 Cat6A" for link in links)


class TestIntegration:
    """Integration tests for the complete cabling calculation."""

    @patch("inferno_tools.cabling._load_yaml")
    def test_calculate_cabling_bom_integration(self, mock_load_yaml, tmp_path):
        """Test complete BOM calculation integration."""
        # Mock the YAML loading
        mock_topology = {
            "spines": [
                {"id": "spine-1", "interfaces": [{"name": "eth1/1", "type": "100G", "connects_to": "tor-1:qsfp28-1"}]}
            ],
            "leafs": [{"id": "tor-1", "rack_id": "rack-1"}],
        }

        mock_site = {
            "racks": [{"id": "rack-1", "grid": [0, 0]}, {"id": "rack-2", "grid": [1, 0]}],
            "spine": {"rack_id": "rack-2"},
        }

        def mock_load_side_effect(path):
            if "topology" in path:
                return mock_topology
            elif "site" in path:
                return mock_site
            else:
                return {}

        mock_load_yaml.side_effect = mock_load_side_effect

        # Test the integration
        export_path = tmp_path / "integration_test.yaml"

        calculate_cabling_bom(
            topology_path="mock_topology.yaml",
            nodes_path="mock_nodes.yaml",
            tors_path="mock_tors.yaml",
            site_path="mock_site.yaml",
            policy_path="mock_policy.yaml",
            spares_fraction=0.10,
            length_bins_m=[1, 2, 3, 5, 7, 10],
            export_path=str(export_path),
            export_format="yaml",
        )

        # Verify the export file was created
        assert export_path.exists()

        # Verify the content structure
        with open(export_path) as f:
            data = yaml.safe_load(f)

        assert "bom" in data
        assert "metadata" in data
        assert data["metadata"]["generated_by"] == "inferno-cli tools cabling calculate"
