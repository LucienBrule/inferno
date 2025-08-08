"""
Cabling validation module for Inferno network configurations.

Provides deterministic validation of manifests, topology, and cabling policy
against Inferno's network design rules before calculation/installation.
"""

from __future__ import annotations
from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, Field, ConfigDict

from inferno_core.data.network_loader import (
    load_nodes, load_tors, load_topology, load_site,
    NodeRec, TorRec, TopologyRec, SiteRec
)

# Import shared geometry helpers
try:
    from inferno_tools.cabling.common import compute_rack_distance_m, apply_slack, select_length_bin
except ImportError:
    # Fallback implementations for when inferno-tools is not available
    def compute_rack_distance_m(grid_a: tuple[int, int], grid_b: tuple[int, int], tile_m: float) -> float:
        dx = abs(grid_a[0] - grid_b[0])
        dy = abs(grid_a[1] - grid_b[1])
        return (dx + dy) * tile_m
    
    def apply_slack(distance_m: float, slack_factor: float) -> float:
        return distance_m * slack_factor
    
    def select_length_bin(distance_m: float, bins_m) -> int | None:
        for b in sorted(bins_m):
            if distance_m <= b:
                return b
        return None

# Type definitions
Severity = Literal["FAIL", "WARN", "INFO"]


class Finding(BaseModel):
    """A single validation finding with severity, code, message, and context."""
    model_config = ConfigDict(extra="ignore")
    severity: Severity
    code: str
    message: str
    context: dict = Field(default_factory=dict)


class Report(BaseModel):
    """Complete validation report with summary and findings."""
    model_config = ConfigDict(extra="ignore")
    summary: dict
    findings: list[Finding]


def _load_policy(policy_path: str | None = None) -> dict:
    """Load cabling policy with defaults."""
    defaults = {
        "defaults": {
            "nodes_25g_per_node": 2,
            "mgmt_rj45_per_node": 1,
            "tor_uplink_qsfp28_per_tor": 4,
            "spares_fraction": 0.1
        },
        "site_defaults": {
            "num_racks": 10,
            "nodes_per_rack": 20,
            "uplinks_per_rack": 4,
            "mgmt_rj45_per_node": 1,
            "wan_cat6a": 2
        },
        "media_rules": {
            "sfp28_25g": {
                "dac_max_m": 3,
                "bins_m": [1, 3, 5, 10, 30]
            },
            "qsfp28_100g": {
                "dac_max_m": 3,
                "bins_m": [1, 3, 5, 10, 30]
            },
            "rj45_cat6a": {
                "dac_max_m": 100,
                "bins_m": [1, 3, 5, 10, 30, 100]
            }
        },
        "redundancy": {
            "node_dual_homing": False,
            "tor_uplinks_min": 2
        },
        "oversubscription": {
            "max_leaf_to_spine_ratio": 4.0
        },
        "heuristics": {
            "same_rack_leaf_to_node_m": 2,
            "adjacent_rack_leaf_to_spine_m": 10,
            "non_adjacent_rack_leaf_to_spine_m": 30,
            "slack_factor": 1.2
        }
    }
    
    if policy_path:
        try:
            with open(policy_path, 'r') as f:
                policy = yaml.safe_load(f)
                # Merge with defaults
                for key, value in policy.items():
                    if isinstance(value, dict) and key in defaults:
                        defaults[key].update(value)
                    else:
                        defaults[key] = value
        except FileNotFoundError:
            pass  # Use defaults
    
    return defaults


