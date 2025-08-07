from pydantic import BaseModel


class Chassis(BaseModel):
    vendor: str
    model: str
    u_height: int
    gpus: int
    cpu: str
    ram_gb: int