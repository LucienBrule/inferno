from inferno_core.models.chassis import Chassis
from pydantic import BaseModel


class Node(BaseModel):
    id: str
    hostname: str
    circle_id: str
    rack_id: str
    role: str
    chassis: Chassis