def validate_ports(topology: TopologyRec, tors: dict[str, TorRec], nodes: list[NodeRec], policy: dict) -> list[Finding]:
    """Validate port capacity requirements."""
    findings = []
    
    # Group nodes by rack
    nodes_by_rack = {}
    for node in nodes:
        if node.rack_id not in nodes_by_rack:
            nodes_by_rack[node.rack_id] = []
        nodes_by_rack[node.rack_id].append(node)
    
    # Check ToR SFP28 ports (leaf→node)
    for rack in topology.racks:
        rack_nodes = nodes_by_rack.get(rack.rack_id, [])
        required_sfp28 = 0
        
        for node in rack_nodes:
            if node.nics:
                for nic in node.nics:
                    if nic.type == "SFP28":
                        required_sfp28 += nic.count
            else:
                # Use policy default
                required_sfp28 += policy["defaults"]["nodes_25g_per_node"]
        
        tor = tors.get(rack.tor_id)
        if not tor:
            findings.append(Finding(
                severity="FAIL",
                code="MISSING_TOR",
                message=f"rack {rack.rack_id} references unknown ToR {rack.tor_id}",
                context={"rack_id": rack.rack_id, "tor_id": rack.tor_id}
            ))
            continue
            
        available_sfp28 = tor.ports.sfp28_total
        if required_sfp28 > available_sfp28:
            deficit = required_sfp28 - available_sfp28
            findings.append(Finding(
                severity="FAIL",
                code="PORT_CAPACITY_TOR_SFP28",
                message=f"rack {rack.rack_id} requires {required_sfp28} SFP28 ports, ToR provides {available_sfp28} (deficit {deficit})",
                context={
                    "rack_id": rack.rack_id,
                    "required_sfp28": required_sfp28,
                    "available_sfp28": available_sfp28,
                    "deficit": deficit
                }
            ))
    
    # Check ToR QSFP28 ports (uplinks)
    for rack in topology.racks:
        required_qsfp28 = rack.uplinks_qsfp28
        tor = tors.get(rack.tor_id)
        if tor:
            available_qsfp28 = tor.ports.qsfp28_total
            if required_qsfp28 > available_qsfp28:
                deficit = required_qsfp28 - available_qsfp28
                findings.append(Finding(
                    severity="FAIL",
                    code="PORT_CAPACITY_TOR_QSFP28",
                    message=f"rack {rack.rack_id} requires {required_qsfp28} QSFP28 uplinks, ToR provides {available_qsfp28} (deficit {deficit})",
                    context={
                        "rack_id": rack.rack_id,
                        "required_qsfp28": required_qsfp28,
                        "available_qsfp28": available_qsfp28,
                        "deficit": deficit
                    }
                ))
    
    # Check Spine QSFP28 ports
    total_uplinks = sum(rack.uplinks_qsfp28 for rack in topology.racks)
    spine_capacity = topology.spine.ports.qsfp28_total
    
    if total_uplinks > spine_capacity:
        deficit = total_uplinks - spine_capacity
        findings.append(Finding(
            severity="FAIL",
            code="PORT_CAPACITY_SPINE_QSFP28",
            message=f"total uplinks {total_uplinks} exceed spine capacity {spine_capacity} (deficit {deficit})",
            context={
                "total_uplinks": total_uplinks,
                "spine_capacity": spine_capacity,
                "deficit": deficit
            }
        ))
    elif total_uplinks > spine_capacity * 0.95:
        # Within 5% of capacity → WARN
        utilization = total_uplinks / spine_capacity
        findings.append(Finding(
            severity="WARN",
            code="PORT_CAPACITY_SPINE_NEAR_LIMIT",
            message=f"spine utilization {utilization:.1%} is near capacity limit",
            context={
                "total_uplinks": total_uplinks,
                "spine_capacity": spine_capacity,
                "utilization": utilization
            }
        ))
    
    # Mgmt RJ45 - just note that it's unvalidated for now
    findings.append(Finding(
        severity="INFO",
        code="MGMT_RJ45_UNVALIDATED",
        message="management RJ45 ports not validated (no mgmt switch inventory)",
        context={}
    ))
    
    return findings


def validate_compatibility(topology: TopologyRec, tors: dict[str, TorRec], nodes: list[NodeRec], policy: dict) -> list[Finding]:
    """Validate NIC type compatibility."""
    findings = []
    
    for node in nodes:
        if not node.nics:
            continue
            
        for nic in node.nics:
            if nic.type == "SFP28":
                # Must terminate on SFP28-capable port (ToR leaf)
                rack = next((r for r in topology.racks if r.rack_id == node.rack_id), None)
                if not rack:
                    findings.append(Finding(
                        severity="FAIL",
                        code="NIC_COMPATIBILITY_NO_RACK",
                        message=f"node {node.id} SFP28 NIC has no rack mapping",
                        context={"node_id": node.id, "nic_type": nic.type}
                    ))
                    continue
                    
                tor = tors.get(rack.tor_id)
                if not tor or tor.ports.sfp28_total == 0:
                    findings.append(Finding(
                        severity="FAIL",
                        code="NIC_COMPATIBILITY_SFP28",
                        message=f"node {node.id} SFP28 NIC cannot terminate (no SFP28 ports on ToR)",
                        context={"node_id": node.id, "tor_id": rack.tor_id, "nic_type": nic.type}
                    ))
            
            elif nic.type == "QSFP28":
                # Rare case - requires QSFP28 leaf ports or breakouts
                findings.append(Finding(
                    severity="FAIL",
                    code="NIC_COMPATIBILITY_QSFP28_UNSUPPORTED",
                    message=f"node {node.id} QSFP28 NIC not supported (no breakout policy)",
                    context={"node_id": node.id, "nic_type": nic.type}
                ))
            
            elif nic.type == "RJ45":
                # Should terminate to RJ45 aggregation
                findings.append(Finding(
                    severity="WARN",
                    code="NIC_COMPATIBILITY_RJ45_UNMODELED",
                    message=f"node {node.id} RJ45 mgmt NIC termination not modeled",
                    context={"node_id": node.id, "nic_type": nic.type}
                ))
    
    return findings


