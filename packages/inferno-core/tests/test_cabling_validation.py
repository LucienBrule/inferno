"""
Tests for cabling validation module.

Covers all validation scenarios specified in TASK.cabling.validation.md.
"""

from unittest.mock import patch

import pytest
from inferno_core.models.cabling_report import Report
from inferno_core.models.records import (
    NicRec,
    NodeRec,
    SiteRackRec,
    SiteRec,
    SpinePorts,
    SpineRec,
    TopologyRackRec,
    TopologyRec,
    TopologyWanRec,
    TorPorts,
    TorRec,
)
from inferno_core.validation.cabling import (
    run_cabling_validation,
    validate_compatibility,
    validate_completeness,
    validate_lengths,
    validate_oversubscription,
    validate_policy_sanity,
    validate_ports,
    validate_redundancy,
)


@pytest.fixture
def sample_policy():
    """Sample policy configuration for testing."""
    return {
        "defaults": {
            "nodes_25g_per_node": 2,
            "mgmt_rj45_per_node": 1,
            "tor_uplink_qsfp28_per_tor": 4,
            "spares_fraction": 0.1,
        },
        "site_defaults": {
            "num_racks": 10,
            "nodes_per_rack": 20,
            "uplinks_per_rack": 4,
            "mgmt_rj45_per_node": 1,
            "wan_cat6a": 2,
        },
        "media_rules": {
            "sfp28_25g": {"dac_max_m": 3, "bins_m": [1, 3, 5, 10, 30]},
            "qsfp28_100g": {"dac_max_m": 3, "bins_m": [1, 3, 5, 10, 30]},
            "rj45_cat6a": {"dac_max_m": 100, "bins_m": [1, 3, 5, 10, 30, 100]},
        },
        "redundancy": {"node_dual_homing": False, "tor_uplinks_min": 2},
        "oversubscription": {"max_leaf_to_spine_ratio": 4.0},
        "heuristics": {
            "same_rack_leaf_to_node_m": 2,
            "adjacent_rack_leaf_to_spine_m": 10,
            "non_adjacent_rack_leaf_to_spine_m": 30,
            "slack_factor": 1.2,
        },
    }


@pytest.fixture
def sample_nodes():
    """Sample node configuration for testing."""
    return [
        NodeRec(id="node-1", rack_id="rack-1", hostname="node-1.example.com", nics=[NicRec(type="SFP28", count=2)]),
        NodeRec(id="node-2", rack_id="rack-1", hostname="node-2.example.com", nics=[NicRec(type="SFP28", count=2)]),
        NodeRec(id="node-3", rack_id="rack-2", hostname="node-3.example.com", nics=[NicRec(type="SFP28", count=2)]),
    ]


@pytest.fixture
def sample_tors():
    """Sample ToR configuration for testing."""
    return {
        "tor-1": TorRec(
            id="tor-1", rack_id="rack-1", model="switch-48x25g", ports=TorPorts(sfp28_total=48, qsfp28_total=8)
        ),
        "tor-2": TorRec(
            id="tor-2", rack_id="rack-2", model="switch-48x25g", ports=TorPorts(sfp28_total=48, qsfp28_total=8)
        ),
    }


@pytest.fixture
def sample_topology():
    """Sample topology configuration for testing."""
    return TopologyRec(
        spine=SpineRec(id="spine-1", model="spine-switch", ports=SpinePorts(qsfp28_total=32)),
        racks=[
            TopologyRackRec(rack_id="rack-1", tor_id="tor-1", uplinks_qsfp28=4),
            TopologyRackRec(rack_id="rack-2", tor_id="tor-2", uplinks_qsfp28=4),
        ],
        wan=TopologyWanRec(uplinks_cat6a=2),
    )


@pytest.fixture
def sample_site():
    """Sample site configuration for testing."""
    return SiteRec(
        racks=[
            SiteRackRec(id="rack-1", grid=(0, 0), tor_position_u=42),
            SiteRackRec(id="rack-2", grid=(1, 0), tor_position_u=42),
        ]
    )


