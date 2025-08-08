from typing import List, Literal, Optional

from pydantic import BaseModel


class PowerCircuit(BaseModel):
    id: str
    voltage: Literal[120, 240]
    amperage: int
    racks: list[str]


class PowerFeed(BaseModel):
    id: str
    circuit_type: str
    voltage: Literal[120, 240]
    amperage: int
    phase: Literal["single", "three"]
    breaker_panel: str
    rack_ids: List[str]
    notes: Optional[str] = None


class Outlet(BaseModel):
    type: str  # e.g., 'C13' or 'C19'
    quantity: int


class PDU(BaseModel):
    id: str
    rack_id: str
    feed: str  # e.g., 'A' or 'B'
    model: str
    type: str  # e.g., 'switched + metered'
    form_factor: str  # e.g., '0U'
    input: dict  # contains 'plug', 'voltage', 'amperage'
    output_outlets: List[Outlet]
    management: str
    notes: Optional[str] = None


class UPS(BaseModel):
    id: str
    rack_id: str
    model: str
    type: str  # e.g., 'double-conversion'
    capacity_va: int
    capacity_watts: int
    input_plug: str
    output_outlets: List[Outlet]
    form_factor: str  # e.g., '2U'
    management: str  # e.g., 'SNMP, Web, USB'
    estimated_runtime_minutes: float
    notes: Optional[str] = None
