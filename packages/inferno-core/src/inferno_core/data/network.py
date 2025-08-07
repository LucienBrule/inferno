from pathlib import Path

from inferno_core.data.loader import load_yaml_file
from inferno_core.models.network import NetworkTopology


def load_network_topology(path: Path = Path("doctrine/network/topology.yaml")) -> NetworkTopology:
    data = load_yaml_file(path)
    return NetworkTopology(**data)


network_topology = load_network_topology()