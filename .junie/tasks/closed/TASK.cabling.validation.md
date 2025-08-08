# TASK: cabling.validation

## Purpose
Establish a **deterministic validation pass** that verifies manifests, topology, and cabling policy conform to Inferno’s network design rules **before** calculation/installation. Surface precise failures, remediation hints, and machine‑readable output suitable for CI.

## Scope & Non‑Goals
- **In‑scope:** static analysis of manifests vs. policy; capacity math; media/length feasibility checks; redundancy rules; structured findings.
- **Out‑of‑scope:** physical discovery, SNMP polling, or live measurements (covered later by “measured” tooling).

## Inputs (required unless noted)
- `doctrine/network/topology.yaml`
- `doctrine/naming/nodes.yaml`
- `doctrine/network/tors.yaml`
- `doctrine/network/cabling-policy.yaml` *(optional; if missing, use engine defaults)*
- `doctrine/site.yaml` *(optional; enables geometry/length checks)*

## Policy/Tunables referenced
From `cabling-policy.yaml` (examples; use defaults if absent):
- `defaults.nodes_25g_per_node`
- `defaults.mgmt_rj45_per_node`
- `defaults.tor_uplink_qsfp28_per_tor`
- `defaults.spares_fraction`
- `site-defaults.{num_racks,nodes_per_rack,uplinks_per_rack,mgmt_rj45_per_node,wan_cat6a}`
- `media_rules.{sfp28_25g,qsfp28_100g,rj45_cat6a}.{dac_max_m,bins_m}`
- (Optional) `redundancy.{node_dual_homing,tor_uplinks_min}`
- (Optional) `oversubscription.{max_leaf_to_spine_ratio}` (e.g., `4.0` meaning ≤4:1)

## Definitions
- **Leaf→Node edge bandwidth (per rack):** Σ(node NICs × line rate). Default assumes SFP28=25 Gb/s per NIC unless overridden by declared NIC type.
- **Leaf→Spine uplink bandwidth (per rack):** `uplinks_qsfp28 × 100 Gb/s` (adjust if other uplink media appear).
- **Oversubscription ratio (per rack):** `edge_bw_gbps / uplink_bw_gbps`. Undefined if uplink_bw=0 → **FAIL**.

---

## Checks (with logic details)

### 1) Port capacity validation (**FAIL/WARN**)
- **ToR SFP28 (leaf→node):**
  - Compute required SFP28 ports per rack: sum over nodes in rack of declared `nics` of type `SFP28` (or policy default per node if not declared).
  - Compare to `tors[rack_id].ports.sfp28_total`. If required > total → **FAIL** with deficit count.
- **ToR QSFP28 (uplinks):**
  - Required = `topology.racks[*].uplinks_qsfp28` per rack (or `policy.defaults.tor_uplink_qsfp28_per_tor`). Compare to `tors[rack_id].ports.qsfp28_total`. Excess → **FAIL**.
- **Spine QSFP28:**
  - Required = Σ(all rack uplinks). Compare to `spine.ports.qsfp28_total`. Excess → **FAIL**. Within `5%` of capacity → **WARN**.
- **Mgmt RJ45:**
  - If an explicit mgmt switch inventory exists (future), check port budget; else **INFO** noting unvalidated mgmt ports.

### 2) NIC type compatibility (**FAIL/WARN**)
- For each node NIC:
  - `SFP28` must terminate on an SFP28-capable port (ToR leaf). If absent → **FAIL**.
  - `QSFP28` as a node NIC (rare) requires QSFP28 leaf ports or breakouts per policy (if supported). If not supported in policy → **FAIL**.
  - `RJ45` mgmt should terminate to RJ45 aggregation (router/mgmt switch). If no termination is modeled → **WARN** with guidance.

### 3) Oversubscription ratio (**WARN/FAIL per policy)**
- Compute per rack: `edge_bw_gbps / uplink_bw_gbps`.
- If uplink_bw=0 and edge_bw>0 → **FAIL**.
- If ratio > `policy.oversubscription.max_leaf_to_spine_ratio` (default 4.0 if unspecified):
  - If ≤ 25% over: **WARN** with suggested actions (add uplinks, reduce per-node NICs).
  - If > 25% over: **FAIL**.

### 4) Connection completeness (**FAIL**)
- Every `topology.racks[*].tor_id` must exist in `tors.tors[*].id` and share the same `rack_id`.
- Every `nodes[*].rack_id` must exist in either `site.racks[*].id` or `topology.racks[*].rack_id`.
- Spine must exist and have `ports.qsfp28_total` defined. Missing → **FAIL**.

