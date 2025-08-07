from pydantic import BaseModel

from inferno_core.models.chassis import Chassis


class Node(BaseModel):
    id: str
    hostname: str
    circle_id: str
    rack_id: str
    role: str
    chassis: Chassis