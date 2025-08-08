"""Cross-validation engine for reconciling BOM vs topology/policy.

This module provides functionality to reconcile calculated BOM against declared intent
(topology + policy + site geometry). It detects phantom items, missing items, and
mismatches in media/length bins.
"""

from pathlib import Path
from typing import Any, Dict, List

import yaml
from inferno_core.data.network_loader import (
    load_nodes,
    load_site,
    load_topology,
    load_tors,
)
from inferno_core.models.cross import CrossFinding, CrossReport
from inferno_core.data.cabling_policy import load_cabling_policy


def _load_bom_yaml(bom_path: Path | str) -> Dict[str, Any]:
    """Load BOM from YAML file."""
    with open(bom_path, "r") as f:
        data = yaml.safe_load(f)

    # Handle both old format (direct bom dict) and new format (with items/meta)
    if "items" in data or "meta" in data:
        # New format - return as-is
        return data
    elif "bom" in data:
        # Already wrapped format
        return data
    else:
        # Old format - wrap in metadata structure
        return {"meta": {}, "bom": data}


def _infer_class_from_cable_type(cable_type: str, quantity: int) -> str:
    """Infer class from cable_type when not explicitly provided in BOM."""
    if "sfp28_25g" in cable_type.lower():
        return "leaf-node"
    elif "qsfp28_100g" in cable_type.lower():
        return "leaf-spine"
    elif "rj45_cat6a" in cable_type.lower():
        # Ambiguous case - use quantity heuristics
        # Typically mgmt has more connections than WAN
        if quantity > 10:
            return "mgmt"
        else:
            return "wan"
    else:
        return "unknown"


def _normalize_bom_to_class_structure(bom_data: Dict[str, Any]) -> Dict[str, Dict[str, Dict[int, int]]]:
    """Convert BOM to class -> cable_type -> length_bin -> count structure."""
    items = bom_data.get("items", [])

    result = {}

    if items:
        # New format with explicit class
        for item in items:
            class_name = item["class"]
            cable_type = item["cable_type"]
            length_bin = item["length_bin_m"]
            quantity = item["quantity"]

            if class_name not in result:
                result[class_name] = {}
            if cable_type not in result[class_name]:
                result[class_name][cable_type] = {}

            # Handle case where we have multiple items with same class/type/bin
            if length_bin in result[class_name][cable_type]:
                result[class_name][cable_type][length_bin] += quantity
            else:
                result[class_name][cable_type][length_bin] = quantity
    else:
        # Old format - infer class from cable_type
        # In this case, bom_data itself is the BOM structure
        bom = bom_data.get("bom", bom_data)
        if isinstance(bom, dict):
            for cable_type, length_bins in bom.items():
                # Skip metadata keys
                if cable_type in ["meta", "metadata", "policy_path", "spares_fraction"]:
                    continue

                if isinstance(length_bins, dict):
                    for length_bin, quantity in length_bins.items():
                        # Skip non-numeric length bins (metadata)
                        try:
                            length_bin_int = int(length_bin)
                        except (ValueError, TypeError):
                            continue

                        class_name = _infer_class_from_cable_type(cable_type, quantity)

                        if class_name not in result:
                            result[class_name] = {}
                        if cable_type not in result[class_name]:
                            result[class_name][cable_type] = {}

                        result[class_name][cable_type][length_bin_int] = quantity

    return result


def _calculate_manhattan_distance(rack1_grid: List[int], rack2_grid: List[int], tile_m: float = 1.0) -> float:
    """Calculate Manhattan distance between two rack positions."""
    return abs(rack1_grid[0] - rack2_grid[0]) * tile_m + abs(rack1_grid[1] - rack2_grid[1]) * tile_m


def _select_length_bin(distance_m: float, bins: List[int]) -> int:
    """Select the smallest bin that can accommodate the distance."""
    for bin_size in sorted(bins):
        if distance_m <= bin_size:
            return bin_size
    # If no bin is large enough, return the largest bin
    return max(bins)


