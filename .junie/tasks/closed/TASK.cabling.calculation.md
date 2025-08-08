## TASK: Cabling Calculation Engine

### Purpose
Implement a **deterministic cabling calculation engine** that consumes site, rack, node, and network topology manifests to produce a **Bill of Materials (BOM)** for all structured cabling in the Inferno site.

### Intent
This task builds on `TASK.cabling.loader.md` and follows the EPIC `EPIC.cabling.implement-cabling-calculation.md`. It will implement:

1. **Data ingestion** from the canonical doctrine manifests.
2. **Calculation logic** to determine exact cable types, counts, and length bins.
3. **Application of cabling policies** for length bins, spares, and connector types.
4. **Output generation** in YAML and CSV formats, grouped by cable type.

---

### Required Inputs
- `doctrine/network/topology.yaml` — Logical network topology (nodes, ports, uplinks).
- `doctrine/network/tors.yaml` — ToR switch definitions and port capacities.
- `doctrine/naming/nodes.yaml` — Node inventory with NIC details.
- `doctrine/site.yaml` — Site geometry and rack layout.
- `doctrine/network/cabling-policy.yaml` *(optional override)* — Policy for length binning, spares, and connector mappings.

### Outputs
- **BOM YAML**: `outputs/cabling_bom.yaml`
- **BOM CSV**: `outputs/cabling_bom.csv`
- Grouped by `cable_type` → `length_bin` → `quantity`.
- Includes **metadata**: spares %, length bin rules applied, and any validation warnings.

---

### Implementation Steps
1. **Loader Integration**
    - Import loader functions from `inferno_core.data.network_loader` for topology, tors, nodes, and site.
    - Load `cabling-policy.yaml` if present, else use built-in defaults.

2. **Graph Construction**
    - Create an in-memory representation linking:
        - Nodes → Rack → ToR
        - ToR → Spine
        - Spine → WAN handoff
    - Include cable type for each link (SFP28 25G, QSFP28 100G, RJ45 Cat6A, etc.).

3. **Distance Calculation**
    - Use Manhattan distance from `site.yaml` rack grid + default tile-to-feet conversion.
    - Apply cable length bin rules from `cabling-policy.yaml`.

4. **Quantity Aggregation**
    - Aggregate counts by `(cable_type, length_bin)`.
    - Apply `spares_fraction` from policy (round up to nearest integer).

5. **Validation**
    - Ensure port capacities are not exceeded.
    - Check that all links have a defined cable type.
    - Warn if link distance exceeds max supported length for the cable type.

6. **Export Functions**
    - `export_bom_yaml(data, path)`
    - `export_bom_csv(data, path)`
    - Write BOM with metadata and grouped line items.

---

### CLI Integration
Add to `inferno-cli tools cabling` group:

```bash
inferno-cli tools cabling calculate --export outputs/cabling_bom.yaml --format yaml
```

**Flags:**
- `--export PATH` (required)
- `--format [yaml|csv]` (default: yaml)
- `--policy PATH` (optional)
- `--spares FLOAT` (optional override of policy default)

---

### Acceptance Criteria
- Can run `calculate` with current doctrine manifests and produce a BOM.
- BOM output matches expected counts from a known topology.
- Validation warnings are emitted for missing NIC info or oversubscribed ports.
- Supports both YAML and CSV output formats.