# TASK.cabling.redundancy-stress — Dual‑Homing & Uplink Resilience

**Owner:** Junie  
**State:** Ready  
**Area:** Networking / Cabling QA  
**Packages:** `inferno-core`, `inferno-tools`, `inferno-cli`

---

## Purpose
Exercise and enforce **redundancy guarantees** in the cabling design: node dual‑homing to leafs (ToRs), rack uplink minima to spine, and optional LAG/LACP & mgmt redundancy. These checks **must** be run **before** BOM generation and **cannot** be bypassed except via explicit policy exception keys.

This task complements `TASK.cabling.validation.md` and is a focused set of checks + fixtures that probe redundancy edge cases.

---

## Inputs
- `doctrine/network/topology.yaml` — per‑rack ToR ID, uplink counts.
- `doctrine/network/tors.yaml` — ToR inventory per rack; spine capacity.
- `doctrine/naming/nodes.yaml` — nodes per rack (and NIC declarations if present). Missing NIC declarations here trigger defaults from policy.
- `doctrine/network/cabling-policy.yaml` — redundancy knobs and defaults (see below).
- `doctrine/site.yaml` — optional; used only for context in messages.

---

## Policy Keys (expected / optional)
From `cabling-policy.yaml` (required keys cause FAIL if missing):
```yaml
redundancy:
  node_dual_homing: true        # [required] require nodes to have ≥2 edge links for survival
  tor_uplinks_min: 2            # [required] minimum QSFP28 uplinks per rack ToR → spine
  single_tor_ok: false          # [optional] if true, allow a single ToR even when dual_homing is on (WARN instead of FAIL)
  mgmt_dual: false              # [optional] if true, require ≥2 RJ45 mgmt per node (or documented IPMI/virtual OOB)
lag:
  require_lacp: false           # [optional] informational; if true, uplinks should be in LAGs
  min_members_qsfp28: 2         # [optional] if set, each LAG group per rack must have this minimum member count
oversubscription:
  max_leaf_to_spine_ratio: 4.0  # [optional] used by a separate task; referenced for context only
```
> All keys are validated by policy sanity checks (see `TASK.cabling.policy-edgecases.md`).

---

## Definitions
- **Dual‑homed node:** has **≥2 active, intended-for-edge NICs** (typically SFP28 25G) as per manifests, intended to terminate on **two independent ToRs** in the rack. When explicit NIC→ToR mapping is available, it overrides count heuristics. If explicit mapping is unavailable, NIC count ≥2 is the minimum criterion and a **WARN** is emitted if only one ToR exists in the rack.
- **Rack uplink minimum:** number of QSFP28 (or equivalent) uplinks from ToR(s) to spine **per rack**.
- **LAG group:** set of physical uplinks aggregated (LACP). We only validate divisibility and minimum members per LAG group per rack when declared in policy/topology.

---

## Checks (with expected behavior)

### A) Node Dual‑Homing (**FAIL/WARN**)
- If `redundancy.node_dual_homing: true`:
  1. For each node in a rack, compute **active, intended-for-edge NIC count** (SFP28 25G) from node spec; if absent, use `defaults.nodes_25g_per_node`.
  2. **FAIL** `REDUNDANCY_NODE_SINGLE_HOMED` if count `< 2`.
  3. If count is **odd** (3, 5, …), **WARN** `REDUNDANCY_NODE_ODD_NIC_COUNT` (can hinder symmetric distribution).
  4. If the rack has **only one ToR** and dual_homing is **true**:
     - If `single_tor_ok: false` ⇒ **FAIL** `REDUNDANCY_TOR_PAIR_MISSING`.
     - Else ⇒ **WARN** `REDUNDANCY_TOR_PAIR_MISSING_ALLOWED`.
  5. If manifests later include explicit per‑NIC → leaf mapping and both NICs terminate on the **same ToR**, **FAIL** `REDUNDANCY_NODE_NOT_SPLIT_ACROSS_TORS`.
  6. If an exception list exists (e.g., `redundancy.exceptions.node_single_homed_ids`), those nodes become **INFO** with code `REDUNDANCY_EXCEPTION_NODE`.

### B) Rack Uplink Minimum to Spine (**FAIL**)
- For each rack, compute required uplinks (from `topology.racks[*].uplinks_qsfp28` or policy default `tor_uplink_qsfp28_per_tor`).
- If required `< redundancy.tor_uplinks_min` ⇒ **FAIL** `REDUNDANCY_RACK_UPLINKS_MIN` with deficit in context.

### C) LAG/LACP Conformance (**WARN/FAIL**)
- If `lag.min_members_qsfp28` is set:
  - Verify each LAG group per rack has uplinks count that is a **multiple** of that number. If not ⇒ **FAIL** `REDUNDANCY_LAG_GROUP_SIZE`.
- If `lag.require_lacp: true` but **no LAG metadata** exists in manifests, emit **WARN** `REDUNDANCY_LACP_UNDECLARED` (informational until LAG modeling lands).

### D) Asymmetry Across Racks (**WARN**)
- Compute the **median** and **range** of rack uplink counts.
- If any rack differs from median by **≥2 ports**, **WARN** `REDUNDANCY_ASYMMETRIC_UPLINKS` (context lists counts per rack). This is advisory; may indicate uneven failure domains.

