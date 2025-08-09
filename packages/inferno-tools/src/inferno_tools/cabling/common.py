"""Shared geometry utilities for cabling calculations and validation.

This module provides common functions for distance calculations, slack application,
and length bin selection to ensure consistency between calculation and validation paths.
"""

import math
from typing import Sequence, List, Dict, Any, Tuple, Optional

from inferno_core.models.cabling_policy import CablingPolicy
from inferno_core.models.network import NetworkTopology
from inferno_core.models.records import SiteRec

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


def with_spares(count: int, spares_fraction: float) -> int:
    return math.ceil(count * (1.0 + spares_fraction))


def calculate_manhattan_distance(rack1_grid: List[int], rack2_grid: List[int], tile_m: float = 1.0) -> float:
    """Calculate Manhattan distance between two racks in meters."""
    return compute_rack_distance_m((rack1_grid[0], rack1_grid[1]), (rack2_grid[0], rack2_grid[1]), tile_m)


def select_cable_type_and_bin(
    distance_m: float, link_type: str, policy: CablingPolicy, length_bins_m: List[int]
) -> Tuple[str, int]:
    """Select cable type and length bin based on distance and policy."""
    # Apply slack factor
    slack_factor = policy.heuristics.slack_factor  # 1.2
    adjusted_distance = apply_slack(distance_m, slack_factor)

    # Find appropriate length bin
    selected_bin = select_length_bin(adjusted_distance, length_bins_m)  # 1

    if selected_bin is None:
        selected_bin = max(length_bins_m)  # Use largest bin if distance exceeds all bins

    # Determine cable type based on link type and distance
    media_rules = policy.media_rules

    if link_type == "25G":
        rules = media_rules.get("sfp28_25g", {})
        dac_max = rules.dac_max_m
        if adjusted_distance <= dac_max:
            cable_type = rules.labels.dac
        elif adjusted_distance <= 10:
            cable_type = rules.labels.aoc
        else:
            cable_type = rules.labels.fiber
    elif link_type == "100G":
        rules = media_rules.get("qsfp28_100g", {})
        dac_max = rules.dac_max_m
        if adjusted_distance <= dac_max:
            cable_type = rules.labels.dac
        elif adjusted_distance <= 10:
            cable_type = rules.labels.aoc
        else:
            cable_type = rules.labels.fiber
    elif link_type == "RJ45":
        rules = media_rules.get("rj45_cat6a", {})
        cable_type = rules.labels.rj45
    else:
        cable_type = f"Unknown {link_type}"

    return cable_type, selected_bin


