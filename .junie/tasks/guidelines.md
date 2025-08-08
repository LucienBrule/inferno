
> **VERY IMPORTANT** Junie MUST NOT USE HEREDOC OR python -c "<script>" in the shell. WRITE DEBUG SCRIPTS AND RUN THEM WITH PYTHON. **VERY IMPORTANT**
> 
# Inferno Engineering Guidelines

A living guide to how we build, wire, and document **Inferno**. Ground rules:

- ✅ **Typed, model-driven** code (Pydantic v2) for any external data.
- ✅ **Separation of concerns:** CLI shells only; logic lives in packages.
- ✅ **Workspace-first** Python via `uv` (monorepo of packages).
- ✅ **Doctrine is data, not code.**

---

## 1) Repository Layout & Responsibilities

```
.
├── doctrine/                 # Declarative manifests (YAML) – the "source of truth"
│   ├── naming/               # Logical identifiers (nodes, circles, clusters)
│   ├── network/              # Topology, ToRs, cabling policy, etc.
│   ├── power/                # Power budgets, feeds, UPS/PDU candidates
│   ├── hvac/                 # Cooling options, capacity plans
│   └── site.yaml             # (Optional) rack grid & placement for geometry
├── packages/                 # Executable surface (workspace of Python packages)
│   ├── inferno-cli/          # CLI entrypoints (Click); no business logic
│   ├── inferno-core/         # Data models, schemas, loaders, invariants
│   ├── inferno-tools/        # Engines/calculators (cabling, cooling, rack viz)
│   ├── inferno-graph/        # Rendering & layout (Graphviz/diagrams)
│   └── inferno-planner/      # Planning/what‑if, BOM synthesis, validations
├── EPIC.* / TASK.*.md        # Work planning docs (delivery contracts)
├── README.md / docs/         # User documentation and how‑tos
└── outputs/                  # Generated artifacts (graphs, BOMs, reports)
```