### E) Management Redundancy (**FAIL/WARN**)
- If `redundancy.mgmt_dual: true`:
  - Per node, require **≥2 RJ45 mgmt** ports (from node spec or `defaults.mgmt_rj45_per_node`), or a documented mix of physical RJ45 and IPMI/virtual out-of-band interfaces. If `<2` ⇒ **FAIL** `REDUNDANCY_MGMT_SINGLE_HOMED`.
  - If manifests include a dedicated mgmt switch inventory and it has **insufficient ports**, **WARN** `REDUNDANCY_MGMT_AGG_PORT_DEFICIT`.

---

## Finding Codes & Context
- `REDUNDANCY_NODE_SINGLE_HOMED` (FAIL) — node has <2 edge NICs.  
  Context: `{node_id, rack_id, nic_count, required: 2}`
- `REDUNDANCY_NODE_ODD_NIC_COUNT` (WARN) — odd NIC count.  
  Context: `{node_id, rack_id, nic_count}`
- `REDUNDANCY_TOR_PAIR_MISSING` (FAIL/WARN per policy) — rack has 1 ToR while dual_homing required.  
  Context: `{rack_id, tors_present}`
- `REDUNDANCY_NODE_NOT_SPLIT_ACROSS_TORS` (FAIL) — explicit mapping shows both NICs on same ToR.  
  Context: `{node_id, rack_id, tors_used}`
- `REDUNDANCY_EXCEPTION_NODE` (INFO) — node is whitelisted for single‑homing.  
  Context: `{node_id}`
- `REDUNDANCY_RACK_UPLINKS_MIN` (FAIL) — rack uplinks below threshold.  
  Context: `{rack_id, uplinks, required_min}`
- `REDUNDANCY_LAG_GROUP_SIZE` (FAIL) — uplinks not a multiple of min_members in a LAG group.  
  Context: `{rack_id, uplinks, min_members}`
- `REDUNDANCY_LACP_UNDECLARED` (WARN) — policy requires LACP but manifests lack LAG metadata.  
  Context: `{rack_id}`
- `REDUNDANCY_ASYMMETRIC_UPLINKS` (WARN) — uplink counts vary significantly across racks.  
  Context: `{counts_by_rack}`
- `REDUNDANCY_MGMT_SINGLE_HOMED` (FAIL) — mgmt redundancy required but node has <2 RJ45 or documented OOB.  
  Context: `{node_id, rj45_count, required_min: 2}`
- `REDUNDANCY_MGMT_AGG_PORT_DEFICIT` (WARN) — mgmt aggregation lacks ports.  
  Context: `{required, available}`

---

## Implementation
- **Where:** Implement checks inside `packages/inferno-core/src/inferno_core/validation/cabling.py` within `validate_redundancy(...)` (already referenced in validation task). The function **must not mutate inputs** and must be side-effect free; return `Finding[]`.
- **Helpers:** Reuse NIC counting and port budget helpers from calculation/validation; avoid drift.
- **CLI:** Surfaced via `inferno-cli tools cabling validate [--strict]`. Redundancy findings appear under a **Redundancy** section in the printed report.

---

## Tests (pytest)
Create fixtures under `packages/inferno-core/tests/fixtures/cabling/redundancy/` and tests in `packages/inferno-core/tests/test_cabling_redundancy.py`:

- Fixtures must be minimal and self-contained; no dependency on other fixture sets.

1. **happy_dual_homed/** — nodes have 2× SFP28 each; racks have ≥2 QSFP28 uplinks; two ToRs present or `single_tor_ok: true`.
2. **single_homed_node/** — one node with 1× SFP28 when dual_homing required ⇒ **FAIL** `REDUNDANCY_NODE_SINGLE_HOMED`.
3. **tor_pair_missing/** — dual_homing true but rack has one ToR; policy `single_tor_ok: false` ⇒ **FAIL**; with `true` ⇒ **WARN**.
4. **odd_nic_counts/** — nodes with 3× SFP28 ⇒ **WARN** `REDUNDANCY_NODE_ODD_NIC_COUNT`.
5. **uplinks_below_min/** — rack uplinks < `tor_uplinks_min` ⇒ **FAIL** `REDUNDANCY_RACK_UPLINKS_MIN`.
6. **lag_divisibility/** — `lag.min_members_qsfp28: 2` but odd uplinks in a LAG group ⇒ **FAIL** `REDUNDANCY_LAG_GROUP_SIZE`.
7. **lacp_required_undeclared/** — `lag.require_lacp: true` but no LAG metadata ⇒ **WARN** `REDUNDANCY_LACP_UNDECLARED`.
8. **mgmt_dual_required/** — `mgmt_dual: true` and some nodes have 1 RJ45 ⇒ **FAIL** `REDUNDANCY_MGMT_SINGLE_HOMED`.
9. **asymmetric_uplinks/** — one rack significantly lighter ⇒ **WARN** `REDUNDANCY_ASYMMETRIC_UPLINKS`.
10. **explicit_not_split/** *(optional once mapping exists)* — explicit NIC→ToR mapping places both NICs on same ToR ⇒ **FAIL**.

Each test asserts **finding codes**, message substrings, and severity. Add a CLI smoke test that runs `inferno-cli tools cabling validate` against a FAIL and a WARN fixture to confirm exit codes.

---

## Acceptance Criteria
- All checks emit stable codes with actionable context.
- Behavior toggles correctly with policy flags (`single_tor_ok`, `mgmt_dual`, `lag.*`).
- Test suite passes on all fixtures; CLI smoke tests produce expected exit codes.
- All FAILs must cause non-zero CLI exit code when `--strict` is set.
- Documentation note added to `guidelines.md`: “Redundancy checks run in `validate`; fix FAILs prior to ordering cables.”