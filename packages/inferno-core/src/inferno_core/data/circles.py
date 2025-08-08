from pathlib import Path

from inferno_core.data.loader import load_yaml_list
from inferno_core.models.circle import Circle


def load_circles(path: Path = Path("doctrine/naming/circles.yaml")) -> list[Circle]:
    return load_yaml_list(path, Circle)


circles = load_circles()
