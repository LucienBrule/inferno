

# EPIC.cabling.qa-hardening — Cross‑Validation, Stress Cases, and Drift Detection

**Owner:** Junie  
**State:** Open  
**Area:** Networking / Cabling  
**Packages Touched:** `inferno-core`, `inferno-tools`, `inferno-cli`  
**CLI Surfaces:** `inferno-cli tools cabling {estimate|calculate|validate}`

---

## 0) Context / What Exists Already (Snapshot)

This EPIC assumes the following foundation is in place from prior work:

- **Doctrine manifests (YAML)** under `doctrine/`:
  - `network/topology.yaml` (spine/leaf mappings, per‑rack uplinks)
  - `network/tors.yaml` (ToR + spine inventory and port budgets)
  - `network/cabling-policy.yaml` (media bins, DAC/AOC thresholds, spares, site defaults)
  - `naming/nodes.yaml` (physical hosts with optional NIC declarations)
  - `site.yaml` (optional, for rack grid geometry & ToR U positions)
- **Core models & loaders (Pydantic v2)** live in `packages/inferno-core` (see `TASK.cabling.loader`).
- **Cabling calculation engine** implemented in `packages/inferno-tools` and exposed via
  `inferno-cli tools cabling calculate --export <path> --format yaml|csv` (see `TASK.cabling.calculation`).  
  Output: grouped BOM with media/length bins + spares; basic validation notes.
- **Cabling validation**: in progress (Pydantic v2 report models, granular checks with FAIL/WARN/INFO).  
  Exposed via `inferno-cli tools cabling validate [--strict] [--export findings.yaml]`.
- **Heuristic estimator** available at `inferno-cli tools cabling estimate` for quick counts.
- **Test suites** exist per package (`packages/<name>/tests/`) and are growing with new fixtures.

This EPIC’s job is to **harden** the stack: cross‑validate outputs, push edge conditions, and detect drift between manifests, calculation, and validation.

---

## 1) Goals

- Ensure **calculate ↔ validate** agree and cover the entire link space (no phantom or missing links).
- Exercise **policy edge‑cases** (spares, bins, absent rules) without runtime surprises.
- Verify **geometry impacts** media selection (DAC vs AOC/fiber) and boundary math.
- Prove **redundancy and oversubscription** logic under stress.
- Provide **clear CLI signals** (exit codes), and machine‑readable artifacts for future CI.

---

## 2) Non‑Goals
- Live telemetry, SNMP/Redfish ingestion (that’s a later EPIC).
- Rack‑level SVG visualization polish (separate visualization track; here we may stub minimal renders for debugging only).

---

## 3) Deliverables
- A suite of **fixtures** under `packages/inferno-core/tests/fixtures/cabling/` and `packages/inferno-tools/tests/fixtures/cabling/` covering all cases listed below.
- New **unit tests** and **CLI smoke tests** covering PASS/WARN/FAIL paths and `--strict` behavior.
- Optional **round‑trip checker** script in `inferno-tools` for BOM ↔ topology reconciliation.
- Documentation snippets appended to `guidelines.md` (how to run QA suite).

---

## 4) Tasks

### TASK.cabling.cross-validation
**Purpose:** Prove `calculate` and `validate` are consistent; detect drift.  
**Work:**
- Run both on the same fixture; ensure every cable line item in BOM maps to a corresponding implied link in topology and vice‑versa.
- Detect **phantom** items (in BOM but not in topology) and **missing** items (in topology but absent in BOM).  
**Output:** A small reconciliation report (YAML) listing `missing`, `phantom`, `mismatched_media`.
**Acceptance:** Tests that intentionally introduce drift cause the report to show non‑empty sets and `validate` to FAIL.

### TASK.cabling.policy-edgecases
**Purpose:** Stress policy parsing & application.  
**Work:**
- Spares: test `0.0`, `0.25`, `1.0`, and `>1.0` (expect FAIL for >1.0).  
- Bins: unsorted bins, duplicated bins, and empty bins per media type.  
- Missing media_rules for a type; ensure defaults or explicit errors.
**Acceptance:** Policy sanity checker emits specific codes; calculation respects corrected bins; tests capture each condition.

### TASK.cabling.geometry-stress
**Purpose:** Ensure distance → media selection works and boundaries are correct.  
**Work:**
- `site.yaml` with distant racks requiring AOC/fiber for QSFP28.
- Boundary case where distance equals `dac_max_m` (should still fit in DAC bin).  
- Missing `site.yaml` path → INFO note; calculation falls back to heuristic lengths.
**Acceptance:** Tests assert correct media decisions and boundary behavior; no crashes without site geometry.

### TASK.cabling.redundancy-stress
**Purpose:** Enforce redundancy rules.  
**Work:**
- `redundancy.node_dual_homing: true` with odd NIC counts → FAIL.
- `redundancy.tor_uplinks_min` set above current uplinks → FAIL.
- Exception list honored (nodes allowed to be single‑homed).
**Acceptance:** Validation emits exact codes, messages reference node/rack IDs.

