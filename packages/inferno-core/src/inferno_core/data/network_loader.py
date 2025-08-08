"""
Network manifest loaders for cabling engine using Pydantic v2.

This module provides robust YAML loaders for cabling-related manifests
used by inferno-cli tools cabling calculate|validate|visualize.
"""

from pathlib import Path
from typing import Any

import yaml
from inferno_core.models.records import NodeRec, SiteRec, SpineRec, TopologyRec, TorRec
from pydantic import TypeAdapter, ValidationError


def _read_yaml(path: Path | str) -> dict | list:
    """Read a YAML file and return a dict or list.
    - Ensures UTF-8 decode
    - Raises on empty/unsupported top-level content
    - Normalizes YAML errors to ValueError with file context
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"Unable to decode UTF-8 in {p}: {e}") from e

    try:
        data: Any = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {p}: {e}") from e

    if data is None:
        raise ValueError(f"Empty YAML file: {p}")

    if not isinstance(data, dict | list):
        raise ValueError(f"Unsupported top-level YAML type {type(data).__name__} in {p}; expected dict or list")

    if isinstance(data, dict) and not data:
        raise ValueError(f"YAML object is empty in {p}")
    if isinstance(data, list) and not data:
        raise ValueError(f"YAML list is empty in {p}")

    return data


def load_topology(path: Path | str = Path("doctrine/network/topology.yaml")) -> TopologyRec:
    """
    Load and validate network topology configuration.
    Prefers the unified topology format but supports the legacy TopologyRec shape.
    """
    try:
        data = _read_yaml(path)
    except Exception:
        # propagate consistent error types
        raise

    # 1) Unified format → TopologyRec
    try:
        from inferno_core.data.unified_topology import (
            UnifiedTopology,  # local import to avoid cycles
        )

        ut = UnifiedTopology.model_validate(data)
        if ut.has_capacity_view():
            return ut.to_topology_rec()
        # If unified parsed but lacks capacity view, fall through to legacy
    except Exception:
        pass

    # 2) Legacy TopologyRec format
    try:
        return TopologyRec.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid topology structure in {path}: {e}")


def load_tors(path: Path | str = Path("doctrine/network/tors.yaml")) -> tuple[list[TorRec], SpineRec | None]:
    """
    Load and validate ToR and spine switch configurations.

    Args:
        path: Path to ToRs YAML file

    Returns:
        Tuple of (list of ToR records, optional spine record)

    Raises:
        ValidationError: If the YAML structure is invalid
        ValueError: If file is missing or malformed
        FileNotFoundError: If file doesn't exist
    """
    try:
        data = _read_yaml(path)

        if not isinstance(data, dict):
            raise ValueError(f"Expected dict structure in {path}, got {type(data)}")

        # Extract ToRs
        tors_data = data.get("tors", [])
        if not isinstance(tors_data, list):
            raise ValueError(f"'tors' must be a list in {path}")

        tors = TypeAdapter(list[TorRec]).validate_python(tors_data)

        # Extract optional spine
        spine = None
        spine_data = data.get("spine")
        if spine_data is not None:
            spine = SpineRec.model_validate(spine_data)

        return tors, spine

    except ValidationError as e:
        raise ValueError(f"Invalid ToRs structure in {path}: {e}")


def load_nodes(path: Path | str = Path("doctrine/naming/nodes.yaml")) -> list[NodeRec]:
    """
    Load and validate node configurations.

    Args:
        path: Path to nodes YAML file

    Returns:
        List of validated node records

    Raises:
        ValidationError: If the YAML structure is invalid
        ValueError: If file is missing or malformed
        FileNotFoundError: If file doesn't exist
    """
    try:
        data = _read_yaml(path)

        if not isinstance(data, list):
            raise ValueError(f"Expected list structure in {path}, got {type(data)}")

        return TypeAdapter(list[NodeRec]).validate_python(data)

    except ValidationError as e:
        raise ValueError(f"Invalid nodes structure in {path}: {e}")


def load_site(path: Path | str = Path("doctrine/site.yaml")) -> SiteRec | None:
    """
    Load and validate site configuration (optional).

    Args:
        path: Path to site YAML file

    Returns:
        Validated site configuration or None if file doesn't exist

    Raises:
        ValidationError: If the YAML structure is invalid
        ValueError: If file is malformed
    """
    path = Path(path)
    if not path.exists():
        return None

    try:
        data = _read_yaml(path)
        return SiteRec.model_validate(data)

    except ValidationError as e:
        raise ValueError(f"Invalid site structure in {path}: {e}")
