

# TASK.cabling.cross-validation — Reconcile BOM vs Topology/Policy

**Owner:** Junie  
**State:** Ready  
**Area:** Networking / Cabling QA  
**Packages:** `inferno-core`, `inferno-tools`, `inferno-cli`

---

## Purpose
Build a **cross‑validation pass** that reconciles the **calculated BOM** against the **declared intent** (topology + policy + site geometry). Detect **phantom** items (present in BOM but not implied by topology), **missing** items (implied by topology but absent in BOM), and **mismatches** (wrong media/length bin). Output a machine‑readable report for CI and a human summary for the CLI.

> This is the glue between `calculate` and `validate` — proving that our calculated materials align with the declared network design.

---

## Inputs
- `doctrine/network/topology.yaml`
- `doctrine/network/tors.yaml`
- `doctrine/naming/nodes.yaml`
- `doctrine/site.yaml` *(optional for geometry/lengths)*
- `doctrine/network/cabling-policy.yaml` *(optional policy overrides)*
- **BOM** from `calculate`: `outputs/cabling_bom.yaml` (or path provided via CLI)

### Assumed BOM Shape
From `TASK.cabling.calculation.md` — grouped items like:
```yaml
meta:
  policy_path: doctrine/network/cabling-policy.yaml
  spares_fraction: 0.10
  bins:
    sfp28_25g: [1,2,3,5,7,10]
    qsfp28_100g: [1,2,3,5,7,10]
    rj45_cat6a: [1,2,3,5,7,10]
items:
  - class: leaf-node        # one of: leaf-node | leaf-spine | mgmt | wan
    cable_type: sfp28_25g   # or qsfp28_100g | rj45_cat6a
    length_bin_m: 3
    quantity: 16
  - class: leaf-spine
    cable_type: qsfp28_100g
    length_bin_m: 5
    quantity: 8
```
> If `class` is absent in older BOMs, the engine should infer it from `cable_type` (`sfp28_25g→leaf-node`, `qsfp28_100g→leaf-spine`, `rj45_cat6a→mgmt/wan` using counts).

---

## Output
- **Report YAML** (default `outputs/cabling_reconciliation.yaml`) with:
```yaml
summary:
  missing: 0
  phantom: 0
  mismatched_media: 0
  mismatched_bin: 0
  count_mismatch: 0
findings:
  - severity: FAIL
    code: MISSING_LINK
    message: "rack-2 leaf-node requires 2 × sfp28_25g @ 3 m; BOM provides 0"
    context:
      rack_id: rack-2
      class: leaf-node
      cable_type: sfp28_25g
      length_bin_m: 3
      required: 2
      provided: 0
mapping_stats:
  intent:
    leaf-node:
      sfp28_25g:
        1: 4
        3: 12
  bom:
    leaf-node:
      sfp28_25g:
        3: 16
```
- **CLI** human summary with PASS/WARN/FAIL counts and top discrepancies.
- **Exit codes:** 0 (no FAIL), 1 (any FAIL). `--strict` upgrades WARN→exit 2.

---

## Core Algorithm
1. **Load intent** using loaders from `inferno_core.data.network_loader` (Pydantic v2 models): topology, tors, nodes, site, policy.
2. **Derive expected links** (Intent Graph):
   - **leaf‑node:** For each `node` in a rack, expand `nics` of type `SFP28` (or `policy.defaults.nodes_25g_per_node` if unspecified). Each NIC contributes one link to the rack’s `tor_id`.
   - **leaf‑spine:** For each rack, take `topology.racks[*].uplinks_qsfp28` (or policy default) links from `tor_id` → `spine`.
   - **mgmt:** For each node, derive RJ45 count using `policy.defaults.mgmt_rj45_per_node` (if present). Treat as class `mgmt`.
   - **wan:** From `topology.wan.uplinks_cat6a` (if present) as class `wan`.
3. **Assign media and length bins** to each Intent link:
   - Compute distance:
     - Same rack leaf‑node: use `policy.heuristics.same_rack_leaf_to_node_m` (default 2 m) × `slack_factor`.
     - Leaf‑spine inter‑rack: use Manhattan distance of `site.racks[*].grid` × `policy.heuristics.tile_m` (default 1 m), or fall back to `policy.heuristics.adjacent_rack_leaf_to_spine_m`.
   - Media selection:
     - `sfp28_25g`: if distance ≤ `media_rules.sfp28_25g.dac_max_m`, choose DAC; else choose AOC/fiber; pick nearest **valid** bin ≥ distance.
     - `qsfp28_100g`: same logic with `media_rules.qsfp28_100g`.
     - `rj45_cat6a`: choose nearest bin ≥ distance.