### 5) Cable length feasibility & bin compliance (**WARN/FAIL**)
- If `site.yaml` present:
  - Compute Manhattan distance between ToR location and node location proxy (same rack → use `policy.heuristics.same_rack_leaf_to_node_m`; inter‑rack → use `adjacent_rack_leaf_to_spine_m` or `non_adjacent_rack_leaf_to_spine_m`). Multiply by `slack_factor`.
  - For **leaf→node**: if distance > `media_rules.sfp28_25g.dac_max_m`, mark media requirement as **AOC/fiber**. If **no** AOC/fiber bins exist to satisfy length → **FAIL**.
  - For **leaf→spine**: apply QSFP28 rules similarly.
- If `site.yaml` missing: **INFO** noting geometry‑based checks skipped.

### 6) Redundancy rules (**FAIL/WARN**)
- If `policy.redundancy.node_dual_homing: true`:
  - Require each node to have NIC count divisible by 2 (for dual leafs) or an explicit exception list. Violation → **FAIL**.
- If `policy.redundancy.tor_uplinks_min` present:
  - Ensure each rack uplinks ≥ this value; shortfall → **FAIL**.

### 7) Policy sanity checks (**FAIL**)
- `defaults.spares_fraction` must be `0.0 ≤ x ≤ 1.0`.
- `media_rules.*.bins_m` must be ascending positive ints.

---

## Output Contract

### CLI (human)
- A table per check with **PASS/WARN/FAIL** counts.
- Detailed lines: `SEVERITY CODE rack/node → message (context)`.
- Optional `--strict` to treat **WARN** as exit code **2** (non‑zero) instead of **0**.

### Machine output (JSON/YAML)
Structure:
```yaml
summary:
  pass: 12
  warn: 2
  fail: 1
findings:
  - severity: FAIL
    code: PORT_CAPACITY_TOR_SFP28
    message: "rack-1 requires 52 SFP28 ports, ToR provides 48 (deficit 4)"
    context:
      rack_id: rack-1
      required_sfp28: 52
      available_sfp28: 48
  - severity: WARN
    code: OVERSUB_RATIO
    message: "rack-2 edge 300 Gbps, uplink 200 Gbps → 1.5:1 exceeds policy 1.0:1"
    context:
      rack_id: rack-2
      edge_gbps: 300
      uplink_gbps: 200
      policy_max: 1.0
```

**Exit codes:**
- `0` → no FAIL (WARN allowed)
- `1` → one or more FAIL
- `2` → `--strict` with WARN present

---

## Implementation Notes
- Package: `packages/inferno-core/src/inferno_core/validation/cabling.py`
- Use **Pydantic v2** for findings and report models:
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

class Report(BaseModel):
    model_config = ConfigDict(extra="ignore")
    summary: dict
    findings: list[Finding]
```

- Provide functions:
```python
from inferno_core.data.network_loader import load_nodes, load_tors, load_topology, load_site

def validate_ports(topology, tors, nodes, policy) -> list[Finding]: ...
def validate_compatibility(topology, tors, nodes, policy) -> list[Finding]: ...
def validate_oversubscription(topology, tors, nodes, policy) -> list[Finding]: ...
def validate_lengths(topology, tors, nodes, site, policy) -> list[Finding]: ...
def validate_redundancy(topology, tors, nodes, policy) -> list[Finding]: ...

def run_cabling_validation(policy_path: str | None = None) -> Report:
    """Top-level: load manifests, run checks, return structured Report."""
    ...
```

- CLI wiring (separate task) should catch `Report`, pretty‑print with **rich**, and set exit code per rules.

---

## Tests (pytest)
Create `packages/inferno-core/tests/test_cabling_validation.py` covering:
1. **Happy path:** capacities within limits; ratio under policy; lengths within DAC bins.
2. **Deficit SFP28:** node NIC demand exceeds ToR SFP28 → **FAIL** with deficit context.
3. **Deficit spine QSFP28:** Σuplinks > spine capacity → **FAIL**.
4. **Oversubscription WARN/FAIL:** ratios just over and far over the policy threshold.
5. **Missing tor_id mapping:** topology references unknown ToR → **FAIL**.
6. **Length exceeds DAC:** site present, distance above `dac_max_m` but AOC bins available → **WARN**; if no AOC bins → **FAIL**.
7. **Redundancy rule:** `node_dual_homing: true` but odd NIC counts → **FAIL**.
8. **Policy sanity:** bad `spares_fraction` or unsorted `bins_m` → **FAIL**.
9. **Mgmt RJ45 note:** produces **INFO** in absence of modeled RJ45 aggregation.

---

## Success Criteria
- All checks implemented with precise **Finding.code** values and actionable messages.
- Report model serializes to YAML/JSON; CLI returns correct exit codes with/without `--strict`.
- Unit tests pass; coverage includes happy path and error conditions.
- Ready for CI gating of `doctrine/*` changes.