**Doctrine/** is the human‑authored configuration. Treat it like code: review, version, validate. 

**Packages/** are layered (no upward imports):
- `inferno-cli` ➜ may import `inferno-tools`, `inferno-core`, `inferno-graph`. 
- `inferno-tools` ➜ may import `inferno-core` only. 
- `inferno-core` ➜ standalone (no package deps within the monorepo). 
- `inferno-graph` ➜ may import `inferno-core`. 
- `inferno-planner` ➜ may import `inferno-core` and `inferno-tools`.

> If a module violates layering, refactor. Keep logic in engines; keep I/O in CLI and loaders.

---

## 2) CLI Rules (Click)

**Do not implement logic in CLI functions.** CLI handlers:
- Parse flags/paths.
- Perform **lazy imports** of engines (`inferno_tools.*`) to avoid heavy startup and tight coupling.
- Call a single engine function. Return/print only what the engine provides.

Example (good):
```python
# packages/inferno-cli/src/inferno_cli/commands/cooling.py
@cooling.command("by-load")
@click.option("--budget-path", default="doctrine/power/rack-power-budget.yaml")
def cooling_by_load(budget_path: str) -> None:
    from inferno_tools.cooling import estimate_cooling_by_load
    estimate_cooling_by_load(budget_path=budget_path)
```

Example (avoid): business logic, file parsing, or YAML munging in CLI modules.

---

## 3) Models & Validation (Pydantic v2)

- Use **Pydantic v2** only. Prefer explicit submodels over `dict`.
- Configure models with `ConfigDict(extra="ignore")` so unknown keys don’t explode.
- Coerce external numeric fields with `@field_validator(..., mode="before")`.
- Lists of models: `TypeAdapter(list[MyModel]).validate_python(data)`.
- Raise `ValidationError` (preferred) or `ValueError` with file context.

**Example:**
```python
from pydantic import BaseModel, Field, field_validator, ConfigDict

class TorPorts(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sfp28_total: int = Field(ge=0)
    qsfp28_total: int = Field(ge=0)

    @field_validator("sfp28_total", "qsfp28_total", mode="before")
    @classmethod
    def _coerce_int(cls, v):
        return int(v)
```

Place **schemas** in `inferno-core` and **loaders** in `inferno_core.data.*`.

---

## 4) Engines & Calculators

- Business logic lives in `inferno-tools` (e.g., cabling, cooling, power). 
- Engines accept typed inputs (Pydantic models or simple dataclasses) and return structured results. 
- Engines should be **pure** (no printing). A thin presenter may format output for CLI.
- Prefer small functions with clear seams: `build_runs()`, `aggregate_bom()`, `validate_ports()`.

---

## 5) Dependency Management (uv)

This repo is a `uv` workspace. General rules:

- Add deps to the **correct package**:
  - Core models/validation ➜ `inferno-core`
  - Engines/calculators ➜ `inferno-tools`
  - CLI/UI ➜ `inferno-cli`

- Use `uv add` with `-p` (or `--project`) to target a package:
```bash
uv add -p packages/inferno-core pydantic@^2.5
uv add -p packages/inferno-cli click rich
uv add -p packages/inferno-tools pyyaml graphviz
```

- Sync the whole workspace from the repo root:
```bash
uv sync --all-packages --all-extras
```

- Run commands via `uv run`:
```bash
uv run inferno-cli tools cooling by-load
uv run -p packages/inferno-core pytest -q
```

> Pin ranges conservatively (e.g., `pydantic>=2.5,<3`) to avoid breaking changes.

---

## 6) Testing

- Use **pytest** under each package: `packages/<name>/tests/`.
- Test **happy path + coercion + failure modes** (e.g., missing required keys).
- Engines: deterministic tests with small fixtures in `tests/fixtures/`.
- Avoid network/file I/O in unit tests; use tmp paths and inline YAML.

Quick start:
```bash
uv run -p packages/inferno-core pytest -q
uv run -p packages/inferno-tools pytest -q
```

(Optional) Add coverage:
```bash
uv add -p packages/inferno-tools pytest-cov
uv run -p packages/inferno-tools pytest --cov=inferno_tools -q
```

---

## 7) Linting, Formatting, Types

Recommended (add as needed):
- **ruff** for linting: `uv add -p packages/inferno-core ruff`
- **black** for formatting: `uv add -p packages/inferno-core black`
- **mypy** for typing: `uv add -p packages/inferno-core mypy`

Formatting command (example):
```bash
uv run -p packages/inferno-core black packages/inferno-core
```

Type checking (example):
```bash
uv run -p packages/inferno-core mypy packages/inferno-core
```

---

## 8) File Conventions & Canonical Paths

- **Doctrine (YAML):**
  - `doctrine/naming/nodes.yaml` – physical hosts & attributes
  - `doctrine/network/topology.yaml` – spine/leaf and ToR uplinks per rack
  - `doctrine/network/tors.yaml` – ToR/spine inventory & port budgets
  - `doctrine/network/cabling-policy.yaml` – media rules, bins, site-defaults
  - `doctrine/power/rack-power-budget.yaml` – modeled loads per rack
  - `doctrine/site.yaml` – rack grid and ToR U position (optional)

> **Policy Validation:** Policy sanity checks run automatically; fix policy failures before calculating a BOM.

- **Outputs:** put generated files in `outputs/` (graphs, BOMs, CSVs).

- **Docs:** EPICs and TASKs live at repo root (`EPIC.*.md`, `TASK.*.md`).

---

## 9) Error Handling & UX

- Loaders raise `pydantic.ValidationError` with precise messages. Include file context when wrapping.
- Engines raise `ValueError`/`RuntimeError` with actionable messages; CLI catches and formats.
- CLI prints concise summaries; use **rich** for formatting in CLI only.

---

## 10) Versioning & Releases

- Each package has its own `pyproject.toml` and version. Use semver.
- Bump versions when interfaces change. Keep changelogs minimal but useful.

---

## 11) Contributions & Review

- Small, vertical PRs. Keep diffs reviewable.
- If you touch `doctrine/` schemas, update **models, loaders, and tests** in the same PR.
- Include before/after CLI snippets in PR description when UX is affected.

---

## 12) Quick Recipes

**Add a new engine (e.g., power topology):**
1. Define/extend Pydantic models in `inferno-core`.
2. Add loaders in `inferno_core.data.*`.
3. Implement engine in `inferno-tools` (pure functions).
4. Wire a CLI subcommand in `inferno-cli` (lazy import, no logic).
5. Add tests (core + tools). Update docs.

**Add a dependency to the right place:**
```bash
uv add -p packages/inferno-core pydantic@^2.5
uv sync --all-packages --all-extras
```

**Run a tool:**
```bash
uv run inferno-cli tools cabling estimate
uv run inferno-cli tools cabling calculate --export outputs/cabling_bom.yaml
```

---

## 13) Philosophy

We build as **systems architects**: clear layers, declarative inputs, and explicit models. The CLI is an interface, not a brain. Doctrine is the script; engines execute the ritual. Keep it elegant.