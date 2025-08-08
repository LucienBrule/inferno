from pathlib import Path

from inferno_core.data.loader import load_yaml_file
from inferno_core.models import Node


def load_nodes(path: Path = Path("doctrine/naming/nodes.yaml")) -> list[Node]:
    data = load_yaml_file(path)
    return [Node(**entry) for entry in data]


nodes = load_nodes()
