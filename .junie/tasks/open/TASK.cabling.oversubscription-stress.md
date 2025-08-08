

# TASK.cabling.oversubscription-stress — Edge/Uplink Ratio Scenarios

**Owner:** Junie  
**State:** Ready  
**Area:** Networking / Cabling QA  
**Packages:** `inferno-core`, `inferno-tools`, `inferno-cli`

---

## Purpose
This task MUST exhaustively test and strictly enforce **leaf‑edge to spine‑uplink oversubscription** rules. The implementation MUST ensure:
- Ratio calculations are correct for all racks.
- Policy thresholds are honored exactly as specified.
- All corner cases are handled, including zero uplinks and mixed NIC speeds.
- Actionable guidance is surfaced **before** hardware ordering.

This task complements `TASK.cabling.validation.md` and MUST align with the calculation engine’s bandwidth model. All requirements below are MANDATORY unless explicitly labeled as OPTIONAL.

---

## Inputs
The following inputs MUST be provided:
- `doctrine/network/topology.yaml`: Contains per‑rack uplink counts and (optionally) uplink media types.
- `doctrine/network/tors.yaml`: Specifies ToR and spine port capacities.
- `doctrine/naming/nodes.yaml`: Lists nodes per rack and their NIC types/counts. If NICs are not declared, the implementation MUST fall back to policy defaults.
- `doctrine/network/cabling-policy.yaml`: Contains oversubscription thresholds and default line‑rates.

No geometry data is required; oversubscription calculations MUST use link capacities, not physical distances.

---

## Policy Keys (MUST/OPTIONAL)
The following policy keys MUST be present in `cabling-policy.yaml` (extend with defaults if missing):
```yaml
oversubscription:
  max_leaf_to_spine_ratio: 4.0   # float > 0 (e.g., allow up to 4:1)
  warn_margin_fraction: 0.25     # fraction over max that emits WARN before FAIL
line_rates:
  # Default line‑rates in Gbps, used if NIC/uplink types lack explicit rates
  SFP28: 25
  SFP+: 10
  QSFP28: 100
  RJ45_MGMT: 1
defaults:
  nodes_25g_per_node: 1          # used if node NICs not declared
  tor_uplink_qsfp28_per_tor: 2
```
**Line‑rate map is OPTIONAL**; if omitted, the implementation MUST use built‑in defaults and emit INFO/WARN when guessing line rates.

---

## Definitions (MUST)
- **Edge bandwidth (per rack):** MUST be computed as the sum of all **data‑plane** NICs on nodes in that rack (MUST exclude management RJ45), using the line‑rates (e.g., SFP28=25 Gb/s, SFP+=10 Gb/s). If a node declares an explicit NIC speed, the implementation MUST use that speed.
- **Uplink bandwidth (per rack):** MUST be computed as the number of QSFP28 (or equivalent) uplinks × 100 Gb/s by default. If topology declares other uplink media/speeds, the implementation MUST use the policy `line_rates` mapping.
- **Oversubscription ratio (per rack):** MUST be calculated as `edge_bw_gbps / uplink_bw_gbps`.  
  If `uplink_bw_gbps == 0` and `edge_bw_gbps > 0`, the result MUST be a **FAIL** (no path to spine).
- **Fabric ratio (site‑wide):** MUST be calculated as Σ(edge_bw) / Σ(uplink_bw) across all racks.

---

## Checks (MUST/SHOULD)

### A) Per‑Rack Ratio (**MUST implement WARN/FAIL logic**)
- The implementation MUST compute the oversubscription ratio for each rack and compare it to `max_leaf_to_spine_ratio`.
- If `ratio <= max_leaf_to_spine_ratio`, the result MUST be **PASS**.
- If `max_leaf_to_spine_ratio < ratio <= max_leaf_to_spine_ratio × (1 + warn_margin_fraction)`, the result MUST be **WARN** with code `OVERSUB_RATIO`.
- If `ratio > max_leaf_to_spine_ratio × (1 + warn_margin_fraction)`, the result MUST be **FAIL** with code `OVERSUB_RATIO`.
- If `uplink_bw_gbps == 0` and `edge_bw_gbps > 0`, the result MUST be **FAIL** with code `OVERSUB_NO_UPLINKS`.

### B) Fabric (Global) Ratio (**MUST implement WARN/FAIL logic**)
- The implementation MUST compute the site‑wide ratio.
- The implementation MUST apply the same thresholds as above.
- The implementation MUST emit finding `OVERSUB_RATIO_SITE` with severity based on threshold.

