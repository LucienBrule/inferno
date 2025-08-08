# inferno_core/data/racks.py
from pathlib import Path

from inferno_core.data.loader import load_yaml_file
from inferno_core.models import Rack


def load_racks(path: Path = Path("doctrine/naming/racks.yaml")) -> list[Rack]:
    data = load_yaml_file(path)
    return [Rack(**entry) for entry in data]


racks = load_racks()
