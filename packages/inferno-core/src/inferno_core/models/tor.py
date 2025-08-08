from pydantic import BaseModel


class Tor(BaseModel):
    id: str
    rack_id: str
    model: str
    ports: dict[str, int]