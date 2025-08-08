"""
Test geometry validation for cabling.

Tests the validation side of geometry handling to ensure validation engine
produces correct finding codes for each fixture scenario.
"""

from pathlib import Path

import pytest
from inferno_core.data.network_loader import (
    load_nodes,
    load_site,
    load_topology,
    load_tors,
)
from inferno_core.validation.cabling import _load_policy, validate_lengths


class TestGeometryValidation:
    """Test geometry validation using the test fixtures."""

    @pytest.fixture
    def fixtures_path(self):
        """Path to geometry test fixtures."""
        return Path(__file__).parent.parent.parent / "inferno-tools" / "tests" / "fixtures" / "cabling" / "geometry"

    def _load_fixture_data(self, fixture_name, fixtures_path):
        """Load all data files for a fixture."""
        fixture_path = fixtures_path / fixture_name

        # Load policy
        policy_path = fixture_path / "cabling-policy.yaml"
        policy = _load_policy(str(policy_path))

        # Load topology
        topology_path = fixture_path / "topology.yaml"
        topology = load_topology(str(topology_path))

        # Load tors
        tors_path = fixture_path / "tors.yaml"
        tors_list, spine_rec = load_tors(str(tors_path))
        tors = {tor.id: tor for tor in tors_list}

        # Load nodes
        nodes_path = fixture_path / "nodes.yaml"
        nodes = load_nodes(str(nodes_path))

        # Load site (may not exist for no_site fixture)
        site_path = fixture_path / "site.yaml"
        site = None
        if site_path.exists():
            site = load_site(str(site_path))

        return topology, tors, nodes, site, policy

    def test_boundary_equal_validation(self, fixtures_path):
        """Test boundary_equal fixture - should PASS with no findings."""
        topology, tors, nodes, site, policy = self._load_fixture_data("boundary_equal", fixtures_path)

        findings = validate_lengths(topology, tors, nodes, site, policy)

        # Should have no FAIL or WARN findings for length issues
        length_findings = [f for f in findings if f.code.startswith("LENGTH_")]
        assert len(length_findings) == 0, f"Expected no length findings, got: {[f.code for f in length_findings]}"

    def test_just_over_threshold_validation(self, fixtures_path):
        """Test just_over_threshold fixture - should PASS (AOC available)."""
        topology, tors, nodes, site, policy = self._load_fixture_data("just_over_threshold", fixtures_path)

        findings = validate_lengths(topology, tors, nodes, site, policy)

        # Should have no FAIL findings since AOC bins are available
        fail_findings = [f for f in findings if f.severity == "FAIL"]
        assert len(fail_findings) == 0, f"Expected no FAIL findings, got: {[f.code for f in fail_findings]}"

    def test_far_racks_validation(self, fixtures_path):
        """Test far_racks fixture - should FAIL with LENGTH_EXCEEDS_MAX_BIN."""
        topology, tors, nodes, site, policy = self._load_fixture_data("far_racks", fixtures_path)

        findings = validate_lengths(topology, tors, nodes, site, policy)

        # Should have LENGTH_EXCEEDS_MAX_BIN FAIL finding
        max_bin_findings = [f for f in findings if f.code == "LENGTH_EXCEEDS_MAX_BIN"]
        assert len(max_bin_findings) > 0, "Expected LENGTH_EXCEEDS_MAX_BIN finding"

        # Check that it's a FAIL severity
        fail_finding = max_bin_findings[0]
        assert fail_finding.severity == "FAIL"
        assert "rack-02" in fail_finding.context.get("rack_id", "")
        assert fail_finding.context.get("media_class") == "QSFP28"
        assert fail_finding.context.get("distance_m") > 10  # Should exceed 10m max bin

    def test_no_site_validation(self, fixtures_path):
        """Test no_site fixture - should emit SITE_GEOMETRY_MISSING INFO."""
        # Load fixture data without site.yaml
        fixture_path = fixtures_path / "no_site"

        policy_path = fixture_path / "cabling-policy.yaml"
        policy = _load_policy(str(policy_path))

        topology_path = fixture_path / "topology.yaml"
        topology = load_topology(str(topology_path))

        tors_path = fixture_path / "tors.yaml"
        tors_list, spine_rec = load_tors(str(tors_path))
        tors = {tor.id: tor for tor in tors_list}

        nodes_path = fixture_path / "nodes.yaml"
        nodes = load_nodes(str(nodes_path))

        # No site.yaml - should be None
        site = None

        findings = validate_lengths(topology, tors, nodes, site, policy)

        # Should have SITE_GEOMETRY_MISSING INFO finding
        geometry_findings = [f for f in findings if f.code == "SITE_GEOMETRY_MISSING"]
        assert len(geometry_findings) == 1, "Expected SITE_GEOMETRY_MISSING finding"

        geometry_finding = geometry_findings[0]
        assert geometry_finding.severity == "INFO"
        assert "geometry-based length checks skipped" in geometry_finding.message

    def test_rj45_long_validation(self, fixtures_path):
        """Test rj45_long fixture - should WARN with RJ45_BIN_GT_100M."""
        topology, tors, nodes, site, policy = self._load_fixture_data("rj45_long", fixtures_path)

        findings = validate_lengths(topology, tors, nodes, site, policy)

        # Should have RJ45_BIN_GT_100M WARN finding
        rj45_findings = [f for f in findings if f.code == "RJ45_BIN_GT_100M"]
        assert len(rj45_findings) > 0, "Expected RJ45_BIN_GT_100M finding"

        # Check that it's a WARN severity
        warn_finding = rj45_findings[0]
        assert warn_finding.severity == "WARN"
        assert warn_finding.context.get("media_class") == "RJ45"
        assert warn_finding.context.get("bin") > 100  # Should be 150m bin
        assert "speed may downshift" in warn_finding.message

    def test_slack_variants_consistency(self, fixtures_path):
        """Test slack_variants fixtures - different slack should produce different results."""
        # Load both slack variants
        topology_1_0, tors_1_0, nodes_1_0, site_1_0, policy_1_0 = self._load_fixture_data(
            "slack_variants/slack_1_0", fixtures_path
        )
        topology_1_5, tors_1_5, nodes_1_5, site_1_5, policy_1_5 = self._load_fixture_data(
            "slack_variants/slack_1_5", fixtures_path
        )

        findings_1_0 = validate_lengths(topology_1_0, tors_1_0, nodes_1_0, site_1_0, policy_1_0)
        findings_1_5 = validate_lengths(topology_1_5, tors_1_5, nodes_1_5, site_1_5, policy_1_5)

        # Both should pass (no FAIL findings) but may have different behavior
        fail_findings_1_0 = [f for f in findings_1_0 if f.severity == "FAIL"]
        fail_findings_1_5 = [f for f in findings_1_5 if f.severity == "FAIL"]

        assert len(fail_findings_1_0) == 0, f"slack_1_0 should not fail: {[f.code for f in fail_findings_1_0]}"
        assert len(fail_findings_1_5) == 0, f"slack_1_5 should not fail: {[f.code for f in fail_findings_1_5]}"

    def test_tile_variants_validation(self, fixtures_path):
        """Test tile_variants fixture - larger tiles should produce longer distances."""
        topology, tors, nodes, site, policy = self._load_fixture_data("tile_variants", fixtures_path)

        findings = validate_lengths(topology, tors, nodes, site, policy)

        # With tile_m=2.0, distances should be larger but still within acceptable range
        # Should not fail since bins go up to 10m and calculated distance should be 4.8m
        fail_findings = [f for f in findings if f.severity == "FAIL"]
        assert len(fail_findings) == 0, f"tile_variants should not fail: {[f.code for f in fail_findings]}"

    def test_finding_context_completeness(self, fixtures_path):
        """Test that findings include complete context information."""
        # Use far_racks fixture which should produce LENGTH_EXCEEDS_MAX_BIN
        topology, tors, nodes, site, policy = self._load_fixture_data("far_racks", fixtures_path)

        findings = validate_lengths(topology, tors, nodes, site, policy)

        max_bin_findings = [f for f in findings if f.code == "LENGTH_EXCEEDS_MAX_BIN"]
        assert len(max_bin_findings) > 0

        finding = max_bin_findings[0]
        context = finding.context

        # Check required context fields
        assert "rack_id" in context
        assert "distance_m" in context
        assert "bin" in context
        assert "media_class" in context

        # Check values are reasonable
        assert isinstance(context["distance_m"], int | float)
        assert context["distance_m"] > 0
        assert isinstance(context["bin"], int)
        assert context["bin"] > 0
        assert context["media_class"] in ["SFP28", "QSFP28", "RJ45"]


