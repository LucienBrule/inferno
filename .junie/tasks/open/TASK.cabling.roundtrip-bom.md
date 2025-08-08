

# TASK.cabling.roundtrip-bom — BOM ↔ Ports & Intent Reconciliation

**Owner:** Junie  
**State:** Ready  
**Area:** Networking / Cabling QA  
**Packages:** `inferno-tools`, `inferno-core`, `inferno-cli`

---

## Purpose
Verify that the **calculated BOM** (cables by class/type/bin) is self‑consistent and matches both:
1) the **declared intent** (topology + policy defaults), and 
2) the **available ports** on devices (ToR, spine, mgmt).

This is a strict “materials ↔ endpoints” closure test. It catches miscounts, spares rounding errors, and port over‑allocation **before** purchasing.

---

## Inputs
- **BOM** from calculation: `outputs/cabling_bom.yaml` (or user path).  
  - **Constraint:** Must be a valid YAML file conforming to the expected BOM schema (see below). Fail early if not.
- `doctrine/network/topology.yaml` — rack uplinks, WAN  
  - **Constraint:** Must be present and conform to schema. Fail if missing or malformed.
- `doctrine/network/tors.yaml` — device inventories & **port budgets**  
  - **Constraint:** Must be present and schema-valid.
- `doctrine/naming/nodes.yaml` — node NIC declarations (if absent, policy defaults apply)  
  - **Constraint:** If present, must pass schema validation. If absent, policy must define required defaults.
- `doctrine/network/cabling-policy.yaml` — spares fraction, defaults, media bins (only for meta reconstruction)  
  - **Constraint:** Must be present and schema-valid if referenced in BOM meta. If missing, must emit finding and use explicit fallback.
- `doctrine/site.yaml` *(optional; not required for roundtrip)*

### Expected BOM shape (schema)
```yaml
meta:
  spares_fraction: 0.10
  policy_path: doctrine/network/cabling-policy.yaml
  bins:
    sfp28_25g: [1,2,3,5,7,10]
items:
  - class: leaf-node        # leaf-node | leaf-spine | mgmt | wan
    cable_type: sfp28_25g   # qsfp28_100g | rj45_cat6a
    length_bin_m: 3
    quantity: 16            # includes spares
```
**Constraint:** The BOM file must conform to this schema; validation must pass before proceeding.

---

## Output
- **RoundtripReport YAML** (default `outputs/cabling_roundtrip.yaml`) with:
```yaml
summary:
  mismatched_counts: 0
  port_overalloc: 0
  unmapped_class: 0
  spares_rounding_adjustment: 0
findings:
  - severity: FAIL
    code: ROUNDTRIP_COUNT_MISMATCH
    message: "leaf-node SFP28: intent requires 16, BOM(core) provides 14"
    context:
      class: leaf-node
      cable_type: sfp28_25g
      expected_core: 16
      provided_core: 14
      spares_fraction: 0.10
ports_used:
  racks:
    rack-1:
      tor:
        sfp28_used: 8
        qsfp28_used: 2
  spine:
    qsfp28_used: 8
```
- **CLI** human summary with PASS/WARN/FAIL and top discrepancies.
- **Exit codes:** 0 (no FAIL), 1 (any FAIL). `--strict` upgrades WARN→exit 2.

---

## Core Concepts
- **Core quantity (pre‑spares):** If `meta.spares_fraction = s` and BOM `quantity = q`, reconstruct `core ≈ round_down(q / (1+s))`.
  - Keep both numbers: `provided_total = q`, `provided_core = core`.
  - If `abs(q - ceil(core*(1+s))) > 0`, emit **WARN** `ROUNDTRIP_SPARES_ROUNDING` with details.
- **Endpoint accounting:** Every cable produces **two terminations**. For validation we count **per‑endpoint‑type** to compare against **port budgets**:
  - `leaf-node (SFP28 25G)`: 1 end on **node SFP28**, 1 end on **ToR SFP28**.
  - `leaf-spine (QSFP28 100G)`: 1 end on **ToR QSFP28**, 1 end on **Spine QSFP28**.
  - `mgmt (RJ45)`: 1 end on **node RJ45 mgmt**, 1 end on **mgmt switch RJ45** *(or generic mgmt aggregator if not modeled)*.
  - `wan (RJ45)`: 1 end on **edge router RJ45**, 1 end on **WAN handoff** *(treated as external; budget not enforced)*.
- **Intent counts:**
  - `leaf-node`: sum **edge NICs** per rack from `nodes.yaml` (or policy `defaults.nodes_25g_per_node`).
  - `leaf-spine`: uplink counts from `topology.yaml` (per rack), or policy default.
  - `mgmt`: `defaults.mgmt_rj45_per_node × nodes` unless per‑node overrides exist.
  - `wan`: `topology.wan.uplinks_cat6a` when defined.

---

## Checks & Guardrails
1. **Count closure vs intent (per class/type/bin optional)**
   - Compare `expected_core` (intent) vs `provided_core` reconstructed from BOM for each **class/cable_type** pair.
   - **FAIL** `ROUNDTRIP_COUNT_MISMATCH` if different.
   - **Guardrail:** Do not proceed if schema validation fails on BOM or any manifest.
2. **Port budget closure (per device)**
   - Aggregate endpoints by device class using `provided_total` (post‑spares used in reality).
   - Compare to **available ports** in `tors.yaml` (and mgmt switch if modeled).
   - **FAIL** `ROUNDTRIP_PORT_OVERALLOC` when `used > total` for any `{device_id, port_type}`.
   - **INFO** `ROUNDTRIP_PORT_UTILIZATION` with percentages for ToRs and spine.
   - **Guardrail:** Do not assume any port default unless explicitly defined in policy or manifest. Emit **WARN** if falling back to any default value.
