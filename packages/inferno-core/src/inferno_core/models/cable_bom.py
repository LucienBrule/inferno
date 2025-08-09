from pydantic import BaseModel


class CableBOMSummary(BaseModel):
    metadata: dict[str, str | bool | int]
    summary: dict[str, str]
    findings: list[str]