def _derive_intent_links(topology, tors, nodes, site, policy) -> List[Dict[str, Any]]:
    """Derive expected links from topology, nodes, and policy."""
    links = []

    # Get policy defaults
    defaults = policy.get("defaults", {})
    heuristics = policy.get("heuristics", {})
    media_rules = policy.get("media_rules", {})

    nodes_25g_per_node = defaults.get("nodes_25g_per_node", 2)
    mgmt_rj45_per_node = defaults.get("mgmt_rj45_per_node", 1)
    same_rack_distance = heuristics.get("same_rack_leaf_to_node_m", 2.0)
    adjacent_rack_distance = heuristics.get("adjacent_rack_leaf_to_spine_m", 5.0)
    slack_factor = defaults.get("slack_factor", 1.2)
    tile_m = heuristics.get("tile_m", 1.0)

    # Build rack position lookup if site data available
    rack_positions = {}
    if site and "racks" in site:
        for rack in site["racks"]:
            rack_positions[rack["id"]] = rack.get("grid", [0, 0])

    # 1. Leaf-node links (SFP28)
    for node in nodes.get("nodes", []):
        rack_id = node["rack_id"]

        # Get NIC count from node declaration or policy default
        nics = node.get("nics", [])
        sfp28_count = sum(1 for nic in nics if nic.get("type") == "SFP28")
        if sfp28_count == 0:
            sfp28_count = nodes_25g_per_node

        # Calculate distance (same rack)
        distance = same_rack_distance * slack_factor

        # Select media and bin
        sfp28_rules = media_rules.get("sfp28_25g", {})
        sfp28_rules.get("dac_max_m", 3.0)
        bins = sfp28_rules.get("bins_m", [1, 2, 3, 5, 7, 10])

        length_bin = _select_length_bin(distance, bins)

        for _ in range(sfp28_count):
            links.append(
                {
                    "class": "leaf-node",
                    "cable_type": "sfp28_25g",
                    "length_bin_m": length_bin,
                    "rack_id": rack_id,
                    "node_id": node["id"],
                }
            )

    # 2. Leaf-spine links (QSFP28)
    for rack in topology.get("racks", []):
        rack_id = rack["rack_id"]
        uplinks = rack.get("uplinks_qsfp28", defaults.get("tor_uplink_qsfp28_per_tor", 2))

        # Calculate distance to spine
        if rack_id in rack_positions and "spine" in rack_positions:
            spine_pos = rack_positions.get("spine", [0, 0])
            rack_pos = rack_positions[rack_id]
            distance = _calculate_manhattan_distance(rack_pos, spine_pos, tile_m) * slack_factor
        else:
            distance = adjacent_rack_distance * slack_factor

        # Select media and bin
        qsfp28_rules = media_rules.get("qsfp28_100g", {})
        qsfp28_rules.get("dac_max_m", 3.0)
        bins = qsfp28_rules.get("bins_m", [1, 2, 3, 5, 7, 10])

        length_bin = _select_length_bin(distance, bins)

        for _ in range(uplinks):
            links.append(
                {"class": "leaf-spine", "cable_type": "qsfp28_100g", "length_bin_m": length_bin, "rack_id": rack_id}
            )

    # 3. Management links (RJ45)
    for node in nodes.get("nodes", []):
        rack_id = node["rack_id"]

        # Get mgmt port count
        mgmt_count = mgmt_rj45_per_node

        # Use default distance for mgmt
        distance = 5.0 * slack_factor

        # Select bin
        rj45_rules = media_rules.get("rj45_cat6a", {})
        bins = rj45_rules.get("bins_m", [1, 2, 3, 5, 7, 10])
        length_bin = _select_length_bin(distance, bins)

        for _ in range(mgmt_count):
            links.append(
                {
                    "class": "mgmt",
                    "cable_type": "rj45_cat6a",
                    "length_bin_m": length_bin,
                    "rack_id": rack_id,
                    "node_id": node["id"],
                }
            )

    # 4. WAN links
    wan_config = topology.get("wan", {})
    if wan_config:
        wan_uplinks = wan_config.get("uplinks_cat6a", 0)

        # Use default distance for WAN
        distance = 10.0 * slack_factor

        # Select bin
        rj45_rules = media_rules.get("rj45_cat6a", {})
        bins = rj45_rules.get("bins_m", [1, 2, 3, 5, 7, 10])
        length_bin = _select_length_bin(distance, bins)

        for _ in range(wan_uplinks):
            links.append({"class": "wan", "cable_type": "rj45_cat6a", "length_bin_m": length_bin})

    return links