class TestHappyPath:
    """Test cases for successful validation scenarios."""

    def test_happy_path_validation(self, sample_topology, sample_tors, sample_nodes, sample_site, sample_policy):
        """Test that a well-configured setup passes all validations."""
        findings = []

        # Run all validation functions
        findings.extend(validate_policy_sanity(sample_policy))
        findings.extend(validate_ports(sample_topology, sample_tors, sample_nodes, sample_policy))
        findings.extend(validate_compatibility(sample_topology, sample_tors, sample_nodes, sample_policy))
        findings.extend(validate_oversubscription(sample_topology, sample_tors, sample_nodes, sample_policy))
        findings.extend(validate_completeness(sample_topology, sample_tors, sample_nodes, sample_site, sample_policy))
        findings.extend(validate_lengths(sample_topology, sample_tors, sample_nodes, sample_site, sample_policy))
        findings.extend(validate_redundancy(sample_topology, sample_tors, sample_nodes, sample_policy))

        # Should have minimal findings (only INFO messages)
        fail_findings = [f for f in findings if f.severity == "FAIL"]
        warn_findings = [f for f in findings if f.severity == "WARN"]

        assert len(fail_findings) == 0, f"Unexpected failures: {[f.message for f in fail_findings]}"
        # Some warnings are expected (like mgmt RJ45 unvalidated)
        assert len(warn_findings) <= 2, f"Too many warnings: {[f.message for f in warn_findings]}"


