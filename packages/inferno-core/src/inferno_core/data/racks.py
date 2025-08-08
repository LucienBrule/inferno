# inferno_core/data/racks.py
from pathlib import Path

from inferno_core.data.loader import load_yaml_file, load_yaml_list
from inferno_core.models import Rack


def load_racks(path: Path = Path("doctrine/naming/racks.yaml")) -> list[Rack]:
    return load_yaml_list(path, Rack)


racks = load_racks()
