from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["FAIL", "WARN", "INFO"]


class Finding(BaseModel):
    """A single validation finding with severity, code, message, and context."""

    model_config = ConfigDict(extra="ignore")
    severity: Severity
    code: str
    message: str
    context: dict = Field(default_factory=dict)


class Report(BaseModel):
    """Complete validation report with summary and findings."""

    model_config = ConfigDict(extra="ignore")
    summary: dict
    findings: list[Finding]
