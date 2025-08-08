# inferno_core/models/network.py

from typing import List, Optional

from pydantic import BaseModel


class Interface(BaseModel):
    name: str
    type: str  # e.g., "100G", "25G"
    connects_to: str  # e.g., "spine-1:eth1/1"


class Switch(BaseModel):
    id: str
    model: str
    nos: str
    interfaces: List[Interface]
    rack_id: Optional[str] = None  # only present for leaf switches


class NetworkTopology(BaseModel):
    spines: List[Switch]
    leafs: List[Switch]