4. **Aggregate intent** into a mapping: `class → cable_type → length_bin_m → count`.
5. **Aggregate BOM** identically (load from YAML). If `class` missing, infer per cable type.
6. **Reconcile:**
   - **MISSING_LINK:** intent count > BOM count for a bucket.
   - **PHANTOM_ITEM:** BOM count > intent count for a bucket.
   - **MISMATCHED_MEDIA:** same class but different `cable_type` choice than intent (e.g., QSFP28 bin chosen but policy expects AOC vs DAC; flag only if policy enforces media).
   - **MISMATCHED_BIN:** same class/type but BOM uses a different bin than intent (treat as WARN if BOM bin ≥ intent bin but within `bin_slop_m` policy; else FAIL).
   - **COUNT_MISMATCH:** same class/type/bin but counts differ (after spares normalization). Consider 
     policy spares in comparison: compare **pre‑spares** if BOM includes spares in `meta`, otherwise compare raw.

---

## Implementation Plan

### New module (engine)
- `packages/inferno-tools/src/inferno_tools/cabling/cross_validate.py`
  - Pure functions; no printing.
  - Pydantic v2 models for `CrossFinding` and `CrossReport` (mirror validation task).

**Function seams:**
```python
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Severity = Literal["FAIL", "WARN", "INFO"]

class CrossFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    severity: Severity
    code: str
    message: str
    context: dict = Field(default_factory=dict)

class CrossReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    summary: dict
    findings: list[CrossFinding]
    mapping_stats: dict

# Entrypoint: load manifests + BOM, run reconciliation, return report

def cross_validate_bom(
    bom_path: Path | str = Path("outputs/cabling_bom.yaml"),
    policy_path: Path | str | None = None,
) -> CrossReport:
    ...
```

### CLI wiring
- Add a subcommand in `inferno-cli` under `tools cabling`:
```
inferno-cli tools cabling cross-validate \
  --bom outputs/cabling_bom.yaml \
  --export outputs/cabling_reconciliation.yaml \
  [--strict]
```
- CLI prints a small table and writes the YAML `CrossReport`. Exit codes: 0/1/2 as defined above.

### Tests
Create `packages/inferno-tools/tests/test_cabling_cross_validation.py` with fixtures in `packages/inferno-tools/tests/fixtures/cabling/`:
1. **happy.yaml** — Intent and BOM match exactly (exit 0, no findings).
2. **missing_leaf_node.yaml** — Remove two SFP28 leaf‑node cables from BOM; expect MISSING_LINK with correct bin.
3. **phantom_leaf_spine.yaml** — Add extra QSFP28 item; expect PHANTOM_ITEM.
4. **bin_mismatch_warn.yaml** — BOM uses next‑higher bin; within `bin_slop_m` ⇒ WARN.
5. **bin_mismatch_fail.yaml** — BOM uses lower bin than intent ⇒ FAIL.
6. **media_mismatch.yaml** — Policy requires AOC but BOM uses DAC ⇒ FAIL.
7. **strict_mode.yaml** — Only WARNs; `--strict` returns exit 2.

### Acceptance Criteria
- `cross_validate_bom` returns a `CrossReport` with correct summary counts and detailed findings for each test fixture.
- CLI subcommand writes YAML, prints human summary, and exits with proper code.
- Works when `site.yaml` is absent (skips distance/bin checks with INFO).
- Handles BOMs without `class` by inference; warns if ambiguous (RJ45 case: mgmt vs WAN — include counts in context).

---

## Notes & Gotchas
- Keep numeric coercion strict (Pydantic validators).  
- Align binning logic with calculation engine helpers to avoid double‑math drift. If needed, import a shared helper `select_length_bin(distance_m, bins)` from `inferno_tools.cabling.common`.
- When comparing counts, take **spares** into account; prefer comparing **pre‑spares** numbers reconstructed from policy and BOM `meta.spares_fraction`.
- All engines must be pure; only CLI touches stdout/stderr.