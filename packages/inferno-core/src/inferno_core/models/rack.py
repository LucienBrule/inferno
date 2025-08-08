from typing import List

from pydantic import BaseModel


class Rack(BaseModel):
    id: str
    name: str
    location: str
    circle_ids: List[str]
