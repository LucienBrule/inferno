from pathlib import Path

from inferno_core.data.loader import load_yaml_typed, load_yaml_list
from inferno_core.models.tor import Tor


def load_tors_typed(path: str | Path) -> list[Tor]:
    """Preferred: strongly-typed policy loader (Pydantic v2)."""
    return load_yaml_list(Path(path), item_model=Tor)