def validate_oversubscription(topology: TopologyRec, tors: dict[str, TorRec], nodes: list[NodeRec], policy: dict) -> list[Finding]:
    """Validate oversubscription ratios."""
    findings = []
    
    # Group nodes by rack
    nodes_by_rack = {}
    for node in nodes:
        if node.rack_id not in nodes_by_rack:
            nodes_by_rack[node.rack_id] = []
        nodes_by_rack[node.rack_id].append(node)
    
    max_ratio = policy["oversubscription"]["max_leaf_to_spine_ratio"]
    
    for rack in topology.racks:
        rack_nodes = nodes_by_rack.get(rack.rack_id, [])
        
        # Calculate edge bandwidth (leaf→node)
        edge_bw_gbps = 0
        for node in rack_nodes:
            if node.nics:
                for nic in node.nics:
                    if nic.type == "SFP28":
                        edge_bw_gbps += nic.count * 25  # 25 Gbps per SFP28
                    elif nic.type == "QSFP28":
                        edge_bw_gbps += nic.count * 100  # 100 Gbps per QSFP28
            else:
                # Use policy default
                edge_bw_gbps += policy["defaults"]["nodes_25g_per_node"] * 25
        
        # Calculate uplink bandwidth (leaf→spine)
        uplink_bw_gbps = rack.uplinks_qsfp28 * 100  # 100 Gbps per QSFP28
        
        if uplink_bw_gbps == 0 and edge_bw_gbps > 0:
            findings.append(Finding(
                severity="FAIL",
                code="OVERSUB_NO_UPLINKS",
                message=f"rack {rack.rack_id} has edge bandwidth {edge_bw_gbps} Gbps but no uplinks",
                context={
                    "rack_id": rack.rack_id,
                    "edge_gbps": edge_bw_gbps,
                    "uplink_gbps": uplink_bw_gbps
                }
            ))
            continue
        
        if uplink_bw_gbps > 0:
            ratio = edge_bw_gbps / uplink_bw_gbps
            if ratio > max_ratio:
                excess_pct = (ratio - max_ratio) / max_ratio
                if excess_pct <= 0.25:  # ≤ 25% over
                    findings.append(Finding(
                        severity="WARN",
                        code="OVERSUB_RATIO",
                        message=f"rack {rack.rack_id} edge {edge_bw_gbps} Gbps, uplink {uplink_bw_gbps} Gbps → {ratio:.1f}:1 exceeds policy {max_ratio}:1",
                        context={
                            "rack_id": rack.rack_id,
                            "edge_gbps": edge_bw_gbps,
                            "uplink_gbps": uplink_bw_gbps,
                            "ratio": ratio,
                            "policy_max": max_ratio
                        }
                    ))
                else:  # > 25% over
                    findings.append(Finding(
                        severity="FAIL",
                        code="OVERSUB_RATIO_CRITICAL",
                        message=f"rack {rack.rack_id} edge {edge_bw_gbps} Gbps, uplink {uplink_bw_gbps} Gbps → {ratio:.1f}:1 critically exceeds policy {max_ratio}:1",
                        context={
                            "rack_id": rack.rack_id,
                            "edge_gbps": edge_bw_gbps,
                            "uplink_gbps": uplink_bw_gbps,
                            "ratio": ratio,
                            "policy_max": max_ratio
                        }
                    ))
    
    return findings