3. **Unmapped/unknown classes**
   - If a BOM `class` cannot be mapped to endpoints, **WARN** `ROUNDTRIP_UNMAPPED_CLASS` (include item stanza).
4. **Spares rounding anomalies**
   - When `q` doesn’t match `ceil(core*(1+s))`, **WARN** `ROUNDTRIP_SPARES_ROUNDING` (include both values, `s`).
5. **Missing policy**
   - If `spares_fraction` is missing anywhere, assume `0.0` and emit **INFO** `ROUNDTRIP_SPARES_DEFAULTED`.  
   - **Guardrail:** Always warn if using a fallback for a missing required field.

---

## Implementation Plan

### Engine (pure)
Create `packages/inferno-tools/src/inferno_tools/cabling/roundtrip.py`:
```python
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Severity = Literal["FAIL", "WARN", "INFO"]

class RoundtripFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    severity: Severity
    code: str
    message: str
    context: dict = Field(default_factory=dict)

class RoundtripReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    summary: dict
    findings: list[RoundtripFinding]
    ports_used: dict


def roundtrip_bom(
    bom_path: Path | str = Path("outputs/cabling_bom.yaml"),
    policy_path: Path | str | None = None,
) -> RoundtripReport:
    """Reconcile BOM cables with intent counts and device port budgets; return report."""
    # Guardrail: Validate all loaded manifests (BOM, topology, tors, nodes, policy) against their schemas using Pydantic v2 strict models before any reconciliation logic.
    # Fail early and return actionable error if any input is missing or malformed.
    ...
```
- **Guardrails:**  
  - Always use existing data loaders and shared validation utilities from `inferno_core.data.*` and `inferno_tools.cabling.common`.  
  - Do **not** duplicate parsing or validation logic.
  - Schema validation must pass on all manifests before reconciliation; fail early with clear errors otherwise.

### CLI
Add a subcommand under `tools cabling`:
```
inferno-cli tools cabling roundtrip \
  --bom outputs/cabling_bom.yaml \
  --export outputs/cabling_roundtrip.yaml \
  [--strict]
```
- Keep CLI subcommand logic minimal: no business logic or parsing; delegate all processing to `inferno-tools` engine functions.
- Print a short table: counts by class, and a ports utilization snippet per rack (ToR SFP28/QSFP28) + spine.
- Exit: 0 (no FAIL), 1 (any FAIL), 2 (WARN with `--strict`).

---

## Tests (pytest)
Create fixtures under `packages/inferno-tools/tests/fixtures/cabling/roundtrip/` and tests in `packages/inferno-tools/tests/test_cabling_roundtrip.py`:

1. **happy/** — BOM exactly matches intent; ports_used ≤ budgets. Expect **PASS**; utilization INFO present.
2. **count_mismatch/** — Delete a few leaf‑node entries from BOM; expect **FAIL** `ROUNDTRIP_COUNT_MISMATCH`.
3. **port_overalloc/** — Reduce ToR or spine port budgets; expect **FAIL** `ROUNDTRIP_PORT_OVERALLOC` with `{device_id, port_type, used, total}`.
4. **unmapped_class/** — Inject an unknown BOM `class`; expect **WARN** `ROUNDTRIP_UNMAPPED_CLASS`.
5. **spares_rounding/** — Set `spares_fraction: 0.15` and quantities that don’t align; expect **WARN** `ROUNDTRIP_SPARES_ROUNDING`.
6. **no_policy/** — Omit policy file; expect **INFO** `ROUNDTRIP_SPARES_DEFAULTED` and still PASS if counts align.

Each test asserts **finding codes**, severities, and that the YAML `ports_used` rollup matches the implied intent (e.g., leaf‑spine uses contribute to both ToR and spine).
- Write tests for both happy paths and failure modes (malformed/missing input, schema validation errors).

---

## Guidelines

- **Validation & Guardrails**
  - Always validate all loaded manifests (BOM, topology, tors, nodes, policy) using Pydantic v2 models with strict field validation.
  - Use existing data loaders and shared validation utilities from `inferno_core.data.*` and `inferno_tools.cabling.common`.  
  - Do **not** duplicate parsing or validation logic.
  - Fail early with clear, actionable error messages if any required input is missing or malformed.
  - Do not assume any defaults unless explicitly defined in policy or manifest. Emit a **WARN** or **INFO** finding if falling back to a default.
  - Schema validation must pass on all manifests before reconciliation proceeds.

- **CLI**
  - Keep CLI subcommand functions minimal; delegate all processing, validation, and reporting to `inferno-tools` engine functions.

- **Testing**
  - Write tests covering both happy paths and failure modes (including malformed or missing input, schema errors, unexpected classes).

- **Documentation**
  - Any new finding codes must be documented in the central findings reference (e.g., `docs/findings_reference.md`).

- **Modeling**
  - Use Pydantic v2 for all models and enforce strict field validation.

---

## Acceptance Criteria
- Roundtrip report produced and exported via CLI; exit codes per spec.
- All input manifests must pass schema validation before reconciliation; failure to do so must halt processing with actionable error.
- Count closure vs intent: accurate across all classes with or without `site.yaml`.
- Port budget checks trigger precise FAILs with actionable context.
- Spares reconstruction documented in findings when rounding applied.
- Test matrix above passes; suitable for CI gating.
