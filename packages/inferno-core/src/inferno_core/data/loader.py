import yaml
from pathlib import Path


def load_yaml_file(path: Path):
    with path.open("r") as f:
        return yaml.safe_load(f)