def validate_completeness(topology: TopologyRec, tors: dict[str, TorRec], nodes: list[NodeRec], site: SiteRec | None, policy: dict) -> list[Finding]:
    """Validate connection completeness."""
    findings = []
    
    # Every topology.racks[*].tor_id must exist in tors and share the same rack_id
    for rack in topology.racks:
        tor = tors.get(rack.tor_id)
        if not tor:
            findings.append(Finding(
                severity="FAIL",
                code="COMPLETENESS_MISSING_TOR",
                message=f"topology rack {rack.rack_id} references unknown ToR {rack.tor_id}",
                context={"rack_id": rack.rack_id, "tor_id": rack.tor_id}
            ))
        elif tor.rack_id != rack.rack_id:
            findings.append(Finding(
                severity="FAIL",
                code="COMPLETENESS_TOR_RACK_MISMATCH",
                message=f"ToR {rack.tor_id} rack_id {tor.rack_id} doesn't match topology rack_id {rack.rack_id}",
                context={"tor_id": rack.tor_id, "tor_rack_id": tor.rack_id, "topology_rack_id": rack.rack_id}
            ))
    
    # Every nodes[*].rack_id must exist in topology or site
    topology_rack_ids = {rack.rack_id for rack in topology.racks}
    site_rack_ids = {rack.id for rack in site.racks} if site else set()
    valid_rack_ids = topology_rack_ids | site_rack_ids
    
    for node in nodes:
        if node.rack_id not in valid_rack_ids:
            findings.append(Finding(
                severity="FAIL",
                code="COMPLETENESS_NODE_RACK_MISSING",
                message=f"node {node.id} references unknown rack {node.rack_id}",
                context={"node_id": node.id, "rack_id": node.rack_id}
            ))
    
    # Spine must exist and have ports defined
    if not topology.spine:
        findings.append(Finding(
            severity="FAIL",
            code="COMPLETENESS_MISSING_SPINE",
            message="topology missing spine configuration",
            context={}
        ))
    elif not hasattr(topology.spine, 'ports') or topology.spine.ports.qsfp28_total <= 0:
        findings.append(Finding(
            severity="FAIL",
            code="COMPLETENESS_SPINE_NO_PORTS",
            message="spine has no QSFP28 ports defined",
            context={"spine_id": topology.spine.id}
        ))
    
    return findings


