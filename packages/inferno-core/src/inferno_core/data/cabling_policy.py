# inferno_core/data/cabling_policy.py
from __future__ import annotations
from pathlib import Path

from inferno_core.codebase.deprecation import deprecated
from inferno_core.data.loader import load_yaml_typed
from inferno_core.models.cabling_policy import CablingPolicy


def load_cabling_policy_typed(path: str | Path) -> CablingPolicy:
    """Preferred: strongly-typed policy loader (Pydantic v2)."""
    return load_yaml_typed(Path(path), model=CablingPolicy)


# Keep the old CLI-visible name as a thin wrapper, but steer callers over.
@deprecated(
    message="inferno_tools.cabling.cabling.load_cabling_policy is deprecated.",
    since="0.1.0",
    alternative="inferno_core.data.cabling_policy.load_cabling_policy_typed",
    remove_in="0.2.0",
    verbose=True,
    print_args=True,
    print_stack=True,
)
def load_cabling_policy(path: str | Path) -> CablingPolicy:
    return load_cabling_policy_typed(path)