class TestPortCapacityValidation:
    """Test cases for port capacity validation."""

    def test_deficit_sfp28_ports(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test SFP28 port deficit detection."""
        # Create a scenario where nodes need more SFP28 ports than available
        nodes_with_many_nics = [
            NodeRec(id="node-1", rack_id="rack-1", nics=[NicRec(type="SFP28", count=30)]),
            NodeRec(id="node-2", rack_id="rack-1", nics=[NicRec(type="SFP28", count=30)]),
        ]

        findings = validate_ports(sample_topology, sample_tors, nodes_with_many_nics, sample_policy)

        # Should find SFP28 deficit
        deficit_findings = [f for f in findings if f.code == "PORT_CAPACITY_TOR_SFP28"]
        assert len(deficit_findings) == 1
        assert deficit_findings[0].severity == "FAIL"
        assert "deficit" in deficit_findings[0].message
        assert deficit_findings[0].context["deficit"] == 12  # 60 required - 48 available

    def test_deficit_spine_qsfp28(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test spine QSFP28 port deficit detection."""
        # Create topology with more uplinks than spine capacity
        topology_with_many_uplinks = TopologyRec(
            spine=SpineRec(id="spine-1", model="spine-switch", ports=SpinePorts(qsfp28_total=4)),
            racks=[
                TopologyRackRec(rack_id="rack-1", tor_id="tor-1", uplinks_qsfp28=4),
                TopologyRackRec(rack_id="rack-2", tor_id="tor-2", uplinks_qsfp28=4),
            ],
            wan=TopologyWanRec(uplinks_cat6a=2),
        )

        findings = validate_ports(topology_with_many_uplinks, sample_tors, sample_nodes, sample_policy)

        # Should find spine deficit
        deficit_findings = [f for f in findings if f.code == "PORT_CAPACITY_SPINE_QSFP28"]
        assert len(deficit_findings) == 1
        assert deficit_findings[0].severity == "FAIL"
        assert deficit_findings[0].context["deficit"] == 4  # 8 required - 4 available

    def test_spine_near_capacity_warning(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test spine near capacity warning."""
        # Create topology with spine at 96% capacity
        topology_near_limit = TopologyRec(
            spine=SpineRec(id="spine-1", model="spine-switch", ports=SpinePorts(qsfp28_total=8)),
            racks=[
                TopologyRackRec(rack_id="rack-1", tor_id="tor-1", uplinks_qsfp28=4),
                TopologyRackRec(rack_id="rack-2", tor_id="tor-2", uplinks_qsfp28=4),
            ],
            wan=TopologyWanRec(uplinks_cat6a=2),
        )

        findings = validate_ports(topology_near_limit, sample_tors, sample_nodes, sample_policy)

        # Should find near capacity warning
        warn_findings = [f for f in findings if f.code == "PORT_CAPACITY_SPINE_NEAR_LIMIT"]
        assert len(warn_findings) == 1
        assert warn_findings[0].severity == "WARN"
        assert warn_findings[0].context["utilization"] == 1.0  # 8/8 = 100%


class TestOversubscriptionValidation:
    """Test cases for oversubscription ratio validation."""

    def test_oversubscription_warning(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test oversubscription ratio warning (≤25% over policy)."""
        # Create nodes with high bandwidth demand that will exceed policy by ≤25%
        # Policy max is 4.0:1, so we want ratio around 4.5:1 to 5.0:1
        high_bandwidth_nodes = [
            NodeRec(id="node-1", rack_id="rack-1", nics=[NicRec(type="SFP28", count=9)]),
            NodeRec(id="node-2", rack_id="rack-1", nics=[NicRec(type="SFP28", count=9)]),
        ]

        # Topology with limited uplinks to create 4.5:1 ratio
        limited_topology = TopologyRec(
            spine=SpineRec(id="spine-1", model="spine-switch", ports=SpinePorts(qsfp28_total=32)),
            racks=[TopologyRackRec(rack_id="rack-1", tor_id="tor-1", uplinks_qsfp28=1)],  # Only 100 Gbps uplink
            wan=TopologyWanRec(uplinks_cat6a=2),
        )

        findings = validate_oversubscription(limited_topology, sample_tors, high_bandwidth_nodes, sample_policy)

        # Should find oversubscription warning
        oversub_findings = [f for f in findings if f.code == "OVERSUB_RATIO"]
        assert len(oversub_findings) == 1
        assert oversub_findings[0].severity == "WARN"
        # 18 NICs * 25 Gbps = 450 Gbps edge, 1 * 100 Gbps = 100 Gbps uplink → 4.5:1 ratio
        assert oversub_findings[0].context["ratio"] == 4.5

    def test_oversubscription_critical_failure(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test oversubscription ratio critical failure (>25% over policy)."""
        # Create nodes with very high bandwidth demand
        very_high_bandwidth_nodes = [
            NodeRec(id="node-1", rack_id="rack-1", nics=[NicRec(type="SFP28", count=20)]),
            NodeRec(id="node-2", rack_id="rack-1", nics=[NicRec(type="SFP28", count=20)]),
        ]

        # Topology with very limited uplinks
        very_limited_topology = TopologyRec(
            spine=SpineRec(id="spine-1", model="spine-switch", ports=SpinePorts(qsfp28_total=32)),
            racks=[TopologyRackRec(rack_id="rack-1", tor_id="tor-1", uplinks_qsfp28=1)],  # Only 100 Gbps uplink
            wan=TopologyWanRec(uplinks_cat6a=2),
        )

        findings = validate_oversubscription(
            very_limited_topology, sample_tors, very_high_bandwidth_nodes, sample_policy
        )

        # Should find critical oversubscription failure
        oversub_findings = [f for f in findings if f.code == "OVERSUB_RATIO_CRITICAL"]
        assert len(oversub_findings) == 1
        assert oversub_findings[0].severity == "FAIL"
        # 40 NICs * 25 Gbps = 1000 Gbps edge, 1 * 100 Gbps = 100 Gbps uplink → 10:1 ratio
        assert oversub_findings[0].context["ratio"] == 10.0

    def test_no_uplinks_failure(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test failure when rack has edge bandwidth but no uplinks."""
        # Topology with no uplinks
        no_uplinks_topology = TopologyRec(
            spine=SpineRec(id="spine-1", model="spine-switch", ports=SpinePorts(qsfp28_total=32)),
            racks=[TopologyRackRec(rack_id="rack-1", tor_id="tor-1", uplinks_qsfp28=0)],
            wan=TopologyWanRec(uplinks_cat6a=2),
        )

        findings = validate_oversubscription(no_uplinks_topology, sample_tors, sample_nodes, sample_policy)

        # Should find no uplinks failure
        no_uplinks_findings = [f for f in findings if f.code == "OVERSUB_NO_UPLINKS"]
        assert len(no_uplinks_findings) == 1
        assert no_uplinks_findings[0].severity == "FAIL"


class TestCompletenessValidation:
    """Test cases for connection completeness validation."""

    def test_missing_tor_mapping(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test failure when topology references unknown ToR."""
        # Topology referencing non-existent ToR
        bad_topology = TopologyRec(
            spine=SpineRec(id="spine-1", model="spine-switch", ports=SpinePorts(qsfp28_total=32)),
            racks=[TopologyRackRec(rack_id="rack-1", tor_id="unknown-tor", uplinks_qsfp28=4)],
            wan=TopologyWanRec(uplinks_cat6a=2),
        )

        findings = validate_completeness(bad_topology, sample_tors, sample_nodes, None, sample_policy)

        # Should find missing ToR
        missing_tor_findings = [f for f in findings if f.code == "COMPLETENESS_MISSING_TOR"]
        assert len(missing_tor_findings) == 1
        assert missing_tor_findings[0].severity == "FAIL"
        assert "unknown-tor" in missing_tor_findings[0].message

    def test_tor_rack_mismatch(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test failure when ToR rack_id doesn't match topology rack_id."""
        # ToR with mismatched rack_id
        bad_tors = {
            "tor-1": TorRec(
                id="tor-1",
                rack_id="wrong-rack",  # Should be "rack-1"
                model="switch-48x25g",
                ports=TorPorts(sfp28_total=48, qsfp28_total=8),
            )
        }

        findings = validate_completeness(sample_topology, bad_tors, sample_nodes, None, sample_policy)

        # Should find rack mismatch
        mismatch_findings = [f for f in findings if f.code == "COMPLETENESS_TOR_RACK_MISMATCH"]
        assert len(mismatch_findings) == 1
        assert mismatch_findings[0].severity == "FAIL"

    def test_missing_spine(self, sample_tors, sample_nodes, sample_policy):
        """Test failure when spine has no ports defined."""
        # Topology with spine that has no ports
        no_ports_spine_topology = TopologyRec(
            spine=SpineRec(id="spine-1", model="spine-switch", ports=SpinePorts(qsfp28_total=0)),
            racks=[TopologyRackRec(rack_id="rack-1", tor_id="tor-1", uplinks_qsfp28=4)],
            wan=TopologyWanRec(uplinks_cat6a=2),
        )

        findings = validate_completeness(no_ports_spine_topology, sample_tors, sample_nodes, None, sample_policy)

        # Should find spine with no ports
        missing_spine_findings = [f for f in findings if f.code == "COMPLETENESS_SPINE_NO_PORTS"]
        assert len(missing_spine_findings) == 1
        assert missing_spine_findings[0].severity == "FAIL"


class TestLengthValidation:
    """Test cases for cable length feasibility validation."""

    def test_length_checks_skipped_no_site(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test that length checks are skipped when no site.yaml is present."""
        findings = validate_lengths(sample_topology, sample_tors, sample_nodes, None, sample_policy)

        # Should find info message about skipped checks
        skipped_findings = [f for f in findings if f.code == "SITE_GEOMETRY_MISSING"]
        assert len(skipped_findings) == 1
        assert skipped_findings[0].severity == "INFO"

    def test_length_exceeds_dac_with_aoc_available(
        self, sample_topology, sample_tors, sample_nodes, sample_site, sample_policy
    ):
        """Test that no failures occur when length exceeds DAC but AOC bins are available."""
        # Policy with very short DAC limit but longer bins available
        short_dac_policy = sample_policy.copy()
        short_dac_policy["heuristics"]["same_rack_leaf_to_node_m"] = 5  # 5m * 1.2 slack = 6m
        short_dac_policy["media_rules"]["sfp28_25g"]["dac_max_m"] = 3  # DAC only up to 3m

        findings = validate_lengths(sample_topology, sample_tors, sample_nodes, sample_site, short_dac_policy)

        # Should have no FAIL findings since AOC bins are available
        fail_findings = [f for f in findings if f.severity == "FAIL"]
        assert len(fail_findings) == 0

    def test_length_exceeds_all_bins(self, sample_topology, sample_tors, sample_nodes, sample_site, sample_policy):
        """Test failure when length exceeds all available bins."""
        # Policy with very short bins
        short_bins_policy = sample_policy.copy()
        short_bins_policy["heuristics"]["same_rack_leaf_to_node_m"] = 50  # 50m * 1.2 slack = 60m
        short_bins_policy["media_rules"]["sfp28_25g"]["bins_m"] = [1, 3, 5]  # Max 5m

        findings = validate_lengths(sample_topology, sample_tors, sample_nodes, sample_site, short_bins_policy)

        # Should find length exceeds bins failure
        exceeds_findings = [f for f in findings if f.code == "LENGTH_EXCEEDS_MAX_BIN"]
        assert len(exceeds_findings) >= 1
        assert all(f.severity == "FAIL" for f in exceeds_findings)


class TestRedundancyValidation:
    """Test cases for redundancy rules validation."""

    def test_dual_homing_odd_nics_failure(self, sample_topology, sample_tors, sample_policy):
        """Test failure when dual homing is required but node has odd NIC count."""
        # Enable dual homing
        dual_homing_policy = sample_policy.copy()
        dual_homing_policy["redundancy"]["node_dual_homing"] = True

        # Node with odd NIC count
        odd_nic_nodes = [NodeRec(id="node-1", rack_id="rack-1", nics=[NicRec(type="SFP28", count=3)])]

        findings = validate_redundancy(sample_topology, sample_tors, odd_nic_nodes, dual_homing_policy)

        # Should find dual homing failure
        dual_homing_findings = [f for f in findings if f.code == "REDUNDANCY_DUAL_HOMING"]
        assert len(dual_homing_findings) == 1
        assert dual_homing_findings[0].severity == "FAIL"
        assert dual_homing_findings[0].context["nic_count"] == 3

    def test_tor_uplinks_minimum_failure(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test failure when ToR uplinks are below minimum."""
        # Set minimum uplinks requirement
        min_uplinks_policy = sample_policy.copy()
        min_uplinks_policy["redundancy"]["tor_uplinks_min"] = 6

        findings = validate_redundancy(sample_topology, sample_tors, sample_nodes, min_uplinks_policy)

        # Should find uplinks minimum failure
        uplinks_findings = [f for f in findings if f.code == "REDUNDANCY_TOR_UPLINKS"]
        assert len(uplinks_findings) == 2  # Both racks have only 4 uplinks
        assert all(f.severity == "FAIL" for f in uplinks_findings)
        assert all(f.context["shortfall"] == 2 for f in uplinks_findings)


class TestPolicySanityValidation:
    """Test cases for policy sanity checks."""

    def test_bad_spares_fraction(self, sample_policy):
        """Test failure when spares_fraction is out of range."""
        bad_policy = sample_policy.copy()
        bad_policy["defaults"]["spares_fraction"] = 1.5  # > 1.0

        findings = validate_policy_sanity(bad_policy)

        # Should find spares fraction error
        spares_findings = [f for f in findings if f.code == "POLICY_SPARES_RANGE"]
        assert len(spares_findings) == 1
        assert spares_findings[0].severity == "FAIL"

    def test_unsorted_media_bins(self, sample_policy):
        """Test failure when media bins are not sorted."""
        bad_policy = sample_policy.copy()
        bad_policy["media_rules"]["sfp28_25g"]["bins_m"] = [5, 3, 1, 10]  # Unsorted

        findings = validate_policy_sanity(bad_policy)

        # Should find media bins error
        bins_findings = [f for f in findings if f.code == "POLICY_BINS_UNSORTED"]
        assert len(bins_findings) == 1
        assert bins_findings[0].severity == "FAIL"
        assert "sfp28_25g" in bins_findings[0].context["media_type"]


class TestNicCompatibility:
    """Test cases for NIC type compatibility validation."""

    def test_sfp28_no_compatible_ports(self, sample_topology, sample_nodes, sample_policy):
        """Test failure when SFP28 NIC has no compatible ToR ports."""
        # ToR with no SFP28 ports
        no_sfp28_tors = {
            "tor-1": TorRec(
                id="tor-1", rack_id="rack-1", model="qsfp-only-switch", ports=TorPorts(sfp28_total=0, qsfp28_total=8)
            )
        }

        findings = validate_compatibility(sample_topology, no_sfp28_tors, sample_nodes, sample_policy)

        # Should find SFP28 compatibility failure
        compat_findings = [f for f in findings if f.code == "NIC_COMPATIBILITY_SFP28"]
        assert len(compat_findings) >= 1
        assert all(f.severity == "FAIL" for f in compat_findings)

    def test_qsfp28_nic_unsupported(self, sample_topology, sample_tors, sample_policy):
        """Test failure when QSFP28 NIC is used (unsupported)."""
        # Node with QSFP28 NIC
        qsfp28_nodes = [NodeRec(id="node-1", rack_id="rack-1", nics=[NicRec(type="QSFP28", count=1)])]

        findings = validate_compatibility(sample_topology, sample_tors, qsfp28_nodes, sample_policy)

        # Should find QSFP28 unsupported failure
        qsfp28_findings = [f for f in findings if f.code == "NIC_COMPATIBILITY_QSFP28_UNSUPPORTED"]
        assert len(qsfp28_findings) == 1
        assert qsfp28_findings[0].severity == "FAIL"

    def test_rj45_unmodeled_warning(self, sample_topology, sample_tors, sample_policy):
        """Test warning when RJ45 mgmt NIC termination is not modeled."""
        # Node with RJ45 NIC
        rj45_nodes = [NodeRec(id="node-1", rack_id="rack-1", nics=[NicRec(type="RJ45", count=1)])]

        findings = validate_compatibility(sample_topology, sample_tors, rj45_nodes, sample_policy)

        # Should find RJ45 unmodeled warning
        rj45_findings = [f for f in findings if f.code == "NIC_COMPATIBILITY_RJ45_UNMODELED"]
        assert len(rj45_findings) == 1
        assert rj45_findings[0].severity == "WARN"


class TestMgmtRj45Info:
    """Test cases for management RJ45 info messages."""

    def test_mgmt_rj45_unvalidated_info(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test that mgmt RJ45 produces INFO message."""
        findings = validate_ports(sample_topology, sample_tors, sample_nodes, sample_policy)

        # Should find mgmt RJ45 info message
        mgmt_findings = [f for f in findings if f.code == "MGMT_RJ45_UNVALIDATED"]
        assert len(mgmt_findings) == 1
        assert mgmt_findings[0].severity == "INFO"


class TestIntegration:
    """Integration tests for the complete validation system."""

    @patch("inferno_core.validation.cabling.load_topology")
    @patch("inferno_core.validation.cabling.load_tors")
    @patch("inferno_core.validation.cabling.load_nodes")
    @patch("inferno_core.validation.cabling.load_site")
    def test_run_cabling_validation_success(
        self,
        mock_load_site,
        mock_load_nodes,
        mock_load_tors,
        mock_load_topology,
        sample_topology,
        sample_tors,
        sample_nodes,
        sample_site,
    ):
        """Test the complete validation pipeline with successful data loading."""
        # Mock the data loading functions
        mock_load_topology.return_value = sample_topology
        mock_load_tors.return_value = (list(sample_tors.values()), None)  # Return tuple as expected
        mock_load_nodes.return_value = sample_nodes
        mock_load_site.return_value = sample_site

        # Run validation
        report = run_cabling_validation()

        # Verify report structure
        assert isinstance(report, Report)
        assert "pass" in report.summary
        assert "warn" in report.summary
        assert "fail" in report.summary
        assert "info" in report.summary
        assert isinstance(report.findings, list)

        # Should have minimal failures in a good configuration
        assert report.summary["fail"] == 0

    @patch("inferno_core.validation.cabling.load_topology")
    def test_run_cabling_validation_data_load_error(self, mock_load_topology):
        """Test validation pipeline with data loading error."""
        # Mock data loading to raise an exception
        mock_load_topology.side_effect = FileNotFoundError("topology.yaml not found")

        # Run validation
        report = run_cabling_validation()

        # Should return error report
        assert isinstance(report, Report)
        assert report.summary["fail"] == 1
        assert len(report.findings) == 1
        assert report.findings[0].code == "DATA_LOAD_ERROR"
        assert report.findings[0].severity == "FAIL"

    def test_report_serialization(self, sample_topology, sample_tors, sample_nodes, sample_policy):
        """Test that Report can be serialized to dict/JSON."""
        findings = validate_ports(sample_topology, sample_tors, sample_nodes, sample_policy)
        report = Report(summary={"pass": 10, "warn": 1, "fail": 0, "info": 1}, findings=findings)

        # Should be serializable
        report_dict = report.model_dump()
        assert isinstance(report_dict, dict)
        assert "summary" in report_dict
        assert "findings" in report_dict

        # Findings should be serializable too
        for finding_dict in report_dict["findings"]:
            assert "severity" in finding_dict
            assert "code" in finding_dict
            assert "message" in finding_dict
            assert "context" in finding_dict