def validate_lengths(topology: TopologyRec, tors: dict[str, TorRec], nodes: list[NodeRec], site: SiteRec | None, policy: dict) -> list[Finding]:
    """Validate cable length feasibility and bin compliance."""
    findings = []
    
    if not site:
        findings.append(Finding(
            severity="INFO",
            code="SITE_GEOMETRY_MISSING",
            message="geometry-based length checks skipped (no site.yaml)",
            context={}
        ))
        return findings
    
    # Create rack position lookup
    rack_positions = {rack.id: rack.grid for rack in site.racks if rack.grid}
    
    heuristics = policy["heuristics"]
    media_rules = policy["media_rules"]
    
    # Group nodes by rack
    nodes_by_rack = {}
    for node in nodes:
        if node.rack_id not in nodes_by_rack:
            nodes_by_rack[node.rack_id] = []
        nodes_by_rack[node.rack_id].append(node)
    
    # Check leaf→node lengths
    for rack in topology.racks:
        rack_nodes = nodes_by_rack.get(rack.rack_id, [])
        
        for node in rack_nodes:
            if not node.nics:
                continue
                
            for nic in node.nics:
                if nic.type == "SFP28":
                    # Same rack connection - use shared helpers
                    base_distance = heuristics["same_rack_leaf_to_node_m"]
                    slack_factor = heuristics["slack_factor"]
                    distance = apply_slack(base_distance, slack_factor)
                    
                    dac_max = media_rules["sfp28_25g"]["dac_max_m"]
                    bins = media_rules["sfp28_25g"]["bins_m"]
                    
                    # Select appropriate bin
                    selected_bin = select_length_bin(distance, bins)
                    
                    if selected_bin is None:
                        # Distance exceeds all available bins
                        findings.append(Finding(
                            severity="FAIL",
                            code="LENGTH_EXCEEDS_MAX_BIN",
                            message=f"node {node.id} SFP28 requires {distance:.1f}m but exceeds maximum bin {max(bins)}m",
                            context={
                                "node_id": node.id,
                                "rack_id": rack.rack_id,
                                "distance_m": distance,
                                "bin": max(bins),
                                "media_class": "SFP28"
                            }
                        ))
                    elif distance > dac_max:
                        # Need AOC/fiber - check if AOC/fiber bins are available
                        aoc_bins = [b for b in bins if b > dac_max]
                        if not aoc_bins:
                            findings.append(Finding(
                                severity="FAIL",
                                code="LENGTH_EXCEEDS_DAC_NO_AOC_BINS",
                                message=f"node {node.id} SFP28 requires {distance:.1f}m, exceeds DAC limit {dac_max}m but no AOC/fiber bins configured",
                                context={
                                    "node_id": node.id,
                                    "rack_id": rack.rack_id,
                                    "distance_m": distance,
                                    "bin": selected_bin,
                                    "media_class": "SFP28"
                                }
                            ))
    
    # Check leaf→spine lengths
    spine_position = (0, 0)  # Assume spine at origin for simplicity
    tile_m = heuristics.get("tile_m", 1.0)
    
    for rack in topology.racks:
        rack_pos = rack_positions.get(rack.rack_id)
        if not rack_pos:
            continue
            
        # Use shared geometry helper for Manhattan distance calculation
        base_distance = compute_rack_distance_m(tuple(rack_pos), spine_position, tile_m)
        
        # Apply slack factor using shared helper
        slack_factor = heuristics["slack_factor"]
        cable_length = apply_slack(base_distance, slack_factor)
        
        dac_max = media_rules["qsfp28_100g"]["dac_max_m"]
        bins = media_rules["qsfp28_100g"]["bins_m"]
        
        # Select appropriate bin
        selected_bin = select_length_bin(cable_length, bins)
        
        if selected_bin is None:
            # Distance exceeds all available bins
            findings.append(Finding(
                severity="FAIL",
                code="LENGTH_EXCEEDS_MAX_BIN",
                message=f"rack {rack.rack_id} uplinks require {cable_length:.1f}m but exceed maximum bin {max(bins)}m",
                context={
                    "rack_id": rack.rack_id,
                    "distance_m": cable_length,
                    "bin": max(bins),
                    "media_class": "QSFP28"
                }
            ))
        elif cable_length > dac_max:
            # Need AOC/fiber - check if AOC/fiber bins are available
            aoc_bins = [b for b in bins if b > dac_max]
            if not aoc_bins:
                findings.append(Finding(
                    severity="FAIL",
                    code="LENGTH_EXCEEDS_DAC_NO_AOC_BINS",
                    message=f"rack {rack.rack_id} uplinks require {cable_length:.1f}m, exceed DAC limit {dac_max}m but no AOC/fiber bins configured",
                    context={
                        "rack_id": rack.rack_id,
                        "distance_m": cable_length,
                        "bin": selected_bin,
                        "media_class": "QSFP28"
                    }
                ))
    
    # Check RJ45 connections (mgmt/WAN) for bins > 100m warning
    rj45_rules = media_rules.get("rj45_cat6a", {})
    rj45_bins = rj45_rules.get("bins_m", [])
    
    # For each rack, check management connections
    for rack in topology.racks:
        rack_nodes = nodes_by_rack.get(rack.rack_id, [])
        
        for node in rack_nodes:
            if not node.nics:
                continue
                
            for nic in node.nics:
                if nic.type == "RJ45":
                    # Use heuristic distance for mgmt connections
                    mgmt_distance = heuristics.get("same_rack_leaf_to_node_m", 2.0)
                    mgmt_distance = apply_slack(mgmt_distance, slack_factor)
                    
                    selected_bin = select_length_bin(mgmt_distance, rj45_bins)
                    
                    if selected_bin and selected_bin > 100:
                        findings.append(Finding(
                            severity="WARN",
                            code="RJ45_BIN_GT_100M",
                            message=f"node {node.id} RJ45 connection uses bin {selected_bin}m > 100m (speed may downshift)",
                            context={
                                "node_id": node.id,
                                "rack_id": rack.rack_id,
                                "distance_m": mgmt_distance,
                                "bin": selected_bin,
                                "media_class": "RJ45"
                            }
                        ))
                    elif selected_bin is None:
                        findings.append(Finding(
                            severity="FAIL",
                            code="LENGTH_EXCEEDS_MAX_BIN",
                            message=f"node {node.id} RJ45 requires {mgmt_distance:.1f}m but exceeds maximum bin {max(rj45_bins)}m",
                            context={
                                "node_id": node.id,
                                "rack_id": rack.rack_id,
                                "distance_m": mgmt_distance,
                                "bin": max(rj45_bins),
                                "media_class": "RJ45"
                            }
                        ))
    
    return findings


