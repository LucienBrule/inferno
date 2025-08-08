# TASK.cabling.geometry-stress — Media Selection & Boundary Tests

**Owner:** Junie  
**State:** Ready  
**Area:** Networking / Cabling QA  
**Packages:** `inferno-core`, `inferno-tools`, `inferno-cli`

---

## Purpose
Stress‑test all geometry‑driven decisions so that **distance → media (DAC vs AOC/fiber) → length bin** behaves deterministically across racks and policies. Verify boundary math, fallbacks when `site.yaml` is missing, and consistency between **calculate** and **validate** paths.

This task complements `TASK.cabling.calculation` and `TASK.cabling.validation` by focusing purely on geometry effects.

---

## Inputs
- `doctrine/site.yaml` — rack grid, optional `tor_position_u`, cooling zones (informative).
- `doctrine/network/topology.yaml` — rack→spine uplink counts.
- `doctrine/network/tors.yaml` — ToR/spine inventory per rack (IDs must match site racks).
- `doctrine/naming/nodes.yaml` — nodes per rack; NIC types per node (if absent, policy defaults apply).
- `doctrine/network/cabling-policy.yaml` — **required** for bins and thresholds; if absent, engine defaults apply with WARN.

---

## Geometry Model (expected behavior)
- **Grid:** `site.racks[*].grid: [x, y]` are integer tiles; origin `(0,0)` is front‑left.  
  Convert tiles → meters via `policy.heuristics.tile_m` (default `1.0`).
- **Distance metric:** **Manhattan** (`|Δx| + |Δy|`) × `tile_m`.  
  Reason: cabling follows trays/90° paths.
- **Slack:** multiply physical distance by `policy.heuristics.slack_factor` (default `1.2`, must be `≥ 1.0`).
- **Leaf→Node (same rack):** use `policy.heuristics.same_rack_leaf_to_node_m` (default `2.0 m`) × `slack_factor`.  
  *Optional extension:* if `tor_position_u` and node RU exist later, add vertical term `ΔU × U_PITCH_M` (with `U_PITCH_M = 0.04445 m`). For now, treat as constant per policy. Vertical RU distance is explicitly out of scope for this task and reserved for a future extension.
- **Leaf→Spine (inter‑rack):** manhattan distance between racks × `tile_m` × `slack_factor`.  
  If `site.yaml` missing, fall back to `adjacent_rack_leaf_to_spine_m` / `non_adjacent_rack_leaf_to_spine_m` heuristics.

---

## Media & Binning Rules (expected behavior)
- **SFP28 25G** (leaf→node):
  - If `distance_m ≤ policy.media_rules.sfp28_25g.dac_max_m` ⇒ **DAC**; else ⇒ **AOC/fiber**.
  - Choose the **smallest** `bins_m` value `≥ distance_m`. If none, **FAIL** length feasibility.
- **QSFP28 100G** (leaf→spine): same rule using `policy.media_rules.qsfp28_100g.dac_max_m`.
- **RJ45 Cat6A** (mgmt/WAN): choose smallest bin `≥ distance_m`. If `bin > 100 m`, allow with **WARN** (speed may downshift).

---

## Checks to Cover (as tests)
1. **Boundary equality** — `distance_m == dac_max_m` should still select **DAC** and pick a bin ≥ distance (not the next lower).  
   *Finding codes to expect:* none; normal PASS.
2. **Just over threshold** — `distance_m = dac_max_m + ε` must select **AOC/fiber** and pick appropriate bin.  
   If policy has no AOC/fiber bins, **FAIL** `LENGTH_EXCEEDS_DAC_NO_AOC_BINS`.
3. **Far racks** — inter‑rack distances large enough to require higher bins; if `distance_m > max(bins_m)` ⇒ **FAIL** `LENGTH_EXCEEDS_MAX_BIN` with context.
4. **Missing site geometry** — no `site.yaml`:  
   - **INFO** `SITE_GEOMETRY_MISSING` and fallback to heuristic distances; calculation still succeeds.  
   - Validation should not emit media/length findings in this path **unless** a distance is explicitly declared elsewhere.
