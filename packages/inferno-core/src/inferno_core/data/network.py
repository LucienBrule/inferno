from pathlib import Path

from inferno_core.data.loader import load_yaml_file
from inferno_core.models.network import NetworkTopology


def load_network_topology(path: Path | str = Path("doctrine/network/topology.yaml")) -> NetworkTopology:
    try:
        # Try to load using unified topology loader first
        from inferno_core.data.unified_topology import load_topology_as_network_topology

        return load_topology_as_network_topology(path)
    except Exception:
        # Fallback to original format for backward compatibility
        data = load_yaml_file(path)
        return NetworkTopology(**data)


network_topology = load_network_topology()