def validate_redundancy(topology: TopologyRec, tors: dict[str, TorRec], nodes: list[NodeRec], policy: dict) -> list[Finding]:
    """Validate redundancy rules."""
    findings = []
    
    redundancy = policy["redundancy"]
    
    # Check node dual homing
    if redundancy.get("node_dual_homing", False):
        for node in nodes:
            if node.nics:
                total_nics = sum(nic.count for nic in node.nics if nic.type in ["SFP28", "QSFP28"])
            else:
                total_nics = policy["defaults"]["nodes_25g_per_node"]
            
            if total_nics % 2 != 0:
                findings.append(Finding(
                    severity="FAIL",
                    code="REDUNDANCY_DUAL_HOMING",
                    message=f"node {node.id} has {total_nics} NICs, not divisible by 2 (dual homing required)",
                    context={"node_id": node.id, "nic_count": total_nics}
                ))
    
    # Check ToR uplinks minimum
    min_uplinks = redundancy.get("tor_uplinks_min")
    if min_uplinks:
        for rack in topology.racks:
            if rack.uplinks_qsfp28 < min_uplinks:
                shortfall = min_uplinks - rack.uplinks_qsfp28
                findings.append(Finding(
                    severity="FAIL",
                    code="REDUNDANCY_TOR_UPLINKS",
                    message=f"rack {rack.rack_id} has {rack.uplinks_qsfp28} uplinks, minimum {min_uplinks} required (shortfall {shortfall})",
                    context={
                        "rack_id": rack.rack_id,
                        "uplinks": rack.uplinks_qsfp28,
                        "minimum": min_uplinks,
                        "shortfall": shortfall
                    }
                ))
    
    return findings


