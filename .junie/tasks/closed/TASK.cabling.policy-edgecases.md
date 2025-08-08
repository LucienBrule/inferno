

# TASK.cabling.policy-edgecases — Policy Sanity & Edge‑Case Coverage

**Owner:** Junie  
**State:** Ready  
**Area:** Networking / Cabling QA  
**Packages:** `inferno-core`, `inferno-tools`, `inferno-cli`

---

## Purpose
Harden the cabling stack by stress‑testing **cabling-policy.yaml** parsing, normalization, and enforcement. Catch bad policies **before** calculation/validation, and ensure the validator emits precise, actionable findings.

## Scope / Non‑Goals
- **In scope:** schema sanity, numeric coercion, bin ordering & uniqueness, bounds/units checks, default fallbacks, redundancy/oversubscription rules, geometry heuristics bounds.
- **Out of scope:** live telemetry; physical discovery; visualization polish.

---

## Inputs
- `doctrine/network/cabling-policy.yaml` *(may be absent; engine defaults apply)*
- Optional context used by downstream checks:
  - `doctrine/network/topology.yaml`
  - `doctrine/network/tors.yaml`
  - `doctrine/naming/nodes.yaml`
  - `doctrine/site.yaml`

---

## Baseline Policy Shape (informative)
Minimal, with common keys used by calc/validation.

```yaml
# doctrine/network/cabling-policy.yaml
defaults:
  nodes_25g_per_node: 1        # int ≥ 0
  mgmt_rj45_per_node: 1        # int ≥ 0
  tor_uplink_qsfp28_per_tor: 2 # int ≥ 0
  spares_fraction: 0.10        # 0.0 ≤ x ≤ 1.0

site-defaults:
  num_racks: 4
  nodes_per_rack: 4
  uplinks_per_rack: 2
  mgmt_rj45_per_node: 1
  wan_cat6a: 2

media_rules:
  sfp28_25g:
    dac_max_m: 7
    bins_m: [1,2,3,5,7,10]
  qsfp28_100g:
    dac_max_m: 5
    bins_m: [1,2,3,5,7,10]
  rj45_cat6a:
    bins_m: [1,2,3,5,7,10,20,30]

redundancy:
  node_dual_homing: false
  tor_uplinks_min: 2

oversubscription:
  max_leaf_to_spine_ratio: 4.0  # > 0

heuristics:
  same_rack_leaf_to_node_m: 2.0 # > 0
  adjacent_rack_leaf_to_spine_m: 5.0 # > 0
  non_adjacent_rack_leaf_to_spine_m: 10.0 # > 0
  tile_m: 1.0                   # > 0
  slack_factor: 1.2             # ≥ 1.0
```

---

## Checks (to be enforced by validator)
Emit **FAIL/WARN/INFO** findings with stable codes (see below). Use Pydantic v2 validators for coercion; keep engines pure.

### A) Spares fraction
- `defaults.spares_fraction` present, numeric, **0.0 ≤ x ≤ 1.0**.
  - Not coercible to float → **FAIL** `POLICY_SPARES_TYPE`.
  - Out of range → **FAIL** `POLICY_SPARES_RANGE` (include value).

### B) Length bins (all media types)
- `bins_m` must be **non‑empty**, **strictly ascending**, **positive integers**.
  - Empty → **FAIL** `POLICY_BINS_EMPTY`.
  - Non‑ascending or duplicates → **FAIL** `POLICY_BINS_UNSORTED` / `POLICY_BINS_DUPLICATE`.
  - Non‑integer/≤0 values → **FAIL** `POLICY_BINS_INVALID`.

### C) DAC thresholds
- For optical/DAC capable media (`sfp28_25g`, `qsfp28_100g`), `dac_max_m` must be an **int ≥ 1**.
  - Missing with bins defined → **WARN** `POLICY_DAC_MAX_MISSING` (assume smallest bin as soft threshold).
  - Non‑int/≤0 → **FAIL** `POLICY_DAC_MAX_INVALID`.
  - If `dac_max_m < min(bins_m)` → **WARN** `POLICY_DAC_MAX_LT_SMALLEST_BIN`.

### D) Media presence / fallbacks
- If a media class (e.g., `qsfp28_100g`) is **absent** from policy:
  - If the engine has **built‑in defaults**, emit **WARN** `POLICY_MEDIA_MISSING_DEFAULTED` and proceed.
  - Else → **FAIL** `POLICY_MEDIA_MISSING`.

### E) RJ45 constraints
- `rj45_cat6a.bins_m` allowed up to **100 m** for 10G; bins **>100** → **WARN** `POLICY_RJ45_BINS_GT_100M` (not a hard fail; some gear negotiates lower speeds).