class TestGeometryIntegration:
    """Test integration between calculation and validation paths."""

    @pytest.fixture
    def fixtures_path(self):
        """Path to geometry test fixtures."""
        return Path(__file__).parent.parent.parent / "inferno-tools" / "tests" / "fixtures" / "cabling" / "geometry"

    def test_shared_helpers_consistency(self):
        """Test that shared helpers produce consistent results."""
        from inferno_tools.cabling.common import (
            apply_slack,
            compute_rack_distance_m,
            select_length_bin,
        )

        # Test same calculations used in both paths
        base_distance = compute_rack_distance_m((0, 0), (3, 2), 1.0)
        assert base_distance == 5.0  # Manhattan distance

        slacked_distance = apply_slack(base_distance, 1.2)
        assert slacked_distance == 6.0

        bins = [1, 3, 5, 10]
        selected_bin = select_length_bin(slacked_distance, bins)
        assert selected_bin == 10

        # These same calculations should be used in both calculation and validation

    def test_boundary_conditions(self):
        """Test boundary conditions for media selection."""
        from inferno_tools.cabling.common import select_length_bin

        bins = [1, 3, 5, 10]

        # Test exact boundary conditions
        assert select_length_bin(3.0, bins) == 3  # Exact match should select that bin
        assert select_length_bin(3.0001, bins) == 5  # Just over should select next bin
        assert select_length_bin(2.9999, bins) == 3  # Just under should select same bin

        # Test edge cases
        assert select_length_bin(0.0, bins) == 1  # Zero distance
        assert select_length_bin(10.0, bins) == 10  # Exact max
        assert select_length_bin(10.0001, bins) is None  # Just over max
