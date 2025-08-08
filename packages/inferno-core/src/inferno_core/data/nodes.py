from pathlib import Path

from inferno_core.data.loader import load_yaml_file, load_yaml_list
from inferno_core.models import Node


def load_nodes(path: Path = Path("doctrine/naming/nodes.yaml")) -> list[Node]:
    return load_yaml_list(path, Node)


nodes = load_nodes()
