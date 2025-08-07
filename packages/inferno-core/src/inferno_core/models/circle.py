from typing import List
from pydantic import BaseModel


class Circle(BaseModel):
    id: str
    name: str
    role:  str
    circle: int
    rack_ids: List[str]
    nodes: List[str]