from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
        if isinstance(v, list | tuple) and len(v) == 2:
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
