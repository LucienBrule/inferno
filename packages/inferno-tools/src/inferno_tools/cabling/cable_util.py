import math
from typing import List, Dict, Any, Tuple, Optional

from inferno_tools.cabling.common import compute_rack_distance_m, apply_slack, select_length_bin


def _with_spares(count: int, spares_fraction: float) -> int:
    return math.ceil(count * (1.0 + spares_fraction))


def _calculate_manhattan_distance(rack1_grid: List[int], rack2_grid: List[int], tile_m: float = 1.0) -> float:
    """Calculate Manhattan distance between two racks in meters."""
    return compute_rack_distance_m((rack1_grid[0], rack1_grid[1]), (rack2_grid[0], rack2_grid[1]), tile_m)


def _select_cable_type_and_bin(
        distance_m: float, link_type: str, policy: Dict[str, Any], length_bins_m: List[int]
) -> Tuple[str, int]:
    """Select cable type and length bin based on distance and policy."""
    # Apply slack factor
    slack_factor = policy.get("heuristics", {}).get("slack_factor", 1.2)
    adjusted_distance = apply_slack(distance_m, slack_factor)

    # Find appropriate length bin
    selected_bin = select_length_bin(adjusted_distance, length_bins_m)

    if selected_bin is None:
        selected_bin = max(length_bins_m)  # Use largest bin if distance exceeds all bins

    # Determine cable type based on link type and distance
    media_rules = policy.get("media_rules", {})

    if link_type == "25G":
        rules = media_rules.get("sfp28_25g", {})
        dac_max = rules.get("dac_max_m", 3)
        if adjusted_distance <= dac_max:
            cable_type = rules.get("labels", {}).get("dac", "SFP28 25G DAC")
        elif adjusted_distance <= 10:
            cable_type = rules.get("labels", {}).get("aoc", "SFP28 25G AOC")
        else:
            cable_type = rules.get("labels", {}).get("fiber", "SFP28 25G MMF + SR")
    elif link_type == "100G":
        rules = media_rules.get("qsfp28_100g", {})
        dac_max = rules.get("dac_max_m", 3)
        if adjusted_distance <= dac_max:
            cable_type = rules.get("labels", {}).get("dac", "QSFP28 100G DAC")
        elif adjusted_distance <= 10:
            cable_type = rules.get("labels", {}).get("aoc", "QSFP28 100G AOC")
        else:
            cable_type = rules.get("labels", {}).get("fiber", "QSFP28 100G MMF + SR4")
    elif link_type == "RJ45":
        rules = media_rules.get("rj45_cat6a", {})
        cable_type = rules.get("label", "RJ45 Cat6A")
    else:
        cable_type = f"Unknown {link_type}"

    return cable_type, selected_bin


def _build_network_links(
        topology: Dict[str, Any], site: Optional[Dict[str, Any]], policy: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Build network links with distances and cable types."""
    links = []

    # Build rack position lookup
    rack_positions = {}
    if site and "racks" in site:
        for rack in site["racks"]:
            rack_positions[rack["id"]] = rack["grid"]

    # Get spine rack position
    spine_rack = None
    if site and "spine" in site:
        spine_rack = site["spine"].get("rack_id")

    # Process spine to leaf connections
    spines = topology.get("spines", [])
    leafs = topology.get("leafs", [])

    for spine in spines:
        spine_interfaces = spine.get("interfaces", [])
        for interface in spine_interfaces:
            if "connects_to" in interface:
                # Parse connection (e.g., "tor-west-1:qsfp28-1")
                connection_parts = interface["connects_to"].split(":")
                if len(connection_parts) == 2:
                    leaf_id, leaf_port = connection_parts

                    # Find the leaf
                    leaf = next((lf for lf in leafs if lf["id"] == leaf_id), None)
                    if leaf:
                        leaf_rack = leaf.get("rack_id")

                        # Calculate distance
                        distance_m = 3.0  # Default fallback
                        if spine_rack and leaf_rack and spine_rack in rack_positions and leaf_rack in rack_positions:
                            heuristics = policy.get("heuristics", {})
                            tile_m = heuristics.get("tile_m", 1.0)
                            distance_m = _calculate_manhattan_distance(
                                rack_positions[spine_rack], rack_positions[leaf_rack], tile_m
                            )
                        elif site is None:
                            # Use heuristic distances from policy
                            heuristics = policy.get("heuristics", {})
                            if spine_rack == leaf_rack:
                                distance_m = heuristics.get("same_rack_leaf_to_node_m", 1.5)
                            else:
                                distance_m = heuristics.get("adjacent_rack_leaf_to_spine_m", 3)

                        # Determine link type
                        link_type = interface.get("type", "100G")

                        # Select cable type and bin
                        cable_type, length_bin = _select_cable_type_and_bin(
                            distance_m, link_type, policy, [1, 2, 3, 5, 7, 10]
                        )

                        links.append(
                            {
                                "from": f"{spine['id']}:{interface['name']}",
                                "to": f"{leaf_id}:{leaf_port}",
                                "type": link_type,
                                "distance_m": distance_m,
                                "cable_type": cable_type,
                                "length_bin": length_bin,
                                "category": "spine_to_leaf",
                            }
                        )

    # Add WAN connections if specified
    if site and "spine" in site and "wan_handoff" in site["spine"]:
        wan_handoff = site["spine"]["wan_handoff"]
        wan_count = wan_handoff.get("count", 2)
        wan_type = wan_handoff.get("type", "RJ45")

        for i in range(wan_count):
            cable_type, length_bin = _select_cable_type_and_bin(2.0, wan_type, policy, [1, 2, 3, 5, 7, 10])
            links.append(
                {
                    "from": f"spine-wan-{i + 1}",
                    "to": f"wan-router:{i + 1}",
                    "type": wan_type,
                    "distance_m": 2.0,
                    "cable_type": cable_type,
                    "length_bin": length_bin,
                    "category": "wan",
                }
            )

    return links
