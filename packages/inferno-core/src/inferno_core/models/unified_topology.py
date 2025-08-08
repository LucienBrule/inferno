"""
Unified topology model that serves as a superset of NetworkTopology and TopologyRec.

This model supports both interface-level connectivity (NetworkTopology) and
rack-level capacity planning (TopologyRec) use cases.
"""

from typing import List, Optional

from inferno_core.models.network import NetworkTopology
from inferno_core.models.records import TopologyRec
from pydantic import BaseModel, ConfigDict, Field, field_validator


class UnifiedInterface(BaseModel):
    """Network interface with connection information."""

    model_config = ConfigDict(extra="ignore")
    name: str
    type: str  # e.g., "100G", "25G"
    connects_to: Optional[str] = None  # e.g., "spine-1:eth1/1"


class UnifiedPorts(BaseModel):
    """Port capacity information for switches."""

    model_config = ConfigDict(extra="ignore")
    sfp28_total: Optional[int] = Field(default=None, ge=0)
    qsfp28_total: Optional[int] = Field(default=None, ge=0)

    @field_validator("sfp28_total", "qsfp28_total", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return None if v is None else int(v)


class UnifiedSwitch(BaseModel):
    """Unified switch model supporting both interface and capacity views."""

    model_config = ConfigDict(extra="ignore")
    id: str
    model: str
    nos: Optional[str] = None  # Network OS
    rack_id: Optional[str] = None  # For leaf switches
    interfaces: Optional[List[UnifiedInterface]] = None  # Interface-level view
    ports: Optional[UnifiedPorts] = None  # Capacity view


class UnifiedRack(BaseModel):
    """Rack configuration for capacity planning."""

    model_config = ConfigDict(extra="ignore")
    rack_id: str
    tor_id: str
    uplinks_qsfp28: int = Field(ge=0)

    @field_validator("uplinks_qsfp28", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)


class UnifiedWan(BaseModel):
    """WAN uplink configuration."""

    model_config = ConfigDict(extra="ignore")
    uplinks_cat6a: int = Field(ge=0)

    @field_validator("uplinks_cat6a", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)


class UnifiedTopology(BaseModel):
    """
    Unified topology model that supports both interface-level and capacity-level views.

    This model can be populated from either NetworkTopology or TopologyRec formats
    and provides methods to convert between them.
    """

    model_config = ConfigDict(extra="ignore")

    schema_version: str = Field(default="1.0")

    # Interface-level view (NetworkTopology compatibility)
    spines: Optional[List[UnifiedSwitch]] = None
    leafs: Optional[List[UnifiedSwitch]] = None

    # Capacity-level view (TopologyRec compatibility)
    spine: Optional[UnifiedSwitch] = None
    racks: Optional[List[UnifiedRack]] = None
    wan: Optional[UnifiedWan] = None

    def has_interface_view(self) -> bool:
        return self.spines is not None and self.leafs is not None

    def has_capacity_view(self) -> bool:
        return self.spine is not None and self.racks is not None and self.wan is not None

    def require_interface_view(self) -> None:
        if not self.has_interface_view():
            raise ValueError("Interface-level data (spines/leafs) not available")

    def require_capacity_view(self) -> None:
        if not self.has_capacity_view():
            raise ValueError("Capacity-level data (spine/racks/wan) not available")

    @field_validator("leafs", mode="after")
    @classmethod
    def _validate_leafs_have_rack(cls, v):
        # If leaf switches are provided, encourage rack_id presence
        if v is None:
            return v
        for sw in v:
            if getattr(sw, "rack_id", None) is None:
                # Allow but warn by raising a clear error to upstream callers if needed
                # For now we accept None to remain permissive; downstream calculate will fail if required
                pass
        return v

    def to_network_topology(self) -> NetworkTopology:
        """Convert to NetworkTopology format."""
        from inferno_core.models.network import Interface, NetworkTopology, Switch

        self.require_interface_view()

        spines = []
        for spine in self.spines:
            interfaces = []
            if spine.interfaces:
                for iface in spine.interfaces:
                    interfaces.append(Interface(name=iface.name, type=iface.type, connects_to=iface.connects_to or ""))
            spines.append(
                Switch(
                    id=spine.id, model=spine.model, nos=spine.nos or "", interfaces=interfaces, rack_id=spine.rack_id
                )
            )

        leafs = []
        for leaf in self.leafs:
            interfaces = []
            if leaf.interfaces:
                for iface in leaf.interfaces:
                    interfaces.append(Interface(name=iface.name, type=iface.type, connects_to=iface.connects_to or ""))
            leafs.append(
                Switch(id=leaf.id, model=leaf.model, nos=leaf.nos or "", interfaces=interfaces, rack_id=leaf.rack_id)
            )

        return NetworkTopology(spines=spines, leafs=leafs)

    def to_topology_rec(self) -> TopologyRec:
        """Convert to TopologyRec format."""
        from inferno_core.models.records import (
            SpinePorts,
            SpineRec,
            TopologyRackRec,
            TopologyRec,
            TopologyWanRec,
        )

        self.require_capacity_view()

        qs_total = 0
        if self.spine and self.spine.ports and self.spine.ports.qsfp28_total is not None:
            qs_total = int(self.spine.ports.qsfp28_total)
        spine_ports = SpinePorts(qsfp28_total=qs_total)
        spine_rec = SpineRec(id=self.spine.id, model=self.spine.model, ports=spine_ports)

        # Convert racks
        rack_recs = []
        for rack in self.racks:
            rack_recs.append(
                TopologyRackRec(rack_id=rack.rack_id, tor_id=rack.tor_id, uplinks_qsfp28=rack.uplinks_qsfp28)
            )

        # Convert WAN
        wan_rec = TopologyWanRec(uplinks_cat6a=self.wan.uplinks_cat6a)

        return TopologyRec(spine=spine_rec, racks=rack_recs, wan=wan_rec)

    @classmethod
    def from_network_topology(cls, nt: NetworkTopology) -> "UnifiedTopology":
        """Create UnifiedTopology from NetworkTopology."""
        spines = []
        for spine in nt.spines:
            interfaces = []
            for iface in spine.interfaces:
                interfaces.append(UnifiedInterface(name=iface.name, type=iface.type, connects_to=iface.connects_to))
            spines.append(
                UnifiedSwitch(
                    id=spine.id, model=spine.model, nos=spine.nos, rack_id=spine.rack_id, interfaces=interfaces
                )
            )

        leafs = []
        for leaf in nt.leafs:
            interfaces = []
            for iface in leaf.interfaces:
                interfaces.append(UnifiedInterface(name=iface.name, type=iface.type, connects_to=iface.connects_to))
            leafs.append(
                UnifiedSwitch(id=leaf.id, model=leaf.model, nos=leaf.nos, rack_id=leaf.rack_id, interfaces=interfaces)
            )

        return cls(spines=spines, leafs=leafs)

    @classmethod
    def from_topology_rec(cls, tr: TopologyRec) -> "UnifiedTopology":
        """Create UnifiedTopology from TopologyRec."""
        # Convert spine
        spine_ports = UnifiedPorts(qsfp28_total=tr.spine.ports.qsfp28_total)
        spine = UnifiedSwitch(id=tr.spine.id, model=tr.spine.model, ports=spine_ports)

        # Convert racks
        racks = []
        for rack in tr.racks:
            racks.append(UnifiedRack(rack_id=rack.rack_id, tor_id=rack.tor_id, uplinks_qsfp28=rack.uplinks_qsfp28))

        # Convert WAN
        wan = UnifiedWan(uplinks_cat6a=tr.wan.uplinks_cat6a)

        return cls(spine=spine, racks=racks, wan=wan)