def validate_policy_sanity(policy: dict) -> list[Finding]:
    """Validate policy sanity checks with comprehensive edge case coverage."""
    findings = []
    
    # A) Spares fraction validation
    spares_fraction = policy.get("defaults", {}).get("spares_fraction")
    if spares_fraction is not None:
        try:
            spares_float = float(spares_fraction)
            if not (0.0 <= spares_float <= 1.0):
                findings.append(Finding(
                    severity="FAIL",
                    code="POLICY_SPARES_RANGE",
                    message=f"defaults.spares_fraction {spares_float} must be between 0.0 and 1.0",
                    context={"key": "defaults.spares_fraction", "value": spares_float}
                ))
        except (ValueError, TypeError):
            findings.append(Finding(
                severity="FAIL",
                code="POLICY_SPARES_TYPE",
                message=f"defaults.spares_fraction '{spares_fraction}' is not coercible to float",
                context={"key": "defaults.spares_fraction", "value": spares_fraction}
            ))
    
    # B) Length bins validation (all media types)
    media_rules = policy.get("media_rules", {})
    for media_type, rules in media_rules.items():
        bins = rules.get("bins_m")
        if bins is not None:
            # Check if empty
            if not bins:
                findings.append(Finding(
                    severity="FAIL",
                    code="POLICY_BINS_EMPTY",
                    message=f"media_rules.{media_type}.bins_m cannot be empty",
                    context={"media_type": media_type}
                ))
                continue
            
            # Check if all are positive integers
            invalid_bins = [b for b in bins if not isinstance(b, int) or b <= 0]
            if invalid_bins:
                findings.append(Finding(
                    severity="FAIL",
                    code="POLICY_BINS_INVALID",
                    message=f"media_rules.{media_type}.bins_m contains non-integer or non-positive values: {invalid_bins}",
                    context={"media_type": media_type, "invalid_values": invalid_bins}
                ))
                continue
            
            # Check for duplicates
            if len(bins) != len(set(bins)):
                duplicates = [b for b in set(bins) if bins.count(b) > 1]
                findings.append(Finding(
                    severity="FAIL",
                    code="POLICY_BINS_DUPLICATE",
                    message=f"media_rules.{media_type}.bins_m contains duplicate values: {duplicates}",
                    context={"media_type": media_type, "duplicates": duplicates}
                ))
                continue
            
            # Check if strictly ascending
            if bins != sorted(bins):
                findings.append(Finding(
                    severity="FAIL",
                    code="POLICY_BINS_UNSORTED",
                    message=f"media_rules.{media_type}.bins_m must be strictly ascending: {bins}",
                    context={"media_type": media_type, "bins_m": bins}
                ))
    
    # C) DAC thresholds validation
    optical_media_types = ["sfp28_25g", "qsfp28_100g"]
    for media_type in optical_media_types:
        if media_type in media_rules:
            rules = media_rules[media_type]
            bins = rules.get("bins_m", [])
            dac_max = rules.get("dac_max_m")
            
            if dac_max is None and bins:
                findings.append(Finding(
                    severity="WARN",
                    code="POLICY_DAC_MAX_MISSING",
                    message=f"media_rules.{media_type}.dac_max_m missing, will assume smallest bin as soft threshold",
                    context={"media_type": media_type, "smallest_bin": min(bins) if bins else None}
                ))
            elif dac_max is not None:
                if not isinstance(dac_max, int) or dac_max <= 0:
                    findings.append(Finding(
                        severity="FAIL",
                        code="POLICY_DAC_MAX_INVALID",
                        message=f"media_rules.{media_type}.dac_max_m must be an integer ≥ 1, got: {dac_max}",
                        context={"media_type": media_type, "value": dac_max}
                    ))
                elif bins and dac_max < min(bins):
                    findings.append(Finding(
                        severity="WARN",
                        code="POLICY_DAC_MAX_LT_SMALLEST_BIN",
                        message=f"media_rules.{media_type}.dac_max_m ({dac_max}) is less than smallest bin ({min(bins)})",
                        context={"media_type": media_type, "dac_max_m": dac_max, "smallest_bin": min(bins)}
                    ))
    
    # D) Media presence / fallbacks
    expected_media_types = ["sfp28_25g", "qsfp28_100g", "rj45_cat6a"]
    for media_type in expected_media_types:
        if media_type not in media_rules:
            # Check if we have built-in defaults (we do in _load_policy)
            findings.append(Finding(
                severity="WARN",
                code="POLICY_MEDIA_MISSING_DEFAULTED",
                message=f"media_rules.{media_type} missing from policy, using built-in defaults",
                context={"media_type": media_type}
            ))
    
    # E) RJ45 constraints
    if "rj45_cat6a" in media_rules:
        rj45_bins = media_rules["rj45_cat6a"].get("bins_m", [])
        over_100m = [b for b in rj45_bins if isinstance(b, int) and b > 100]
        if over_100m:
            findings.append(Finding(
                severity="WARN",
                code="POLICY_RJ45_BINS_GT_100M",
                message=f"rj45_cat6a.bins_m contains bins > 100m: {over_100m} (may negotiate lower speeds)",
                context={"bins_over_100m": over_100m}
            ))
    
    # F) Defaults and counts validation
    defaults = policy.get("defaults", {})
    for key, value in defaults.items():
        if key == "spares_fraction":
            continue  # Already handled in section A
        
        if value is not None:
            if not isinstance(value, int):
                findings.append(Finding(
                    severity="FAIL",
                    code="POLICY_DEFAULT_TYPE",
                    message=f"defaults.{key} must be an integer, got: {type(value).__name__}",
                    context={"key": f"defaults.{key}", "value": value, "type": type(value).__name__}
                ))
            elif value < 0:
                findings.append(Finding(
                    severity="FAIL",
                    code="POLICY_DEFAULT_NEGATIVE",
                    message=f"defaults.{key} must be ≥ 0, got: {value}",
                    context={"key": f"defaults.{key}", "value": value}
                ))
    
    # G) Redundancy rules validation
    redundancy = policy.get("redundancy", {})
    if "node_dual_homing" in redundancy:
        dual_homing = redundancy["node_dual_homing"]
        if not isinstance(dual_homing, bool):
            findings.append(Finding(
                severity="FAIL",
                code="POLICY_REDUNDANCY_INVALID",
                message=f"redundancy.node_dual_homing must be boolean, got: {type(dual_homing).__name__}",
                context={"key": "redundancy.node_dual_homing", "value": dual_homing}
            ))
    
    if "tor_uplinks_min" in redundancy:
        uplinks_min = redundancy["tor_uplinks_min"]
        if not isinstance(uplinks_min, int) or uplinks_min < 0:
            findings.append(Finding(
                severity="FAIL",
                code="POLICY_REDUNDANCY_INVALID",
                message=f"redundancy.tor_uplinks_min must be integer ≥ 0, got: {uplinks_min}",
                context={"key": "redundancy.tor_uplinks_min", "value": uplinks_min}
            ))
    
    # H) Oversubscription policy validation
    oversubscription = policy.get("oversubscription", {})
    if "max_leaf_to_spine_ratio" not in oversubscription:
        findings.append(Finding(
            severity="WARN",
            code="POLICY_OVERSUB_DEFAULTED",
            message="oversubscription.max_leaf_to_spine_ratio missing, using engine default 4.0",
            context={"default_value": 4.0}
        ))
    else:
        ratio = oversubscription["max_leaf_to_spine_ratio"]
        try:
            ratio_float = float(ratio)
            if ratio_float <= 0:
                findings.append(Finding(
                    severity="FAIL",
                    code="POLICY_OVERSUB_INVALID",
                    message=f"oversubscription.max_leaf_to_spine_ratio must be > 0, got: {ratio_float}",
                    context={"key": "oversubscription.max_leaf_to_spine_ratio", "value": ratio_float}
                ))
        except (ValueError, TypeError):
            findings.append(Finding(
                severity="FAIL",
                code="POLICY_OVERSUB_INVALID",
                message=f"oversubscription.max_leaf_to_spine_ratio must be numeric, got: {ratio}",
                context={"key": "oversubscription.max_leaf_to_spine_ratio", "value": ratio}
            ))
    
    # I) Geometry heuristics validation
    heuristics = policy.get("heuristics", {})
    heuristic_fields = {
        "same_rack_leaf_to_node_m": ("> 0", lambda x: x > 0),
        "adjacent_rack_leaf_to_spine_m": ("> 0", lambda x: x > 0),
        "non_adjacent_rack_leaf_to_spine_m": ("> 0", lambda x: x > 0),
        "tile_m": ("> 0", lambda x: x > 0),
        "slack_factor": ("≥ 1.0", lambda x: x >= 1.0)
    }
    
    for field, (constraint_desc, constraint_func) in heuristic_fields.items():
        if field in heuristics:
            value = heuristics[field]
            try:
                value_float = float(value)
                if not constraint_func(value_float):
                    findings.append(Finding(
                        severity="FAIL",
                        code="POLICY_HEURISTICS_INVALID",
                        message=f"heuristics.{field} must be {constraint_desc}, got: {value_float}",
                        context={"key": f"heuristics.{field}", "value": value_float, "constraint": constraint_desc}
                    ))
            except (ValueError, TypeError):
                findings.append(Finding(
                    severity="FAIL",
                    code="POLICY_HEURISTICS_INVALID",
                    message=f"heuristics.{field} must be numeric, got: {value}",
                    context={"key": f"heuristics.{field}", "value": value}
                ))
    
    return findings


