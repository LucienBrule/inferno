"""
Network manifest loaders for cabling engine using Pydantic v2.

This module provides robust YAML loaders for cabling-related manifests
used by inferno-cli tools cabling calculate|validate|visualize.
"""

from __future__ import annotations
from pathlib import Path
from typing import Literal, Iterable
import yaml
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError, TypeAdapter

# Type definitions
NicType = Literal["SFP28", "QSFP28", "RJ45"]


class NicRec(BaseModel):
    """Network interface card record."""
    model_config = ConfigDict(extra="ignore")
    type: NicType
    count: int = Field(default=1, ge=1)

    @field_validator("count", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)


class NodeRec(BaseModel):
    """Node record with networking information."""
    model_config = ConfigDict(extra="ignore")
    id: str
    rack_id: str
    hostname: str | None = None
    nics: list[NicRec] = Field(default_factory=list)


class TorPorts(BaseModel):
    """Top-of-rack switch port configuration."""
    model_config = ConfigDict(extra="ignore")
    sfp28_total: int = Field(ge=0)
    qsfp28_total: int = Field(ge=0)

    @field_validator("sfp28_total", "qsfp28_total", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)


class TorRec(BaseModel):
    """Top-of-rack switch record."""
    model_config = ConfigDict(extra="ignore")
    id: str
    rack_id: str
    model: str
    ports: TorPorts


class SpinePorts(BaseModel):
    """Spine switch port configuration."""
    model_config = ConfigDict(extra="ignore")
    qsfp28_total: int = Field(ge=0)

    @field_validator("qsfp28_total", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)


class SpineRec(BaseModel):
    """Spine switch record."""
    model_config = ConfigDict(extra="ignore")
    id: str
    model: str
    ports: SpinePorts


class TopologyRackRec(BaseModel):
    """Rack record in topology configuration."""
    model_config = ConfigDict(extra="ignore")
    rack_id: str
    tor_id: str
    uplinks_qsfp28: int = Field(ge=0)

    @field_validator("uplinks_qsfp28", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)


class TopologyWanRec(BaseModel):
    """WAN uplink configuration."""
    model_config = ConfigDict(extra="ignore")
    uplinks_cat6a: int = Field(ge=0)

    @field_validator("uplinks_cat6a", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)


class TopologyRec(BaseModel):
    """Complete topology configuration."""
    model_config = ConfigDict(extra="ignore")
    spine: SpineRec
    racks: list[TopologyRackRec]
    wan: TopologyWanRec


class SiteRackRec(BaseModel):
    """Site-specific rack configuration."""
    model_config = ConfigDict(extra="ignore")
    id: str
    grid: tuple[int, int] | None = None
    tor_position_u: int | None = None

    @field_validator("grid", mode="before")
    @classmethod
    def _coerce_grid(cls, v):
        if v is None:
            return None
        if isinstance(v, (list, tuple)) and len(v) == 2:
            x, y = v
        elif isinstance(v, str):
            # allow "x,y"
            parts = [p.strip() for p in v.split(",")]
            if len(parts) != 2:
                raise ValueError("grid must be two integers")
            x, y = parts
        else:
            raise ValueError("grid must be [x, y] or 'x,y'")
        return (int(x), int(y))

    @field_validator("tor_position_u", mode="before")
    @classmethod
    def _coerce_u(cls, v):
        return None if v is None else int(v)


class SiteRec(BaseModel):
    """Site configuration with rack layout."""
    model_config = ConfigDict(extra="ignore")
    racks: list[SiteRackRec]


def _read_yaml(path: Path | str) -> dict | list:
    """Read and parse YAML file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if data is None:
            raise ValueError(f"Empty or invalid YAML file: {path}")
        return data
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}")


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
        from inferno_core.data.unified_topology import UnifiedTopology  # local import to avoid cycles
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