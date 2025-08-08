"""Tests for cabling cross-validation functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from inferno_tools.cabling.cross_validate import (
    CrossReport,
    _aggregate_intent_to_class_structure,
    _derive_intent_links,
    _normalize_bom_to_class_structure,
    _reconcile_bom_vs_intent,
    cross_validate_bom,
)


@pytest.fixture
def sample_topology():
    """Sample topology data."""
    return {
        "racks": [{"rack_id": "rack-1", "uplinks_qsfp28": 2}, {"rack_id": "rack-2", "uplinks_qsfp28": 2}],
        "wan": {"uplinks_cat6a": 2},
    }


@pytest.fixture
def sample_nodes():
    """Sample nodes data."""
    return {
        "nodes": [
            {"id": "node-1", "rack_id": "rack-1", "nics": [{"type": "SFP28"}, {"type": "SFP28"}]},
            {"id": "node-2", "rack_id": "rack-1", "nics": [{"type": "SFP28"}, {"type": "SFP28"}]},
            {"id": "node-3", "rack_id": "rack-2", "nics": [{"type": "SFP28"}, {"type": "SFP28"}]},
            {"id": "node-4", "rack_id": "rack-2", "nics": [{"type": "SFP28"}, {"type": "SFP28"}]},
        ]
    }


@pytest.fixture
def sample_tors():
    """Sample ToR data."""
    return {
        "tors": [{"id": "tor-1", "rack_id": "rack-1"}, {"id": "tor-2", "rack_id": "rack-2"}],
        "spine": {"id": "spine-1"},
    }


@pytest.fixture
def sample_site():
    """Sample site data."""
    return {
        "racks": [{"id": "rack-1", "grid": [0, 0]}, {"id": "rack-2", "grid": [1, 0]}, {"id": "spine", "grid": [0, 1]}]
    }


@pytest.fixture
def sample_policy():
    """Sample cabling policy."""
    return {
        "defaults": {
            "nodes_25g_per_node": 2,
            "mgmt_rj45_per_node": 1,
            "tor_uplink_qsfp28_per_tor": 2,
            "slack_factor": 1.2,
        },
        "heuristics": {
            "same_rack_leaf_to_node_m": 2.0,
            "adjacent_rack_leaf_to_spine_m": 5.0,
            "tile_m": 1.0,
            "bin_slop_m": 2.0,
        },
        "media_rules": {
            "sfp28_25g": {"dac_max_m": 3.0, "bins_m": [1, 2, 3, 5, 7, 10]},
            "qsfp28_100g": {"dac_max_m": 3.0, "bins_m": [1, 2, 3, 5, 7, 10]},
            "rj45_cat6a": {"bins_m": [1, 2, 3, 5, 7, 10]},
        },
    }


@pytest.fixture
def happy_bom():
    """BOM that matches intent exactly."""
    return {
        "meta": {"policy_path": "doctrine/network/cabling-policy.yaml", "spares_fraction": 0.10},
        "items": [
            {"class": "leaf-node", "cable_type": "sfp28_25g", "length_bin_m": 3, "quantity": 8},
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 2, "quantity": 2},
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 3, "quantity": 2},
            {"class": "mgmt", "cable_type": "rj45_cat6a", "length_bin_m": 7, "quantity": 4},
            {"class": "wan", "cable_type": "rj45_cat6a", "length_bin_m": 10, "quantity": 2},
        ],
    }


@pytest.fixture
def missing_leaf_node_bom():
    """BOM missing some leaf-node cables."""
    return {
        "meta": {"policy_path": "doctrine/network/cabling-policy.yaml", "spares_fraction": 0.10},
        "items": [
            {"class": "leaf-node", "cable_type": "sfp28_25g", "length_bin_m": 3, "quantity": 6},  # Missing 2
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 2, "quantity": 2},
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 3, "quantity": 2},
            {"class": "mgmt", "cable_type": "rj45_cat6a", "length_bin_m": 7, "quantity": 4},
            {"class": "wan", "cable_type": "rj45_cat6a", "length_bin_m": 10, "quantity": 2},
        ],
    }


@pytest.fixture
def phantom_leaf_spine_bom():
    """BOM with extra leaf-spine cables."""
    return {
        "meta": {"policy_path": "doctrine/network/cabling-policy.yaml", "spares_fraction": 0.10},
        "items": [
            {"class": "leaf-node", "cable_type": "sfp28_25g", "length_bin_m": 3, "quantity": 8},
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 2, "quantity": 2},
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 3, "quantity": 4},  # Extra 2 in bin 3
            {"class": "mgmt", "cable_type": "rj45_cat6a", "length_bin_m": 7, "quantity": 4},
            {"class": "wan", "cable_type": "rj45_cat6a", "length_bin_m": 10, "quantity": 2},
        ],
    }


@pytest.fixture
def bin_mismatch_warn_bom():
    """BOM using next-higher bin within slop tolerance."""
    return {
        "meta": {"policy_path": "doctrine/network/cabling-policy.yaml", "spares_fraction": 0.10},
        "items": [
            {"class": "leaf-node", "cable_type": "sfp28_25g", "length_bin_m": 5, "quantity": 8},  # 5m instead of 3m
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 2, "quantity": 2},
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 3, "quantity": 2},
            {"class": "mgmt", "cable_type": "rj45_cat6a", "length_bin_m": 7, "quantity": 4},
            {"class": "wan", "cable_type": "rj45_cat6a", "length_bin_m": 10, "quantity": 2},
        ],
    }


@pytest.fixture
def bin_mismatch_fail_bom():
    """BOM using lower bin than intent."""
    return {
        "meta": {"policy_path": "doctrine/network/cabling-policy.yaml", "spares_fraction": 0.10},
        "items": [
            {"class": "leaf-node", "cable_type": "sfp28_25g", "length_bin_m": 1, "quantity": 8},  # 1m instead of 3m
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 2, "quantity": 2},
            {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": 3, "quantity": 2},
            {"class": "mgmt", "cable_type": "rj45_cat6a", "length_bin_m": 7, "quantity": 4},
            {"class": "wan", "cable_type": "rj45_cat6a", "length_bin_m": 10, "quantity": 2},
        ],
    }


class TestCrossValidation:
    """Test cross-validation functionality."""

    def test_normalize_bom_new_format(self, happy_bom):
        """Test BOM normalization with new format (explicit class)."""
        result = _normalize_bom_to_class_structure(happy_bom)

        assert "leaf-node" in result
        assert "sfp28_25g" in result["leaf-node"]
        assert result["leaf-node"]["sfp28_25g"][3] == 8

        assert "leaf-spine" in result
        assert "qsfp28_100g" in result["leaf-spine"]
        assert result["leaf-spine"]["qsfp28_100g"][2] == 2
        assert result["leaf-spine"]["qsfp28_100g"][3] == 2

    def test_normalize_bom_old_format(self):
        """Test BOM normalization with old format (inferred class)."""
        old_bom = {"sfp28_25g_dac": {3: 8}, "qsfp28_100g_aoc": {7: 4}, "rj45_cat6a": {7: 15}}  # High count -> mgmt

        result = _normalize_bom_to_class_structure(old_bom)

        assert "leaf-node" in result
        assert "leaf-spine" in result
        assert "mgmt" in result
        assert result["mgmt"]["rj45_cat6a"][7] == 15

    def test_derive_intent_links(self, sample_topology, sample_nodes, sample_tors, sample_site, sample_policy):
        """Test deriving intent links from topology/policy."""
        links = _derive_intent_links(sample_topology, sample_tors, sample_nodes, sample_site, sample_policy)

        # Should have leaf-node, leaf-spine, mgmt, and wan links
        leaf_node_links = [l for l in links if l["class"] == "leaf-node"]
        leaf_spine_links = [l for l in links if l["class"] == "leaf-spine"]
        mgmt_links = [l for l in links if l["class"] == "mgmt"]
        wan_links = [l for l in links if l["class"] == "wan"]

        assert len(leaf_node_links) == 8  # 4 nodes × 2 NICs each
        assert len(leaf_spine_links) == 4  # 2 racks × 2 uplinks each
        assert len(mgmt_links) == 4  # 4 nodes × 1 mgmt each
        assert len(wan_links) == 2  # 2 WAN uplinks

    def test_aggregate_intent_to_class_structure(
        self, sample_topology, sample_nodes, sample_tors, sample_site, sample_policy
    ):
        """Test aggregating intent links to class structure."""
        links = _derive_intent_links(sample_topology, sample_tors, sample_nodes, sample_site, sample_policy)
        result = _aggregate_intent_to_class_structure(links)

        assert "leaf-node" in result
        assert "leaf-spine" in result
        assert "mgmt" in result
        assert "wan" in result

        # Check counts
        assert result["leaf-node"]["sfp28_25g"][3] == 8
        # Leaf-spine links are distributed across bins based on distance calculation
        assert result["leaf-spine"]["qsfp28_100g"][2] == 2  # rack-1 links
        assert result["leaf-spine"]["qsfp28_100g"][3] == 2  # rack-2 links

    def test_reconcile_happy_path(self, sample_policy):
        """Test reconciliation with matching BOM and intent."""
        bom_structure = {"leaf-node": {"sfp28_25g": {3: 8}}, "leaf-spine": {"qsfp28_100g": {7: 4}}}
        intent_structure = {"leaf-node": {"sfp28_25g": {3: 8}}, "leaf-spine": {"qsfp28_100g": {7: 4}}}

        findings = _reconcile_bom_vs_intent(bom_structure, intent_structure, sample_policy)
        assert len(findings) == 0

    def test_reconcile_missing_links(self, sample_policy):
        """Test reconciliation with missing links."""
        bom_structure = {"leaf-node": {"sfp28_25g": {3: 6}}}  # Missing 2
        intent_structure = {"leaf-node": {"sfp28_25g": {3: 8}}}

        findings = _reconcile_bom_vs_intent(bom_structure, intent_structure, sample_policy)
        assert len(findings) == 1
        assert findings[0].code == "MISSING_LINK"
        assert findings[0].severity == "FAIL"
        assert findings[0].context["required"] == 2  # The missing quantity
        assert findings[0].context["provided"] == 0  # No additional provision

    def test_reconcile_phantom_items(self, sample_policy):
        """Test reconciliation with phantom items."""
        bom_structure = {"leaf-spine": {"qsfp28_100g": {7: 6}}}  # Extra 2
        intent_structure = {"leaf-spine": {"qsfp28_100g": {7: 4}}}

        findings = _reconcile_bom_vs_intent(bom_structure, intent_structure, sample_policy)
        assert len(findings) == 1
        assert findings[0].code == "PHANTOM_ITEM"
        assert findings[0].severity == "WARN"
        assert findings[0].context["required"] == 0  # No requirement for phantom items
        assert findings[0].context["provided"] == 2  # The extra quantity

    def test_reconcile_bin_mismatch_warn(self, sample_policy):
        """Test reconciliation with bin mismatch within slop tolerance."""
        bom_structure = {"leaf-node": {"sfp28_25g": {5: 8}}}  # 5m instead of 3m (within 2m slop)
        intent_structure = {"leaf-node": {"sfp28_25g": {3: 8}}}

        findings = _reconcile_bom_vs_intent(bom_structure, intent_structure, sample_policy)
        assert len(findings) == 1
        assert findings[0].code == "BIN_MISMATCH_WARN"
        assert findings[0].severity == "WARN"
        assert findings[0].context["bom_bin_m"] == 5
        assert findings[0].context["intent_bin_m"] == 3

    def test_reconcile_bin_mismatch_fail(self, sample_policy):
        """Test reconciliation with bin mismatch outside tolerance."""
        bom_structure = {"leaf-node": {"sfp28_25g": {1: 8}}}  # 1m instead of 3m (too small)
        intent_structure = {"leaf-node": {"sfp28_25g": {3: 8}}}

        findings = _reconcile_bom_vs_intent(bom_structure, intent_structure, sample_policy)
        assert len(findings) == 1
        assert findings[0].code == "BIN_MISMATCH_FAIL"
        assert findings[0].severity == "FAIL"
        assert findings[0].context["bom_bin_m"] == 1
        assert findings[0].context["intent_bin_m"] == 3


class TestCrossValidationIntegration:
    """Integration tests for cross-validation."""

    @patch("inferno_tools.cabling.cross_validate.load_topology")
    @patch("inferno_tools.cabling.cross_validate.load_tors")
    @patch("inferno_tools.cabling.cross_validate.load_nodes")
    @patch("inferno_tools.cabling.cross_validate.load_site")
    @patch("inferno_tools.cabling.cross_validate.load_cabling_policy")
    def test_cross_validate_bom_happy_path(
        self,
        mock_policy,
        mock_site,
        mock_nodes,
        mock_tors,
        mock_topology,
        sample_topology,
        sample_tors,
        sample_nodes,
        sample_site,
        sample_policy,
        happy_bom,
    ):
        """Test full cross-validation with happy path."""
        # Setup mocks
        mock_topology.return_value = MagicMock()
        mock_topology.return_value.model_dump.return_value = sample_topology
        mock_tors.return_value = MagicMock()
        mock_tors.return_value.model_dump.return_value = sample_tors
        mock_nodes.return_value = MagicMock()
        mock_nodes.return_value.model_dump.return_value = sample_nodes
        mock_site.return_value = MagicMock()
        mock_site.return_value.model_dump.return_value = sample_site
        mock_policy.return_value = sample_policy

        # Create temporary BOM file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(happy_bom, f)
            bom_path = f.name

        try:
            # Run cross-validation
            report = cross_validate_bom(bom_path=bom_path)

            # Check results
            assert isinstance(report, CrossReport)
            assert report.summary["missing"] == 0
            assert report.summary["phantom"] == 0
            assert len(report.findings) == 0

        finally:
            Path(bom_path).unlink()

    @patch("inferno_tools.cabling.cross_validate.load_topology")
    @patch("inferno_tools.cabling.cross_validate.load_tors")
    @patch("inferno_tools.cabling.cross_validate.load_nodes")
    @patch("inferno_tools.cabling.cross_validate.load_site")
    @patch("inferno_tools.cabling.cross_validate.load_cabling_policy")
    def test_cross_validate_bom_missing_links(
        self,
        mock_policy,
        mock_site,
        mock_nodes,
        mock_tors,
        mock_topology,
        sample_topology,
        sample_tors,
        sample_nodes,
        sample_site,
        sample_policy,
        missing_leaf_node_bom,
    ):
        """Test cross-validation with missing links."""
        # Setup mocks
        mock_topology.return_value = MagicMock()
        mock_topology.return_value.model_dump.return_value = sample_topology
        mock_tors.return_value = MagicMock()
        mock_tors.return_value.model_dump.return_value = sample_tors
        mock_nodes.return_value = MagicMock()
        mock_nodes.return_value.model_dump.return_value = sample_nodes
        mock_site.return_value = MagicMock()
        mock_site.return_value.model_dump.return_value = sample_site
        mock_policy.return_value = sample_policy

        # Create temporary BOM file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(missing_leaf_node_bom, f)
            bom_path = f.name

        try:
            # Run cross-validation
            report = cross_validate_bom(bom_path=bom_path)

            # Check results
            assert isinstance(report, CrossReport)
            assert report.summary["missing"] > 0
            assert any(f.code == "MISSING_LINK" for f in report.findings)
            assert any(f.severity == "FAIL" for f in report.findings)

        finally:
            Path(bom_path).unlink()

    @patch("inferno_tools.cabling.cross_validate.load_topology")
    @patch("inferno_tools.cabling.cross_validate.load_tors")
    @patch("inferno_tools.cabling.cross_validate.load_nodes")
    @patch("inferno_tools.cabling.cross_validate.load_site")
    @patch("inferno_tools.cabling.cross_validate.load_cabling_policy")
    def test_cross_validate_bom_phantom_items(
        self,
        mock_policy,
        mock_site,
        mock_nodes,
        mock_tors,
        mock_topology,
        sample_topology,
        sample_tors,
        sample_nodes,
        sample_site,
        sample_policy,
        phantom_leaf_spine_bom,
    ):
        """Test cross-validation with phantom items."""
        # Setup mocks
        mock_topology.return_value = MagicMock()
        mock_topology.return_value.model_dump.return_value = sample_topology
        mock_tors.return_value = MagicMock()
        mock_tors.return_value.model_dump.return_value = sample_tors
        mock_nodes.return_value = MagicMock()
        mock_nodes.return_value.model_dump.return_value = sample_nodes
        mock_site.return_value = MagicMock()
        mock_site.return_value.model_dump.return_value = sample_site
        mock_policy.return_value = sample_policy

        # Create temporary BOM file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(phantom_leaf_spine_bom, f)
            bom_path = f.name

        try:
            # Run cross-validation
            report = cross_validate_bom(bom_path=bom_path)

            # Check results
            assert isinstance(report, CrossReport)
            assert report.summary["phantom"] > 0
            assert any(f.code == "PHANTOM_ITEM" for f in report.findings)
            assert any(f.severity == "WARN" for f in report.findings)

        finally:
            Path(bom_path).unlink()

    def test_cross_validate_bom_load_error(self):
        """Test cross-validation with load error."""
        # Use non-existent BOM file
        report = cross_validate_bom(bom_path="nonexistent.yaml")

        # Check error handling
        assert isinstance(report, CrossReport)
        assert len(report.findings) == 1
        assert report.findings[0].code == "LOAD_ERROR"
        assert report.findings[0].severity == "FAIL"