### C) Unknown/Implied Line‑Rates (**MUST emit INFO/WARN**)
- If a NIC/uplink type lacks a declared speed and the policy has no mapping, the implementation MUST use engine defaults and emit a **WARN** with code `OVERSUB_UNKNOWN_LINE_RATE` and the type string.
- If a policy mapping exists but is inferred, the implementation MUST emit **INFO** instead.

### D) Port Budget Tie‑In (**MUST emit INFO/WARN**)
- If the ratio exceeds max and ToR/spine port budgets (from tors.yaml) are near capacity, the implementation MUST emit **INFO** with code `OVERSUB_PORT_BUDGET_LIMITING`, suggesting where to add capacity.

---

## Findings & Context (MUST)
The implementation MUST emit the following findings with the specified context:
- `OVERSUB_RATIO` (WARN/FAIL): Per‑rack ratio exceeds policy.  
  Context MUST include: `{rack_id, edge_gbps, uplink_gbps, ratio, max_allowed, warn_margin_fraction}`
- `OVERSUB_NO_UPLINKS` (FAIL): Nonzero edge bandwidth with zero uplink.  
  Context MUST include: `{rack_id, edge_gbps}`
- `OVERSUB_RATIO_SITE` (WARN/FAIL): Site‑wide ratio exceeds policy.  
  Context MUST include: `{edge_gbps_total, uplink_gbps_total, ratio, max_allowed, warn_margin_fraction}`
- `OVERSUB_UNKNOWN_LINE_RATE` (INFO/WARN): Used default speed for untyped NIC/uplink.  
  Context MUST include: `{type, assumed_gbps, where: "node|uplink"}`
- `OVERSUB_PORT_BUDGET_LIMITING` (INFO): Adding uplinks is constrained by ToR/spine port counts.  
  Context MUST include: `{rack_id, tor_qsfp28_total, tor_qsfp28_free, spine_qsfp28_total, spine_qsfp28_free}`

---

## Implementation (MUST/SHOULD)
- The implementation MUST reside in `packages/inferno-core/src/inferno_core/validation/cabling.py` inside the function `validate_oversubscription(...)`.
- Line‑rate lookup MUST be centralized in `inferno_tools.cabling.common`, using:
```python
def nic_line_rate_gbps(nic_type: str, policy_rates: dict[str, int] | None) -> int: ...
```
- Calculation engines MUST remain pure; CLI output/printing is handled separately.

---

## CLI (MUST)
The implementation MUST be covered by the following CLI command:
```
inferno-cli tools cabling validate [--strict]
```
The CLI output MUST include totals by rack and site under a clearly labeled **Oversubscription** section in the printed report.

---

## Tests (pytest) (MUST/SHOULD)
The implementation MUST provide fixtures under `packages/inferno-core/tests/fixtures/cabling/oversub/` and tests in `packages/inferno-core/tests/test_cabling_oversub.py`:

The following test scenarios MUST be covered:
1. **happy_1to1/**: Edge equals uplink (ratio 1.0) ⇒ MUST result in PASS, no findings.
2. **warn_slight_over/**: Ratio just above max but within `warn_margin_fraction` ⇒ MUST emit WARN `OVERSUB_RATIO`.
3. **fail_far_over/**: Ratio well above max×(1+margin) ⇒ MUST emit FAIL `OVERSUB_RATIO`.
4. **zero_uplinks/**: Edge>0, uplink=0 ⇒ MUST emit FAIL `OVERSUB_NO_UPLINKS`.
5. **site_ratio_warn/**: One rack slightly over; aggregate ratio over threshold ⇒ MUST emit WARN `OVERSUB_RATIO_SITE`.
6. **unknown_line_rate/**: Introduce a NIC type `FOO25` with no policy map ⇒ MUST emit WARN `OVERSUB_UNKNOWN_LINE_RATE`.
7. **port_budget_limiting/**: Ratio FAIL but ToR/spine ports are already near max; MUST ensure `OVERSUB_PORT_BUDGET_LIMITING` INFO accompanies result.

Each test MUST assert the severity, finding codes, and the numeric context (edge/uplink/ratio) as described above. The CLI smoke test MUST assert exit code `0/1/2` behavior.

---

## Acceptance Criteria (MUST)
The following criteria MUST be met for acceptance:
- Per‑rack and site‑wide ratios are computed deterministically and match the expected values in tests.
- WARN/FAIL thresholding MUST strictly respect `max_leaf_to_spine_ratio` and `warn_margin_fraction`.
- Unknown line‑rates MUST produce the correct advisory findings, and ratios MUST still be computed using reasonable assumptions.
- CLI output MUST display results under an **Oversubscription** heading with rack and site totals; exit codes MUST be correct (`0` for PASS, `1` for WARN, `2` for FAIL).
- All described tests MUST pass; the implementation MUST be ready for CI gating.