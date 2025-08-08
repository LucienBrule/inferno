<file name=0 path=TASK.cabling.intentional-corruption.md># TASK.cabling.intentional-corruption — Fuzzing & Failure-Mode QA

**Owner:** Junie  
**State:** Ready  
**Area:** Networking / Cabling QA  
**Packages:** `inferno-core`, `inferno-tools`, `inferno-cli`

---

## Purpose
Systematically **break** our manifests and BOMs to prove the stack fails **gracefully**:
- No Python stack traces
- Stable, actionable **Finding codes** with file/line context
- Deterministic **exit codes** (0/1/2)
- Clear guidance to fix input

This task complements calculation/validation by hardening loaders, cross‑file reference checks, and CLI error surfaces.

---

## Inputs Under Test
- `doctrine/network/topology.yaml`
- `doctrine/network/tors.yaml`
- `doctrine/naming/nodes.yaml`
- `doctrine/network/cabling-policy.yaml`
- `doctrine/site.yaml` (optional)
- `outputs/cabling_bom.yaml` (from calculate)

---

## Target Behavior
- **Loaders** (Pydantic v2) coerce only when safe; otherwise emit **FAIL** with precise codes.
- **Validators** short‑circuit on missing dependencies but continue to collect independent findings.
- **CLI** reports failures concisely and exits non‑zero; never prints raw tracebacks.

---

## Corruption Matrix (cases to cover)
For each family below, create one or more fixtures and expected findings.

### A) YAML syntax & encoding
1. **Syntax error** (bad indent/colon) → `LOAD_YAML_SYNTAX` (FAIL) with line/column.  
2. **Merge‑conflict markers** (`<<<<<<< HEAD`) → `LOAD_YAML_CONFLICT_MARKERS` (FAIL).  
3. **Non‑UTF8** / wrong BOM → `LOAD_YAML_ENCODING` (FAIL).  
4. **Trailing tabs/mixed indentation** → treat as (1) with helpful message.

### B) Schema shape/type
1. Type mismatch (string where int) → `LOAD_SCHEMA_TYPE` (FAIL), include key/value sample.  
2. Missing required field → `LOAD_SCHEMA_MISSING` (FAIL), include key path.  
3. Extra unknown fields → `LOAD_SCHEMA_EXTRA` (WARN) unless `strict` flips to FAIL.  
4. Enum/choice violation → `LOAD_SCHEMA_ENUM` (FAIL).

### C) Identity & duplication
1. Duplicate IDs within a file → `REF_DUPLICATE_ID` (FAIL).  
2. Cross‑file ID collision (e.g., two racks named same) → `REF_ID_COLLISION` (FAIL).

### D) Cross‑file references
1. Topology references unknown **rack_id** → `REF_UNKNOWN_RACK` (FAIL).  
2. Node references unknown **rack_id** → `REF_NODE_RACK_UNKNOWN` (FAIL).  
3. ToR references unknown **device_id** or wrong **rack_id** → `REF_TOR_UNKNOWN` (FAIL).  
4. Spine uplinks to unknown ToR → `REF_SPINE_TOR_UNKNOWN` (FAIL).

### E) Policy
1. Bad spares fraction (type/range) → `POLICY_SPARES_*` (see policy edge‑cases task).  
2. Non‑ascending or duplicate bins → `POLICY_BINS_*` (FAIL).  
3. Missing media stanza → `POLICY_MEDIA_MISSING[_DEFAULTED]` (FAIL/WARN).

### F) Geometry
1. Site racks outside expected grid or duplicate grid coords → `SITE_GEOMETRY_INVALID` (FAIL).  
2. Missing `site.yaml` entirely → `SITE_GEOMETRY_MISSING` (INFO), and downstream geometry checks skip gracefully.

### G) BOM shape/content
1. Negative/zero `quantity` → `BOM_QUANTITY_INVALID` (FAIL).  
2. Unknown `class` → `BOM_CLASS_UNKNOWN` (WARN).  
3. Unknown `cable_type` → `BOM_CABLE_TYPE_UNKNOWN` (FAIL).  
4. `length_bin_m` not in policy bins → `BOM_LENGTH_BIN_UNKNOWN` (FAIL).  
5. Missing `meta`/`spares_fraction` → `BOM_META_MISSING` (WARN) and assume `0.0`.

> **Note:** See the "Example Fixture" section below for explicit guardrails on `length_bin_m`, `cable_type`, and `quantity`, with cross-references to these BOM guardrails.

### H) Numerical pathologies
1. NaN/Infinity in numeric fields → `NUMERIC_INVALID` (FAIL).  
2. Values way out of range (e.g., 10^9 ports) → `NUMERIC_OUT_OF_RANGE` (FAIL).  
3. Negative power/lengths → `NUMERIC_NEGATIVE` (FAIL).