def _aggregate_intent_to_class_structure(links: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[int, int]]]:
    """Aggregate intent links into class -> cable_type -> length_bin -> count structure."""
    result = {}

    for link in links:
        class_name = link["class"]
        cable_type = link["cable_type"]
        length_bin = link["length_bin_m"]

        if class_name not in result:
            result[class_name] = {}
        if cable_type not in result[class_name]:
            result[class_name][cable_type] = {}
        if length_bin not in result[class_name][cable_type]:
            result[class_name][cable_type][length_bin] = 0

        result[class_name][cable_type][length_bin] += 1

    return result


def _reconcile_bom_vs_intent(
    bom_structure: Dict[str, Dict[str, Dict[int, int]]],
    intent_structure: Dict[str, Dict[str, Dict[int, int]]],
    policy: Dict[str, Any],
) -> List[CrossFinding]:
    """Reconcile BOM against intent and generate findings."""
    findings = []

    # Get policy settings
    bin_slop_m = policy.get("heuristics", {}).get("bin_slop_m", 2.0)

    # Track what we've already reconciled to avoid duplicate findings
    reconciled_bom = {}
    reconciled_intent = {}

    # Initialize tracking structures
    for class_name in set(list(bom_structure.keys()) + list(intent_structure.keys())):
        reconciled_bom[class_name] = {}
        reconciled_intent[class_name] = {}

        bom_cable_types = bom_structure.get(class_name, {})
        intent_cable_types = intent_structure.get(class_name, {})

        for cable_type in set(list(bom_cable_types.keys()) + list(intent_cable_types.keys())):
            reconciled_bom[class_name][cable_type] = {}
            reconciled_intent[class_name][cable_type] = {}

            # Copy original counts
            for bin_size, count in bom_cable_types.get(cable_type, {}).items():
                reconciled_bom[class_name][cable_type][bin_size] = count
            for bin_size, count in intent_cable_types.get(cable_type, {}).items():
                reconciled_intent[class_name][cable_type][bin_size] = count

    # First pass: Handle exact matches and bin mismatches
    for class_name in reconciled_bom:
        for cable_type in reconciled_bom[class_name]:
            bom_bins = list(reconciled_bom[class_name][cable_type].keys())
            intent_bins = list(reconciled_intent[class_name][cable_type].keys())

            # Handle exact matches first
            for bin_size in list(bom_bins):
                if bin_size in intent_bins:
                    bom_count = reconciled_bom[class_name][cable_type][bin_size]
                    intent_count = reconciled_intent[class_name][cable_type][bin_size]

                    # Match what we can
                    matched = min(bom_count, intent_count)
                    reconciled_bom[class_name][cable_type][bin_size] -= matched
                    reconciled_intent[class_name][cable_type][bin_size] -= matched

                    # Remove zero entries
                    if reconciled_bom[class_name][cable_type][bin_size] == 0:
                        del reconciled_bom[class_name][cable_type][bin_size]
                    if reconciled_intent[class_name][cable_type][bin_size] == 0:
                        del reconciled_intent[class_name][cable_type][bin_size]

            # Handle bin mismatches for remaining items
            remaining_bom_bins = list(reconciled_bom[class_name][cable_type].keys())
            remaining_intent_bins = list(reconciled_intent[class_name][cable_type].keys())

            for bom_bin in remaining_bom_bins:
                if remaining_intent_bins:
                    # Find closest intent bin
                    closest_intent_bin = min(remaining_intent_bins, key=lambda x: abs(x - bom_bin))

                    bom_count = reconciled_bom[class_name][cable_type][bom_bin]
                    intent_count = reconciled_intent[class_name][cable_type][closest_intent_bin]

                    # Check if this is a valid bin mismatch (same quantities)
                    if bom_count == intent_count:
                        # This is a bin mismatch
                        if bom_bin >= closest_intent_bin and (bom_bin - closest_intent_bin) <= bin_slop_m:
                            severity = "WARN"
                            code = "BIN_MISMATCH_WARN"
                        else:
                            severity = "FAIL"
                            code = "BIN_MISMATCH_FAIL"

                        findings.append(
                            CrossFinding(
                                severity=severity,
                                code=code,
                                message=f"{class_name} {cable_type}:"
                                f" BOM uses {bom_bin}m bin, intent expects {closest_intent_bin}m",
                                context={
                                    "class": class_name,
                                    "cable_type": cable_type,
                                    "bom_bin_m": bom_bin,
                                    "intent_bin_m": closest_intent_bin,
                                    "bin_slop_m": bin_slop_m,
                                },
                            )
                        )

                        # Remove these from further processing
                        del reconciled_bom[class_name][cable_type][bom_bin]
                        del reconciled_intent[class_name][cable_type][closest_intent_bin]

    # Second pass: Handle true missing and phantom items
    for class_name in reconciled_intent:
        for cable_type in reconciled_intent[class_name]:
            for length_bin, required_count in reconciled_intent[class_name][cable_type].items():
                if required_count > 0:
                    findings.append(
                        CrossFinding(
                            severity="FAIL",
                            code="MISSING_LINK",
                            message=f"{class_name} requires {required_count} × {cable_type} @ {length_bin} m;"
                            f" BOM provides 0",
                            context={
                                "class": class_name,
                                "cable_type": cable_type,
                                "length_bin_m": length_bin,
                                "required": required_count,
                                "provided": 0,
                            },
                        )
                    )

    for class_name in reconciled_bom:
        for cable_type in reconciled_bom[class_name]:
            for length_bin, provided_count in reconciled_bom[class_name][cable_type].items():
                if provided_count > 0:
                    findings.append(
                        CrossFinding(
                            severity="WARN",
                            code="PHANTOM_ITEM",
                            message=f"{class_name} BOM has {provided_count} × {cable_type} @ {length_bin} m;"
                            f" intent requires 0",
                            context={
                                "class": class_name,
                                "cable_type": cable_type,
                                "length_bin_m": length_bin,
                                "required": 0,
                                "provided": provided_count,
                            },
                        )
                    )

    return findings