### TASK.cabling.oversubscription-stress
**Purpose:** Verify ratio math and thresholds.  
**Work:**
- Cases just under, slightly over, and far over the threshold.  
- Zero‑uplink with non‑zero edge bandwidth → FAIL.  
- Large uplink surplus → PASS.  
**Acceptance:** WARN vs FAIL split matches policy; messages include computed Gbps and ratio.

### TASK.cabling.cli-smoketests
**Purpose:** Guardrail CLI ergonomics & exit codes.  
**Work:**
- Run `calculate` and `validate` on happy fixture (exit `0`).  
- Run a WARN‑only fixture: default exit `0`, with `--strict` exit `2`.  
- Run a FAIL fixture: exit `1`.  
**Acceptance:** Pytests assert captured exit codes and key lines in output.

### TASK.cabling.roundtrip-bom
**Purpose:** Sanity‑check terminations from BOM back to intent.  
**Work:**
- Post‑process BOM to count terminations; must match `Σ node NICs + (Σ uplinks × 2)` (account for both ends) minus any policy‑defined exceptions (e.g., pre‑patched harnesses).  
**Acceptance:** Round‑trip checker yields `PASS` for clean fixtures and detects mismatches in corrupt ones.

### TASK.cabling.intentional-corruption
**Purpose:** Ensure the validator fails loudly and precisely for broken manifests.  
**Work:**
- Topology references unknown `tor_id`.
- `nodes.yaml` references unknown `rack_id`.
- Duplicate rack IDs in `site.yaml` or `topology.yaml`.
- Non‑numeric counts in critical fields.  
**Acceptance:** Specific FAIL codes per case; messages include file hints and offending keys.

### TASK.cabling.definition-of-done-check
**Purpose:** Verify the EPIC meets its definition of done.
**Work:** Run the full QA suite, capture CLI outputs for each major command with all fixture types (happy/WARN/FAIL), confirm exit codes, and ensure documentation is updated.
**Acceptance:** All tasks in EPIC are closed, all tests pass, and CLI demonstration runs match expected outputs and codes.

---

## 5) Implementation Notes
- Use **Pydantic v2** models for findings (`FAIL|WARN|INFO`) and the validation report.  
- Keep engines pure; the CLI prints.  
- Fixture YAMLs should be compact and live under `packages/*/tests/fixtures/cabling/` with clear names (e.g., `happy.yaml`, `oversub_warn.yaml`, `spine_deficit.yaml`).
- Prefer **deterministic** calculations (no randomness); mark `random.seed` if any randomized layout enters tests.

---

## 6) Reporting & Exit Codes
- Default rules:
  - Exit `0` if **no FAIL** (WARN allowed).  
  - Exit `1` if **any FAIL**.  
  - Exit `2` if `--strict` and there are WARNs (even without FAILs).
- Machine output: YAML/JSON for both validation findings and reconciliation report.

---

## 7) Milestones & Closure
- **M1:** Geometry & policy edge‑cases covered (TASKs: policy‑edgecases, geometry‑stress).  
- **M2:** Cross‑validation and round‑trip BOM checks in place (TASKs: cross‑validation, roundtrip‑bom).  
- **M3:** Oversubscription & redundancy stress complete; CLI smoke tests passing (TASKs: oversubscription‑stress, redundancy‑stress, cli‑smoketests).  
- **Close:** All tasks closed with tests; add a short section to `guidelines.md` (“Running the cabling QA suite”).

---

## 8) How Junie Works in This Repo
- Your workspace is under `.junie/`:
  - Epics: `.junie/epics/open/` (this file) → move to `.junie/epics/closed/` when finished.
  - Tasks: `.junie/tasks/open/` → `.junie/tasks/closed/` upon completion.
- Each task should link to **exact files** touched and include before/after CLI snippets.
- Keep tests close to code under each package.
- If doctrine schemas evolve, update **models, loaders, and tests** in the same PR/patch.

---

## 9) References
- `guidelines.md` — engineering conventions (Pydantic v2, package layering, uv usage).  
- `TASK.cabling.loader.md` — loader contract (Pydantic v2).  
- `TASK.cabling.calculation.md` — calculation engine contract.  
- `TASK.cabling.validation.md` — validation report contract.


## 10) Definition of Done

This EPIC is considered complete only when:
- All tasks listed above are closed.
- All acceptance criteria for each task are met.
- All tests pass (unit, integration, and CLI smoke tests).
- Documentation (including `guidelines.md` and any referenced snippets) is updated to reflect new workflows and findings.
- The QA suite can be run end-to-end without errors.
- A CLI demonstration run is performed and captured, showing:
  - `calculate`, `validate`, `cross-validate`, and roundtrip checks.
  - Relevant smoke tests on happy-path, WARN, and FAIL fixtures.
  - Correct exit codes for each run (0 for PASS, 2 for WARN with `--strict`, 1 for FAIL).
