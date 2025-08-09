"""
Unified topology loader that can parse topology.yaml and create UnifiedTopology instances.

This loader can handle the current NetworkTopology format and automatically derive
capacity-level information for cabling calculations.
"""

from pathlib import Path
from typing import List

import yaml
from inferno_core.models.unified_topology import (
    UnifiedInterface,
    UnifiedPorts,
    UnifiedRack,
    UnifiedSwitch,
    UnifiedTopology,
    UnifiedWan,
)
from pydantic import ValidationError


def _read_yaml(path: Path | str) -> dict | list:
    """Read and parse YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ValueError(f"Empty or invalid YAML file: {path}")
        return data
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}")


def _derive_capacity_info(
    spines: List[UnifiedSwitch], leafs: List[UnifiedSwitch]
) -> tuple[UnifiedSwitch, List[UnifiedRack], UnifiedWan]:
    """
    Derive capacity-level information from interface-level topology.

    This function analyzes the interface connections to determine:
    - Spine capacity (total QSFP28 ports)
    - Rack configurations (rack_id, tor_id, uplink counts)
    - WAN configuration (estimated from remaining capacity)
    """

    # Analyze spine capacity
    spine_switch = spines[0] if spines else None
    if not spine_switch:
        raise ValueError("No spine switches found in topology")

    # Count QSFP28 interfaces on spine
    qsfp28_count = 0
    if spine_switch.interfaces:
        for iface in spine_switch.interfaces:
            if "100G" in iface.type or "QSFP" in iface.name.upper():
                qsfp28_count += 1

    # Create unified spine with capacity info
    spine_ports = UnifiedPorts(qsfp28_total=max(qsfp28_count, 32))  # Default to 32 if not enough interfaces
    unified_spine = UnifiedSwitch(
        id=spine_switch.id,
        rack_id=spine_switch.rack_id,
        model=spine_switch.model,
        nos=spine_switch.nos,
        interfaces=spine_switch.interfaces,
        ports=spine_ports,
    )

    # Analyze leaf switches to create rack configurations
    racks = []
    rack_uplink_counts = {}

    for leaf in leafs:
        if not leaf.rack_id:
            continue

        # Count uplinks to spine
        uplink_count = 0
        if leaf.interfaces:
            for iface in leaf.interfaces:
                if iface.connects_to and spine_switch.id in iface.connects_to:
                    uplink_count += 1

        # Default to 2 uplinks if none found
        if uplink_count == 0:
            uplink_count = 2

        rack_uplink_counts[leaf.rack_id] = uplink_count

        racks.append(UnifiedRack(rack_id=leaf.rack_id, tor_id=leaf.id, uplinks_qsfp28=uplink_count))

    # Estimate WAN configuration (default to 2 uplinks)
    total_rack_uplinks = sum(rack_uplink_counts.values())
    wan_uplinks = max(2, qsfp28_count - total_rack_uplinks) if qsfp28_count > total_rack_uplinks else 2
    wan = UnifiedWan(uplinks_cat6a=wan_uplinks)

    return unified_spine, racks, wan


def load_unified_topology(path: Path | str = Path("doctrine/network/topology.yaml")) -> UnifiedTopology:
    """
    Load topology from YAML and create a UnifiedTopology instance.

    This function can parse the current NetworkTopology format and automatically
    derive capacity-level information for cabling calculations.

    Args:
        path: Path to topology YAML file

    Returns:
        UnifiedTopology instance with both interface and capacity data

    Raises:
        ValidationError: If the YAML structure is invalid
        ValueError: If file is missing or malformed
        FileNotFoundError: If file doesn't exist
    """
    try:
        data = _read_yaml(path)

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict structure in {path}, got {type(data)}")

        # Parse spines
        spines_data = data.get("spines", [])
        spines = []
        for spine_data in spines_data:
            interfaces = []
            if "interfaces" in spine_data:
                for iface_data in spine_data["interfaces"]:
                    interfaces.append(
                        UnifiedInterface(
                            name=iface_data["name"], type=iface_data["type"], connects_to=iface_data.get("connects_to")
                        )
                    )

            spines.append(
                UnifiedSwitch(
                    id=spine_data["id"],
                    rack_id=spine_data.get("rack_id"),
                    model=spine_data["model"],
                    nos=spine_data.get("nos"),
                    interfaces=interfaces,
                )
            )

        # Parse leafs
        leafs_data = data.get("leafs", [])
        leafs = []
        for leaf_data in leafs_data:
            interfaces = []
            if "interfaces" in leaf_data:
                for iface_data in leaf_data["interfaces"]:
                    interfaces.append(
                        UnifiedInterface(
                            name=iface_data["name"], type=iface_data["type"], connects_to=iface_data.get("connects_to")
                        )
                    )

            leafs.append(
                UnifiedSwitch(
                    id=leaf_data["id"],
                    model=leaf_data["model"],
                    nos=leaf_data.get("nos"),
                    rack_id=leaf_data.get("rack_id"),
                    interfaces=interfaces,
                )
            )

        # Derive capacity information
        unified_spine, racks, wan = _derive_capacity_info(spines, leafs)

        # Create unified topology with both views
        return UnifiedTopology(
            # Interface-level view
            spines=spines,
            leafs=leafs,
            # Capacity-level view
            spine=unified_spine,
            racks=racks,
            wan=wan,
        )

    except ValidationError as e:
        raise ValueError(f"Invalid topology structure in {path}: {e}")


def load_unified_topology_from_capacity_format(path: Path | str) -> UnifiedTopology:
    """
    Load topology from capacity-focused YAML format (TopologyRec style).

    This is for backward compatibility with existing cabling test fixtures.
    """
    try:
        data = _read_yaml(path)

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict structure in {path}, got {type(data)}")

        # Parse spine
        spine_data = data.get("spine", {})
        spine_ports = UnifiedPorts(qsfp28_total=spine_data.get("ports", {}).get("qsfp28_total", 32))
        spine = UnifiedSwitch(id=spine_data["id"], model=spine_data["model"], ports=spine_ports)

        # Parse racks
        racks_data = data.get("racks", [])
        racks = []
        for rack_data in racks_data:
            racks.append(
                UnifiedRack(
                    rack_id=rack_data["rack_id"], tor_id=rack_data["tor_id"], uplinks_qsfp28=rack_data["uplinks_qsfp28"]
                )
            )

        # Parse WAN
        wan_data = data.get("wan", {})
        wan = UnifiedWan(uplinks_cat6a=wan_data.get("uplinks_cat6a", 2))

        return UnifiedTopology(spine=spine, racks=racks, wan=wan)

    except ValidationError as e:
        raise ValueError(f"Invalid topology structure in {path}: {e}")


# Backward compatibility functions
def load_topology_as_topology_rec(path: Path | str = Path("doctrine/network/topology.yaml")):
    """Load topology and return as TopologyRec for backward compatibility."""
    unified = load_unified_topology(path)
    return unified.to_topology_rec()


def load_topology_as_network_topology(path: Path | str = Path("doctrine/network/topology.yaml")):
    """Load topology and return as NetworkTopology for backward compatibility."""
    unified = load_unified_topology(path)
    return unified.to_network_topology()