def cross_validate_bom(
    bom_path: Path | str = Path("outputs/cabling_bom.yaml"),
    policy_path: Path | str = Path("doctrine/network/cabling-policy.yaml"),
) -> CrossReport:
    """Cross-validate BOM against topology/policy intent.

    Args:
        bom_path: Path to the BOM YAML file
        policy_path: Path to the cabling policy file (optional)

    Returns:
        CrossReport with findings and statistics
    """
    # Load all required data
    try:
        # Load manifests
        topology = load_topology()
        tors = load_tors()
        nodes = load_nodes()
        try:
            site = load_site()
        except FileNotFoundError:
            site = None

        # Load policy
        policy = load_cabling_policy(str(policy_path))

        # Load BOM
        bom_data = _load_bom_yaml(bom_path)

    except Exception as e:
        # Return error report
        return CrossReport(
            summary={"missing": 0, "phantom": 0, "mismatched_media": 0, "mismatched_bin": 0, "count_mismatch": 0},
            findings=[
                CrossFinding(
                    severity="FAIL",
                    code="LOAD_ERROR",
                    message=f"Failed to load required data: {e}",
                    context={"error": str(e)},
                )
            ],
            mapping_stats={"intent": {}, "bom": {}},
        )

    # Derive intent links
    intent_links = _derive_intent_links(
        topology.model_dump(), tors.model_dump(), nodes.model_dump(), site.model_dump() if site else None, policy
    )

    # Aggregate both structures
    intent_structure = _aggregate_intent_to_class_structure(intent_links)
    bom_structure = _normalize_bom_to_class_structure(bom_data)

    # Reconcile and generate findings
    findings = _reconcile_bom_vs_intent(bom_structure, intent_structure, policy)

    # Generate summary
    summary = {
        "missing": len([f for f in findings if f.code == "MISSING_LINK"]),
        "phantom": len([f for f in findings if f.code == "PHANTOM_ITEM"]),
        "mismatched_media": len([f for f in findings if f.code == "MEDIA_MISMATCH"]),
        "mismatched_bin": len([f for f in findings if f.code.startswith("BIN_MISMATCH")]),
        "count_mismatch": len([f for f in findings if f.code == "COUNT_MISMATCH"]),
    }

    # Generate mapping stats
    mapping_stats = {"intent": intent_structure, "bom": bom_structure}

    return CrossReport(summary=summary, findings=findings, mapping_stats=mapping_stats)