5. **Slack factor sensitivity** — vary `slack_factor` (`1.0`, `1.5`) and confirm bin changes accordingly; ensure `slack_factor < 1.0` triggers **FAIL** in policy sanity (covered by policy‑edgecases).
6. **Tile size sensitivity** — change `tile_m` (e.g., `0.5`, `2.0`) and confirm bin changes.
7. **RJ45 upper bins** — allow bins above 100 m but emit **WARN** `RJ45_BIN_GT_100M` when used.
8. **Consistency** — outputs from **calculate** and media decisions observed by **validate** must match for the same fixture.

---

## Engine Helpers (shared utilities)
Create or extend common helpers to centralize geometry logic. Place in `packages/inferno-tools/src/inferno_tools/cabling/common.py`:

```python
from typing import Sequence

U_PITCH_M = 0.04445  # 1.75 in per U

def compute_rack_distance_m(grid_a: tuple[int, int], grid_b: tuple[int, int], tile_m: float) -> float:
    dx = abs(grid_a[0] - grid_b[0])
    dy = abs(grid_a[1] - grid_b[1])
    return (dx + dy) * tile_m

def apply_slack(distance_m: float, slack_factor: float) -> float:
    return distance_m * slack_factor

def select_length_bin(distance_m: float, bins_m: Sequence[int]) -> int | None:
    for b in sorted(bins_m):
        if distance_m <= b:
            return b
    return None
```

Re‑use these from both **calculation** and **validation** to avoid drift.

---

## Implementation
- **Where:**
  - Geometry code paths in `inferno_tools.cabling.calculate` and `inferno_core.validation.cabling` should call the shared helpers above.
  - Add handling for **INFO** `SITE_GEOMETRY_MISSING` in validation when `site.yaml` is absent.
- **Finding codes** (used by validation):
  - `LENGTH_EXCEEDS_MAX_BIN` (FAIL) — distance exceeds largest bin for chosen media.
  - `LENGTH_EXCEEDS_DAC_NO_AOC_BINS` (FAIL) — needs AOC/fiber but no bins configured.
  - `SITE_GEOMETRY_MISSING` (INFO) — geometry‑based checks skipped.
  - `RJ45_BIN_GT_100M` (WARN) — RJ45 bin selected > 100 m.  
  All codes must exactly match existing validation enums; no variants or alternate spellings should be introduced.

---

## CLI
No new command. Covered by existing:
- `inferno-cli tools cabling calculate`
- `inferno-cli tools cabling validate [--strict]`

Optional (later): `--explain-geometry` flag to print distances and chosen bins per link for debugging.

---

## Tests (pytest)
Create fixtures in `packages/inferno-tools/tests/fixtures/cabling/geometry/` and tests:
- `test_geometry_calculation.py` (calculation side)
- `test_geometry_validation.py` (validation side)

**Fixtures:**
1. `boundary_equal/` — site with racks at distance resolving to exactly `dac_max_m`; expect **DAC**; bin equals threshold or next ≥.
2. `just_over_threshold/` — slightly greater than `dac_max_m`; expect **AOC** and valid bin; FAIL if AOC bins missing.
3. `far_racks/` — racks far apart such that computed distance > max bin; expect **FAIL** `LENGTH_EXCEEDS_MAX_BIN`.
4. `no_site/` — omit `site.yaml`; expect **INFO** and successful calculation using heuristics.
5. `slack_variants/` — same geometry with `slack_factor` = `1.0` vs `1.5`; bins should differ deterministically.
6. `tile_variants/` — same geometry with `tile_m` variation; bins should differ deterministically.
7. `rj45_long/` — WAN or mgmt using RJ45 bins > 100 m; **WARN** `RJ45_BIN_GT_100M`.

Test rack coordinates should be kept simple (e.g., `(0,0)` to `(3,1)`) for easy manual verification of Manhattan distance math.

Each test should assert chosen media, selected bin, and the presence/absence of the above finding codes in the validation report.

---

## Acceptance Criteria
- Calculation and validation both use shared geometry helpers and produce consistent outcomes.
- Boundary behavior around `dac_max_m` is correct (equality → DAC; epsilon over → AOC).
- Missing `site.yaml` does not crash; emits **INFO** and falls back to heuristics.
- Tests cover all seven fixture families and pass.
- Findings use the exact codes listed above with actionable messages and `context` including `distance_m`, `bin`, `rack_id(s)`, and `media_class`.

---