def run_cabling_validation(policy_path: str | None = None) -> Report:
    """
    Top-level cabling validation function.
    
    Loads manifests, runs all validation checks, and returns structured Report.
    """
    # Load policy
    policy = _load_policy(policy_path)
    
    # Load data
    try:
        topology = load_topology()
        tors_list, spine_rec = load_tors()  # Unpack the tuple properly
        nodes = load_nodes()
        
        # Convert tors list to dict for easier lookup
        tors = {tor.id: tor for tor in tors_list}
        
        try:
            site = load_site()
        except FileNotFoundError:
            site = None
            
    except Exception as e:
        # If we can't load basic data, return a failure report
        return Report(
            summary={"pass": 0, "warn": 0, "fail": 1},
            findings=[Finding(
                severity="FAIL",
                code="DATA_LOAD_ERROR",
                message=f"Failed to load required data: {e}",
                context={"error": str(e)}
            )]
        )
    
    # Run all validation checks
    all_findings = []
    
    all_findings.extend(validate_policy_sanity(policy))
    all_findings.extend(validate_ports(topology, tors, nodes, policy))
    all_findings.extend(validate_compatibility(topology, tors, nodes, policy))
    all_findings.extend(validate_oversubscription(topology, tors, nodes, policy))
    all_findings.extend(validate_completeness(topology, tors, nodes, site, policy))
    all_findings.extend(validate_lengths(topology, tors, nodes, site, policy))
    all_findings.extend(validate_redundancy(topology, tors, nodes, policy))
    
    # Generate summary
    summary = {
        "pass": 0,
        "warn": len([f for f in all_findings if f.severity == "WARN"]),
        "fail": len([f for f in all_findings if f.severity == "FAIL"]),
        "info": len([f for f in all_findings if f.severity == "INFO"])
    }
    
    # Calculate pass count (this would be the number of successful checks)
    # For now, we'll estimate based on the number of checks that could have been performed
    total_possible_checks = len(topology.racks) * 4 + len(nodes) * 2 + 10  # Rough estimate
    summary["pass"] = max(0, total_possible_checks - summary["warn"] - summary["fail"])
    
    return Report(summary=summary, findings=all_findings)