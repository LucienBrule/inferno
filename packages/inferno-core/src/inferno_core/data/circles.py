from pathlib import Path

from inferno_core.data.loader import load_yaml_file
from inferno_core.models.circle import Circle


def load_circles(path: Path = Path("doctrine/naming/circles.yaml")) -> list[Circle]:
    data = load_yaml_file(path)
    return [Circle(**entry) for entry in data]


circles = load_circles()