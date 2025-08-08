# TASK.cabling.loader — Manifest Loaders for Cabling Engine (Pydantic v2)

**Owner:** Copilot (paired with Solien)  
**Status:** Ready for implementation  
**Scope:** Implement robust YAML loaders for cabling-related manifests used by `inferno-cli tools cabling calculate|validate|visualize`, using **Pydantic v2** models for validation/normalization.

## 🎯 Purpose
Provide a clean, validated ingestion layer that reads site/network manifests and returns **Pydantic v2** models the cabling engine can use deterministically (no CLI parsing or heuristics here). This isolates I/O and schema concerns from calculation logic.

## ✅ Acceptance Criteria
- Functions exist under `inferno_core.data.network_loader` with the **exact signatures** below.
- Loaders parse **YAML only** (no Markdown/regex) and return **Pydantic v2** models.
- Missing optional fields default sensibly; **required fields raise** `pydantic.ValidationError` (preferred) or `ValueError` with a helpful message (include file + field).
- Loaders are **pure** (no printing). They may raise on invalid input.
- Basic unit tests exist under `packages/inferno-core/tests/` and pass locally (pytest).
- **Dependency added:** `pydantic>=2.5,<3` to `packages/inferno-core/pyproject.toml`.
- No changes to CLI; only the ingestion layer.

## 📁 Files to Create/Edit
- `packages/inferno-core/src/inferno_core/data/network_loader.py` **(new)**
- `packages/inferno-core/tests/test_network_loader.py` **(new)**
- `packages/inferno-core/pyproject.toml` (ensure `pydantic>=2.5,<3` present)

> Do **not** modify `inferno_tools.cabling` in this task. We will wire these loaders in a later task.

## 🧩 Inputs & Minimal Schemas
These reflect what we already modeled in doctrine; keep the loader tolerant but strict on required keys.

### 1) `doctrine/network/topology.yaml`
```yaml
spine:
  id: spine-1
  model: mellanox-sn2700
racks:
  - rack_id: rack-1
    tor_id: tor-1
    uplinks_qsfp28: 2  # QSFP28 100G uplinks from this ToR to spine
  - rack_id: rack-2
    tor_id: tor-2
    uplinks_qsfp28: 2
wan:
  uplinks_cat6a: 2
```

### 2) `doctrine/network/tors.yaml`
```yaml
tors:
  - id: tor-1
    rack_id: rack-1
    model: sn2410
    ports:
      sfp28_total: 48
      qsfp28_total: 8
  - id: tor-2
    rack_id: rack-2
    model: sn2410
    ports:
      sfp28_total: 48
      qsfp28_total: 8
spine:
  id: spine-1
  model: sn2700
  ports:
    qsfp28_total: 32
```

### 3) `doctrine/naming/nodes.yaml`
```yaml
- id: node-1
  hostname: inferno-n1
  rack_id: rack-1
  nics:                # optional
    - type: SFP28      # one of: SFP28 | QSFP28 | RJ45
      count: 1
    - type: RJ45
      count: 1
- id: node-2
  rack_id: rack-1
```

### 4) `doctrine/site.yaml` (optional)
```yaml
racks:
  - id: rack-1
    grid: [0, 0]        # integer grid coords for Manhattan distance
    tor_position_u: 42  # optional; U location of ToR
  - id: rack-2
    grid: [1, 0]
```

## 🧪 Output Contracts (Pydantic v2)
Use **Pydantic v2** models with validators for coercion/normalization. Prefer explicit submodels over raw dicts.

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

NicType = Literal["SFP28", "QSFP28", "RJ45"]

class NicRec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: NicType
    count: int = Field(default=1, ge=1)

    @field_validator("count", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)

class NodeRec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    rack_id: str
    hostname: str | None = None
    nics: list[NicRec] = Field(default_factory=list)

