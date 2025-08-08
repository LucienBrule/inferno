from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["FAIL", "WARN", "INFO"]


class CrossFinding(BaseModel):
    """A single cross-validation finding."""

    model_config = ConfigDict(extra="ignore")

    severity: Severity
    code: str
    message: str
    context: dict = Field(default_factory=dict)


class CrossReport(BaseModel):
    """Complete cross-validation report."""

    model_config = ConfigDict(extra="ignore")

    summary: dict
    findings: list[CrossFinding]
    mapping_stats: dict
