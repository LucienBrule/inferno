

# TASK: Cabling — Definition of Done (DoD) Check

**Epic:** `EPIC.Cabling.Engine`  
**Owner:** Junie  
**Status:** Open  
**Goal:** Provide a single, unambiguous checklist to declare the cabling epic “Done”.

---

## ✅ Scope (what’s being verified)

This DoD confirms that the cabling tooling is **shippable** across:
- CLI surfaces (estimate / calculate / validate / cross-validate / roundtrip / visualize stub)
- Deterministic BOM generation from manifests
- Policy- & topology-aware validation
- Cross-validation (BOM ↔ Topology/Policy)
- Audit automation and tests
- Minimal documentation for operators and contributors

Out of scope: physical install how‑tos, vendor‑specific switch configs (covered elsewhere).

---

## 📂 Inputs (must exist and parse)

- `doctrine/network/cabling-policy.yaml`
- `doctrine/network/topology.yaml`
- `doctrine/network/tors.yaml`
- `doctrine/naming/nodes.yaml`
- `doctrine/site.yaml` (rack grid & geometry; optional for estimate)
- `doctrine/power/rack-power-budget.yaml` (not required by cabling but must remain valid)
- Python packages:
  - `packages/inferno-cli`
  - `packages/inferno-tools`
  - `packages/inferno-core`

**Parsers:** All above must load via project loaders without exceptions.

---

## 🧪 Test & Audit Commands (must pass)

Run from repo root:

```bash
# 0) Environment sanity
uv --version
uv run python -V

# 1) Unit tests (project-wide)
uv run pytest -q

# 2) CLI help must show all subcommands
uv run inferno-cli tools cabling --help

# 3) Heuristic estimate
uv run inferno-cli tools cabling estimate --policy doctrine/network/cabling-policy.yaml

# 4) Calculate BOM (deterministic from manifests)
uv run inferno-cli tools cabling calculate --export outputs/cabling_bom.yaml --format yaml

# 5) Validate (non-strict & strict exit-code contracts)
uv run inferno-cli tools cabling validate --export outputs/cabling_findings.yaml
uv run inferno-cli tools cabling validate --strict --export outputs/cabling_findings_strict.yaml

# 6) Cross-validate BOM against topology/policy
uv run inferno-cli tools cabling cross-validate --bom outputs/cabling_bom.yaml --export outputs/cabling_reconcile.yaml

# 7) Roundtrip check (idempotence-ish)
uv run inferno-cli tools cabling roundtrip --bom outputs/cabling_bom.yaml --export outputs/cabling_roundtrip.yaml

# 8) Full scripted audit
bash .junie/scripts/epic-audit-2.sh
```

---

## 🔔 Exit‑Code Contract (enforced)

- `estimate`, `calculate`, `cross-validate`, `roundtrip`: **exit 0** on success; non‑zero on unhandled error.
- `validate`:
  - **0** → no WARN/FAIL findings
  - **2** → WARNs only (acceptable in non‑strict workflows)
  - **1** → any FAIL present
- `.junie/scripts/epic-audit-2.sh`: **exit 0** and end with `OK: Audit complete`.

---

## 📄 Expected Artifacts (must be written)

- `outputs/cabling_bom.yaml` — has keys `bom`, `metadata`, optional `warnings`.
- `outputs/cabling_findings.yaml` & `outputs/cabling_findings_strict.yaml` — structured list of findings with `code`, `severity`, `message`, `context`.
- `outputs/cabling_reconcile.yaml` — cross‑validation report with zero mismatches.
- `outputs/cabling_roundtrip.yaml` — roundtrip summary; `findings: []` for green path.
- `outputs/_audit_*.{txt,yaml}` — from audit script.

All files must be git‑diffable and deterministic across two consecutive runs with unchanged inputs.

---

## 📊 Acceptance Criteria (must be TRUE)

1. **Unit tests:** `uv run pytest -q` → *all tests pass*.  
2. **CLI surface:** `inferno-cli tools cabling --help` lists:  
   `estimate`, `calculate`, `validate`, `cross-validate`, `roundtrip`, `visualize`.  
   - `visualize` may be a **stub**, but must run and exit 0 with a clear TODO message.
3. **Heuristic estimate:** Produces non‑empty counts, shows policy path and bins, **no tracebacks**.
4. **Calculate:** Writes a valid BOM. `metadata.generated_by` is set and includes `spares_fraction` & `slack_factor`.
5. **Validate (non‑strict):** Prints summary table and exports findings; **exit 0** on clean run.
6. **Validate (strict):**  
   - **exit 0** on clean run,  
   - **exit 2** with WARN‑only,  
   - **exit 1** if any FAIL.  
   Strict result must **not** be 1 at DoD time.
7. **Cross‑validate:** Zero mismatches; **exit 0**.
8. **Roundtrip:** No findings; **exit 0**.
9. **Audit script:** Ends with `OK: Audit complete` and **no WARN lines** in output.  
   If WARNs are policy‑intended, they must be **muted via fixtures** or **converted to INFO** before DoD.
10. **Docs:**  
    - `packages/inferno-cli/README.md` has updated cabling examples.  
    - `doctrine/network/cabling-policy.yaml` contains field‑level comments.  
    - `doctrine/network/README.md` (or `docs/cabling.md`) explains data flow: topology → calculate → validate → cross‑validate → roundtrip.
11. **Determinism:** Two consecutive `calculate` runs produce identical `outputs/cabling_bom.yaml` (no clock/random influences).

---

## 🧭 Reviewer Checklist (PR must show)

- [ ] All acceptance criteria satisfied (link CI logs / script output).
- [ ] Example outputs attached (`outputs/` files) or pasted for quick review.
- [ ] No stray `print()`/debug logs in library code.
- [ ] CLI messages concise and actionable; no stack traces on expected bad input.
- [ ] Tests added/updated for: policy validation, oversubscription, dual‑homing, cross‑validation, roundtrip.

---

## 🚧 Guardrails & Constraints

- **No business logic in CLI handlers.** All logic lives in `inferno_tools` / `inferno_core`.
- **Pydantic v2** only. Model coercions must be explicit; fail closed on bad data.
- **YAML I/O** via shared loader utilities; never re‑implement ad‑hoc loaders.
- **Pure functions** for engines; no hidden state. Deterministic outputs given the same inputs.
- **Human‑safe failures:** return structured findings instead of raising for expected user errors.
- **Performance target:** `calculate + validate` completes in **< 500ms** on modest dev hardware.

---

## 📝 Notes / Known Issues Policy

At DoD time, there must be **no FAIL** findings on the canonical manifests.  
If a legitimate blocker remains (e.g., schema migration in progress), it must be:
- documented inline in the findings,  
- justified in the PR description, and  
- accompanied by a follow‑up task in `.junie/tasks/open/` with owner & ETA.