class TorPorts(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sfp28_total: int = Field(ge=0)
    qsfp28_total: int = Field(ge=0)

    @field_validator("sfp28_total", "qsfp28_total", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)

class TorRec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    rack_id: str
    model: str
    ports: TorPorts

class SpinePorts(BaseModel):
    model_config = ConfigDict(extra="ignore")
    qsfp28_total: int = Field(ge=0)

    @field_validator("qsfp28_total", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)

class SpineRec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    model: str
    ports: SpinePorts

class TopologyRackRec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rack_id: str
    tor_id: str
    uplinks_qsfp28: int = Field(ge=0)

    @field_validator("uplinks_qsfp28", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)

class TopologyWanRec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    uplinks_cat6a: int = Field(ge=0)

    @field_validator("uplinks_cat6a", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)

class TopologyRec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    spine: SpineRec
    racks: list[TopologyRackRec]
    wan: TopologyWanRec

class SiteRackRec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    grid: tuple[int, int] | None = None
    tor_position_u: int | None = None

    @field_validator("grid", mode="before")
    @classmethod
    def _coerce_grid(cls, v):
        if v is None:
            return None
        if isinstance(v, (list, tuple)) and len(v) == 2:
            x, y = v
        elif isinstance(v, str):
            # allow "x,y"
            parts = [p.strip() for p in v.split(",")]
            if len(parts) != 2:
                raise ValueError("grid must be two integers")
            x, y = parts
        else:
            raise ValueError("grid must be [x, y] or 'x,y'")
        return (int(x), int(y))

    @field_validator("tor_position_u", mode="before")
    @classmethod
    def _coerce_u(cls, v):
        return None if v is None else int(v)

class SiteRec(BaseModel):
    model_config = ConfigDict(extra="ignore")
    racks: list[SiteRackRec]
```

## 🧰 Functions to Implement
Place in `inferno_core/data/network_loader.py` with docstrings and type hints.

```python
from pathlib import Path
from typing import Iterable
from pydantic import ValidationError, TypeAdapter

# Return a validated model; raise ValidationError/ValueError on schema issues

def load_topology(path: Path | str = Path("doctrine/network/topology.yaml")) -> TopologyRec: ...

# Return list of ToRs and optional spine from tors.yaml

def load_tors(path: Path | str = Path("doctrine/network/tors.yaml")) -> tuple[list[TorRec], SpineRec | None]: ...

# Return validated list of nodes

def load_nodes(path: Path | str = Path("doctrine/naming/nodes.yaml")) -> list[NodeRec]: ...

# Optional — return None if file missing

def load_site(path: Path | str = Path("doctrine/site.yaml")) -> SiteRec | None: ...
```

### Normalization Rules (enforced via Pydantic v2)
- Coerce counts and numeric fields via `@field_validator(..., mode="before")` to `int`.
- `nics` missing ⇒ `[]` (model default).
- `hostname` missing ⇒ `None` (model default).
- For `site.yaml`, if file doesn’t exist ⇒ return `None` (not an error).
- For `grid`, accept list/tuple or `'x,y'` strings; normalize to `tuple[int,int]`.
- Light cross-reference validation: ensure each `TopologyRackRec` has non-empty `rack_id` and `tor_id`.
- Use `ConfigDict(extra="ignore")` so unknown keys don’t explode.

### Error Handling
Raise **`pydantic.ValidationError`** (preferred) or **`ValueError`** with context on:
- Missing required files (except `site.yaml`).
- Missing required keys per schema (e.g., `spine.id`, `racks[*].rack_id`).
- Wrong types (e.g., `uplinks_qsfp28: "two"`).

## 🧪 Tests (pytest)
Create `packages/inferno-core/tests/test_network_loader.py` with fixtures containing **inline YAML** written to tmp paths. Cover:
- Happy path for each loader.
- Missing optional fields defaults (e.g., node without `nics`).
- Type coercion (counts as strings -> ints; grid as `'1,2'`).
- Error paths (missing required key, wrong type) and assert `ValidationError`.
- `site.yaml` absent ⇒ `None`.

## 🔧 Implementation Notes for Copilot
- Use a small private helper `_read_yaml(path) -> dict|list` with `yaml.safe_load`.
- Parse lists with `TypeAdapter(list[NodeRec]).validate_python(data)` for strong typing.
- Keep functions pure (no console I/O) and let callers decide how to handle exceptions.
- Do not import CLI or calculation code here.

## 🧵 Milestone Done When
- Running `pytest packages/inferno-core/tests/test_network_loader.py -q` passes.
- Importing these functions from a Python REPL and calling them on the repo’s actual doctrine files returns validated **Pydantic v2** models (or helpful exceptions).