### F) Defaults and counts
- All `defaults.*` numerical fields must be **ints ≥ 0**.
  - Negative → **FAIL** `POLICY_DEFAULT_NEGATIVE` (include key).
  - Non‑int → **FAIL** `POLICY_DEFAULT_TYPE`.

### G) Redundancy rules
- `redundancy.node_dual_homing` is boolean if present; `redundancy.tor_uplinks_min` is **int ≥ 0**.
  - Type errors → **FAIL** `POLICY_REDUNDANCY_INVALID`.

### H) Oversubscription policy
- `oversubscription.max_leaf_to_spine_ratio` **float > 0**.
  - Missing → **WARN** `POLICY_OVERSUB_DEFAULTED` (use engine default 4.0).
  - Non‑positive/non‑numeric → **FAIL** `POLICY_OVERSUB_INVALID`.

### I) Geometry heuristics
- `heuristics.*` must be **float > 0** (except `slack_factor ≥ 1.0`).
  - Violations → **FAIL** `POLICY_HEURISTICS_INVALID` with key/value.

---

## Findings Schema (Pydantic v2)
```python
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Severity = Literal["FAIL", "WARN", "INFO"]

class Finding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    severity: Severity
    code: str
    message: str
    context: dict = Field(default_factory=dict)
```

All policy sanity findings should be grouped under a `Report` alongside other validation findings (see `TASK.cabling.validation.md`).

---

## Implementation
- **Where:** `packages/inferno-core/src/inferno_core/validation/policy.py`
- **Expose:**
```python
from pathlib import Path
from .models import Finding  # or reuse validation.cabling Finding

def validate_policy(policy_path: Path | str | None) -> list[Finding]:
    """Load policy (or defaults), run checks A–I, return findings."""
    ...
```
- **Integration:** Wire into the top‑level cabling validation flow so policy checks always run first. CLI should present a **Policy** section before topology checks.

---

## CLI
- Surfaces through existing command:
```
inferno-cli tools cabling validate [--strict] [--export findings.yaml] [--policy doctrine/network/cabling-policy.yaml]
```
- Exit codes follow validation rules (0/1/2). Policy FAILs alone should exit **1**.

---

## Tests (pytest)
Create fixtures under `packages/inferno-core/tests/fixtures/cabling/policy/` and tests in `packages/inferno-core/tests/test_policy_validation.py`:

1. **happy.yaml** — valid policy; **no findings**.
2. **spares_out_of_range.yaml** — `spares_fraction: 1.5` → **FAIL** `POLICY_SPARES_RANGE`.
3. **spares_type.yaml** — `spares_fraction: "ten"` → **FAIL** `POLICY_SPARES_TYPE`.
4. **bins_empty.yaml** — `sfp28_25g.bins_m: []` → **FAIL** `POLICY_BINS_EMPTY`.
5. **bins_unsorted.yaml** — `[1,3,2]` → **FAIL** `POLICY_BINS_UNSORTED`.
6. **bins_duplicate.yaml** — `[1,2,2,3]` → **FAIL** `POLICY_BINS_DUPLICATE`.
7. **dac_invalid.yaml** — `dac_max_m: 0` → **FAIL** `POLICY_DAC_MAX_INVALID`.
8. **media_missing_defaulted.yaml** — omit `qsfp28_100g` when engine has defaults → **WARN** `POLICY_MEDIA_MISSING_DEFAULTED`.
9. **rj45_over100.yaml** — RJ45 bins include 150 → **WARN** `POLICY_RJ45_BINS_GT_100M`.
10. **defaults_negative.yaml** — `nodes_25g_per_node: -1` → **FAIL** `POLICY_DEFAULT_NEGATIVE`.
11. **redundancy_invalid.yaml** — `node_dual_homing: 2` → **FAIL** `POLICY_REDUNDANCY_INVALID`.
12. **oversub_invalid.yaml** — `max_leaf_to_spine_ratio: 0` → **FAIL** `POLICY_OVERSUB_INVALID`.
13. **heuristics_invalid.yaml** — `slack_factor: 0.9` → **FAIL** `POLICY_HEURISTICS_INVALID`.

Each test asserts **Finding.code**, message substrings, and severities. A CLI smoke test should show policy failures causing exit code `1`.

---

## Acceptance Criteria
- Policy validation runs as part of `inferno-cli tools cabling validate` and can be invoked with a custom `--policy` path.
- All checks A–I produce stable codes and clear messages with the offending **key** and **value**.
- Test suite covers the 13 fixtures and passes.
- `guidelines.md` includes a short note: “Policy sanity checks run automatically; fix policy failures before calculating a BOM.”

--- END FILE ---