def build_network_links(topology: NetworkTopology, site: SiteRec, policy: CablingPolicy) -> List[Dict[str, Any]]:
    """Build network links with distances and cable types."""
    # TODO: Add type annotation to  links
    links = []

    # Build rack position lookup
    rack_positions = {}
    if site and site.racks is not None and len(site.racks) > 0 and site.racks[0].grid is not None:
        for rack in site.racks:
            rack_positions[rack.id] = rack.grid

    # Get spine rack position
    spine_rack = None
    if topology and topology.spines is not None and len(topology.spines) > 0:
        spine_rack = topology.spines[0].rack_id

    # Process spine to leaf connections
    spines = topology.spines
    leafs = topology.leafs
    """
       We have one spine:
       
       [Switch(
           id='spine-1',
           model='Mellanox SN2700',
           nos='Cumulus Linux (SONiC compatible)',
           interfaces=[
               Interface(
                   name='eth1/1',
                   type='100G',
                   connects_to='tor-west-1:qsfp28-1'
               ),
               Interface(
                   name='eth1/2',
                   type='100G',
                   connects_to='tor-east-1:qsfp28-1'
               ),
               Interface(
                   name='eth1/3',
                   type='100G',
                   connects_to='tor-north-1:qsfp28-1'
               ),
              Interface(
                   name='eth1/4',
                   type='100G',
                   connects_to='tor-crypt-1:qsfp28-1'
               )
           ],
           rack_id='rack-1'
        )]
    we have multiple leaves (4), e.g:
    [Switch(id='tor-west-1', model='Mellanox SN2410', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='qsfp28-1', type='100G', connects_to='spine-1:eth1/1'), Interface(name='qsfp28-2', type='100G', connects_to='spine-1:eth1/2')], rack_id='rack-1'), Switch(id='tor-east-1', model='Mellanox SN2410', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='qsfp28-1', type='100G', connects_to='spine-1:eth1/2'), Interface(name='qsfp28-2', type='100G', connects_to='spine-1:eth1/1')], rack_id='rack-2'), Switch(id='tor-north-1', model='Mellanox SN2410', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='qsfp28-1', type='100G', connects_to='spine-1:eth1/3')], rack_id='rack-3'), Switch(id='tor-crypt-1', model='Mellanox SN2410', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='qsfp28-1', type='100G', connects_to='spine-1:eth1/4')], rack_id='rack-4')]
    """
    for spine in spines:

        spine_interfaces = spine.interfaces  # redundant copy?
        for interface in spine_interfaces:
            if (
                interface.connects_to is not None  # True: they always have connects_to in valid yaml
                # and "leaf" in interface.connects_to.lower() # False: only if the connecting interface rack is named leaf for some reason TODO: FIXME
                and interface.type is not None  # True: they always have a type in valid yaml
            ):
                # Parse connection (e.g., "tor-west-1:qsfp28-1")
                connection_parts = interface.connects_to.split(":")  # ['tor-west-1', 'qsfp28-1']
                if len(connection_parts) == 2:
                    leaf_id, leaf_port = connection_parts

                    # Find the leaf
                    leaf = next(
                        filter(lambda x: x.id == leaf_id, leafs)
                    )  # Switch(id='tor-west-1', model='Mellanox SN2410', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='qsfp28-1', type='100G', connects_to='spine-1:eth1/1'), Interface(name='qsfp28-2', type='100G', connects_to='spine-1:eth1/2')], rack_id='rack-1')
                    if leaf:
                        leaf_rack = leaf.rack_id  # rack-1

                        # Calculate distance
                        distance_m = 3.0  # Default fallback
                        if (
                            spine_rack and leaf_rack and spine_rack in rack_positions and leaf_rack in rack_positions
                        ):  # True
                            heuristics = (
                                policy.heuristics
                            )  # Heuristics(same_rack_leaf_to_node_m=2.0, adjacent_rack_leaf_to_spine_m=10.0, non_adjacent_rack_leaf_to_spine_m=30.0, slack_factor=1.2, tile_m=1.0)
                            tile_m = heuristics.tile_m  # 1.0
                            distance_m = calculate_manhattan_distance(
                                rack_positions[spine_rack], rack_positions[leaf_rack], tile_m
                            )
                        elif site is None:
                            # Use heuristic distances from policy
                            heuristics = policy.heuristics
                            if spine_rack == leaf_rack:
                                distance_m = heuristics.same_rack_leaf_to_node_m
                            else:
                                distance_m = heuristics.adjacent_rack_leaf_to_spine_m

                        # Determine link type
                        link_type = interface.type  # 100G

                        # Select cable type and bin TODO: don't hard code the bin lengths here
                        cable_type, length_bin = select_cable_type_and_bin(
                            distance_m, link_type, policy, [1, 2, 3, 5, 7, 10]
                        )

                        links.append(
                            {
                                "from": f"{spine.id}:{interface.name}",
                                "to": f"{leaf_id}:{leaf_port}",
                                "type": link_type,
                                "distance_m": distance_m,
                                "cable_type": cable_type,
                                "length_bin": length_bin,
                                "category": "spine_to_leaf",
                            }
                        )

    # Add WAN connections if specified
    # site is the wrong attribute to check for wan_handoff
    # wan_handoff is not defined on any models
    # spine: SiteRec(racks=[SiteRackRec(id='rack-1', grid=(0, 0), tor_position_u=42), SiteRackRec(id='rack-2', grid=(1, 0), tor_position_u=42), SiteRackRec(id='rack-3', grid=(0, 1), tor_position_u=42), SiteRackRec(id='rack-4', grid=(1, 1), tor_position_u=42)])
    # might make sense to leave that under toplogy.yaml as an interface?
    # NetworkTopology(spines=[Switch(id='spine-1', model='Mellanox SN2700', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='eth1/1', type='100G', connects_to='tor-west-1:qsfp28-1'), Interface(name='eth1/2', type='100G', connects_to='tor-east-1:qsfp28-1'), Interface(name='eth1/3', type='100G', connects_to='tor-north-1:qsfp28-1'), Interface(name='eth1/4', type='100G', connects_to='tor-crypt-1:qsfp28-1')], rack_id='rack-1')], leafs=[Switch(id='tor-west-1', model='Mellanox SN2410', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='qsfp28-1', type='100G', connects_to='spine-1:eth1/1'), Interface(name='qsfp28-2', type='100G', connects_to='spine-1:eth1/2')], rack_id='rack-1'), Switch(id='tor-east-1', model='Mellanox SN2410', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='qsfp28-1', type='100G', connects_to='spine-1:eth1/2'), Interface(name='qsfp28-2', type='100G', connects_to='spine-1:eth1/1')], rack_id='rack-2'), Switch(id='tor-north-1', model='Mellanox SN2410', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='qsfp28-1', type='100G', connects_to='spine-1:eth1/3')], rack_id='rack-3'), Switch(id='tor-crypt-1', model='Mellanox SN2410', nos='Cumulus Linux (SONiC compatible)', interfaces=[Interface(name='qsfp28-1', type='100G', connects_to='spine-1:eth1/4')], rack_id='rack-4')])

    if site and "spine" in site and "wan_handoff" in site["spine"]:
        wan_handoff = site["spine"]["wan_handoff"]
        wan_count = wan_handoff.get("count", 2)
        wan_type = wan_handoff.get("type", "RJ45")

        for i in range(wan_count):
            cable_type, length_bin = select_cable_type_and_bin(2.0, wan_type, policy, [1, 2, 3, 5, 7, 10])
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