### I) Partial/empty files
1. Empty file → `LOAD_EMPTY_FILE` (FAIL).  
2. File missing on disk → `LOAD_FILE_NOT_FOUND` (FAIL).

---

## Finding Model (Pydantic v2)
Use the common shape across tasks:
```python
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Severity = Literal["FAIL", "WARN", "INFO"]

class Finding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    severity: Severity
    code: str
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    context: dict = Field(default_factory=dict)
```

Populate `file/line/column` when exceptions (e.g., PyYAML) expose `.problem_mark`.

---

## Implementation Plan

### 1) Loader hardening (`inferno_core.data.loader`)
- Wrap YAML load with rich error mapping:
  - `yaml.ScannerError`/`ParserError` → `LOAD_YAML_SYNTAX` with line/column.
  - UnicodeDecodeError → `LOAD_YAML_ENCODING`.
  - Empty content → `LOAD_EMPTY_FILE`.
- Convert Pydantic `ValidationError` to `LOAD_SCHEMA_*` with joined field paths.
- Detect conflict markers before parsing and raise `LOAD_YAML_CONFLICT_MARKERS`.
- Return **(data | None, findings: list[Finding])**; callers decide to proceed or abort.

### 2) Reference integrity (`inferno_core.validation.refs`)
- New module to cross‑check IDs **after** all loads; emit `REF_*` findings.

### 3) BOM guards (`inferno_tools.cabling.bom_io`)
- Safe read/write; validate shape; normalize numbers; emit `BOM_*` findings; never crash.

### 4) CLI behavior (`inferno-cli`)
- All cabling commands catch loader/validator findings; print a **Failures** section first; exit code:  
  - **1** if any FAIL  
  - **2** if any WARN and `--strict`  
  - **0** otherwise
- No tracebacks; for unexpected exceptions, catch and render `UNEXPECTED_ERROR` with a short fingerprint and request to file an issue.

---

## Fixtures & Fuzzing

### Hand‑crafted fixtures
Under `packages/inferno-core/tests/fixtures/corruption/` create directories mirroring the matrix (A–I). Each contains the minimal set of files to trigger the case and a `expected.yaml` listing expected finding codes.

### Property‑based fuzzing (optional, fast)
- Add `hypothesis` to `inferno-core` tests.  
- Create `tests/fuzz/test_yaml_mutations.py` that:
  - Starts from a valid dict fixture; applies small mutations (drop key, type flip, duplicate id, random NaN).  
  - Asserts: **no crash**, `findings` non‑empty, all severities ∈ {FAIL,WARN,INFO}, and codes are from the allowed set.

---

## Example Fixture (BOM with bad length)
```yaml
# outputs/cabling_bom.yaml

meta:
  # Optional metadata about the BOM; spares_fraction should be a float between 0.0 and 1.0
  spares_fraction: 0.1

items:
  - class: leaf-node               # Must be a known class; unknown classes yield BOM_CLASS_UNKNOWN (WARN)
    cable_type: sfp28_25g          # Must match allowed cable types from policy; unknown types yield BOM_CABLE_TYPE_UNKNOWN (FAIL)
    length_bin_m: 4                # Must exactly match one of the bins defined in cabling-policy.yaml; mismatch yields BOM_LENGTH_BIN_UNKNOWN (FAIL)
    quantity: 8                   # Must be a positive integer; zero or negative values yield BOM_QUANTITY_INVALID (FAIL)
```

**Guardrails:**  
- `length_bin_m` must match policy bins exactly.  
- `cable_type` must be one of the allowed types defined in the cabling policy.  
- `quantity` must be a positive integer greater than zero.

Any deviation from these constraints must yield deterministic findings with the correct finding codes and a non-zero exit code on CLI commands like `cross-validate` or `roundtrip`.

---

### Expected Finding Object for this Example
```python
Finding(
    severity="FAIL",
    code="BOM_LENGTH_BIN_UNKNOWN",
    message="The 'length_bin_m' value 4 is not defined in the cabling policy bins.",
    file="outputs/cabling_bom.yaml",
    line=7,
    column=None,
    context={"invalid_value": 4, "field": "length_bin_m"}
)
```

---

## Tests (pytest)
- Unit tests for loader mapping (syntax, encoding, empty) → exact line/col assertions.  
- Cross‑file reference tests (unknown rack/node/tor).  
- BOM shape tests (unknown class/type/bin; negative qty).  
- CLI smoke tests: run `calculate|validate|cross-validate|roundtrip` on broken fixtures; assert exit codes and presence of the expected codes in output.

---

## Acceptance Criteria
- Every corruption class A–I yields **deterministic** findings (stable codes) and non‑zero exit codes where appropriate.
- No unhandled exceptions; CLI never prints Python tracebacks for expected failures.
- Findings include **file** and, when available, **line/column**.
- Fuzz tests demonstrate robustness across random small mutations (no crashes in 1k seeds).

--- END FILE ---