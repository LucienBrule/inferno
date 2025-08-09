#!/usr/bin/env python3
"""
Demonstration script for TASK.cabling.geometry-stress functionality.
This script validates that all geometry features are working correctly.
"""

import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path("packages/inferno-tools/src")))
sys.path.insert(0, str(Path("packages/inferno-core/src")))

from inferno_core.data.network_loader import (
    load_nodes,
    load_site,
    load_topology,
    load_tors,
)
from inferno_core.validation.cabling import _load_policy, validate_lengths
from inferno_tools.cabling.common import (
    apply_slack,
    compute_rack_distance_m,
    select_length_bin,
)


def test_shared_helpers():
    """Test the shared geometry helper functions."""
    print("Testing shared geometry helpers...")

    # Test Manhattan distance calculation
    distance = compute_rack_distance_m((0, 0), (3, 2), 1.0)
    assert distance == 5.0, f"Expected 5.0, got {distance}"
    print("✓ Manhattan distance calculation works")

    # Test slack application
    slacked = apply_slack(10.0, 1.2)
    assert slacked == 12.0, f"Expected 12.0, got {slacked}"
    print("✓ Slack factor application works")

    # Test length bin selection
    bins = [1, 3, 5, 10]
    selected = select_length_bin(3.1, bins)
    assert selected == 5, f"Expected 5, got {selected}"
    print("✓ Length bin selection works")

    # Test boundary condition
    selected = select_length_bin(3.0, bins)
    assert selected == 3, f"Expected 3, got {selected}"
    print("✓ Boundary condition (exact match) works")

    # Test exceeds all bins
    selected = select_length_bin(15.0, bins)
    assert selected is None, f"Expected None, got {selected}"
    print("✓ Exceeds all bins handling works")


def test_geometry_fixture():
    """Test geometry validation with a specific fixture."""
    print("\nTesting geometry validation with far_racks fixture...")

    fixture_path = Path("packages/inferno-tools/tests/fixtures/cabling/geometry/far_racks")

    # Load fixture data
    policy = _load_policy(str(fixture_path / "cabling-policy.yaml"))
    topology = load_topology(str(fixture_path / "topology.yaml"))
    tors_list, spine_rec = load_tors(str(fixture_path / "tors.yaml"))
    tors = {tor.id: tor for tor in tors_list}
    nodes = load_nodes(str(fixture_path / "nodes.yaml"))
    site = load_site(str(fixture_path / "site.yaml"))

    # Run validation
    findings = validate_lengths(topology, tors, nodes, site, policy)

    # Check for expected LENGTH_EXCEEDS_MAX_BIN finding
    max_bin_findings = [f for f in findings if f.code == "LENGTH_EXCEEDS_MAX_BIN"]
    assert len(max_bin_findings) > 0, "Expected LENGTH_EXCEEDS_MAX_BIN finding"

    finding = max_bin_findings[0]
    assert finding.severity == "FAIL", f"Expected FAIL, got {finding.severity}"
    assert "rack-02" in finding.context.get("rack_id", ""), "Expected rack-02 in context"
    assert finding.context.get("media_class") == "QSFP28", "Expected QSFP28 media class"
    assert finding.context.get("distance_m", 0) > 10, "Expected distance > 10m"

    print("✓ far_racks fixture produces expected LENGTH_EXCEEDS_MAX_BIN finding")
    print(f"  - Severity: {finding.severity}")
    print(f"  - Rack: {finding.context.get('rack_id')}")
    print(f"  - Distance: {finding.context.get('distance_m'):.1f}m")
    print(f"  - Max bin: {finding.context.get('bin')}m")


def test_no_site_fixture():
    """Test validation behavior when site.yaml is missing."""
    print("\nTesting no_site fixture...")

    fixture_path = Path("packages/inferno-tools/tests/fixtures/cabling/geometry/no_site")

    # Load fixture data (no site.yaml)
    policy = _load_policy(str(fixture_path / "cabling-policy.yaml"))
    topology = load_topology(str(fixture_path / "topology.yaml"))
    tors_list, spine_rec = load_tors(str(fixture_path / "tors.yaml"))
    tors = {tor.id: tor for tor in tors_list}
    nodes = load_nodes(str(fixture_path / "nodes.yaml"))
    site = None  # No site.yaml

    # Run validation
    findings = validate_lengths(topology, tors, nodes, site, policy)

    # Check for expected SITE_GEOMETRY_MISSING finding
    geometry_findings = [f for f in findings if f.code == "SITE_GEOMETRY_MISSING"]
    assert len(geometry_findings) == 1, "Expected SITE_GEOMETRY_MISSING finding"

    finding = geometry_findings[0]
    assert finding.severity == "INFO", f"Expected INFO, got {finding.severity}"

    print("✓ no_site fixture produces expected SITE_GEOMETRY_MISSING finding")
    print(f"  - Severity: {finding.severity}")
    print(f"  - Message: {finding.message}")
