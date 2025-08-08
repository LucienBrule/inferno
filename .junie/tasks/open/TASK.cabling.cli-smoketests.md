

# TASK.cabling.cli-smoketests — End‑to‑End CLI behavior & exit codes

**Owner:** Junie  
**State:** Ready  
**Area:** Networking / Cabling QA  
**Packages:** `inferno-cli`, `inferno-tools`, `inferno-core`

---

## Purpose
Provide **end‑to‑end** confidence that the cabling CLI surfaces behave correctly for common and failure paths, with explicit pass/fail criteria and constraints:
- **Command surface**: All required commands exist and accept documented flags/options; `--help` output is complete and accurate for each command.
- **Human output**: Output to stdout/stderr contains expected, stable substrings or regexes for both successful and error cases.
- **Export artifacts**: `--export` artifacts are written exactly to the specified path(s), are valid YAML, and contain required top-level keys.
- **Exit codes**: Exit codes strictly conform to the CLI spec (0 for PASS, 1 for FAIL, 2 for WARN with `--strict`).
- **Error handling**: All error output is human-readable, names missing paths/invalid inputs, and never leaks raw stack traces.

These tests are **smoke‑level** (fast, deterministic) and sit **on top of** the engines validated in other tasks. Tests must be hermetic, deterministic, and not rely on network or mutable global state.

---

## Scope / Non‑Goals
- **In‑scope:** `inferno-cli tools cabling {estimate, calculate, validate, cross-validate}`: CLI surface, argument handling, exit codes, artifact writing, error handling, and output shape.
- **Out‑of‑scope:** Detailed math/geometry/policy validation (covered by engine unit tests); non‑cabling CLI; performance/stress testing; networked or environment-dependent behaviors.

---

## Test Harness
- Use **pytest** with Click’s **`CliRunner`** to invoke the CLI **in‑process** (fast and hermetic).
- Each test must create a per‑test **temp working dir** and copy only the required doctrine fixture(s) into it.
- **Tests must not depend on network access** or any external services; all data must be from local, versioned fixtures.
- **Fixtures must not be mutated** except for files in test-generated temp directories (e.g., under `outputs/`). **No doctrine or non-temp files may be mutated.**
- **All CLI invocations must be deterministic**: test data, arguments, and results must not depend on time, randomness, or environment.
- **Assertions must use stable substrings/regexes**—avoid brittle full-line matches. All assertions on output must include meaningful assertion messages.
- **Assert both stdout and stderr expectations** where relevant; do not ignore stderr.
- **Verify exit codes and artifact creation** for every command under test.
- All YAML exports must be loaded and schema-validated for top-level structure (e.g., keys like `summary`, `findings`, `meta`, `items`).

```python
# packages/inferno-cli/tests/test_cli_cabling_smoke.py
from __future__ import annotations
from pathlib import Path
from shutil import copytree
from click.testing import CliRunner
import yaml

from inferno_cli.__main__ import cli  # click Group

FIXTURES = Path(__file__).parent / "fixtures" / "cabling"


def _prep_fixture(tmp_path: Path, name: str) -> Path:
    src = FIXTURES / name
    dst = tmp_path / name
    copytree(src, dst)
    return dst


def _run(cli_args: list[str], cwd: Path):
    runner = CliRunner(mix_stderr=False)
    return runner.invoke(cli, cli_args, catch_exceptions=False, obj=None, color=False, env={}, standalone_mode=True, 
                         prog_name="inferno-cli", 
                        )
```

> If the console script is not importable, fall back to `subprocess.run([sys.executable, '-m', 'inferno_cli', ...])` for the E2E path. Prefer `CliRunner` for speed.

---

## Fixtures
All fixtures must reside under `packages/inferno-cli/tests/fixtures/cabling/` and be **self-contained** (no references outside the fixture directory). Each fixture directory has a clear intent and constraints:

- `happy/`  
  Minimal, valid doctrine manifests (`doctrine/network/topology.yaml`, `doctrine/network/tors.yaml`, `doctrine/naming/nodes.yaml`, `doctrine/network/cabling-policy.yaml`, optional `doctrine/site.yaml`). All files required for a successful `validate` run. **No errors or warnings expected.** Must not be mutated by tests.

- `warn_only/`  
  Contains doctrine manifests designed to trigger **WARN** findings (e.g., oversubscription within warn margin, RJ45 >100 m bin usage). Should return **0** exit code by default and **2** with `--strict`. Must not be mutated by tests.

- `fail/`  
  Contains doctrine manifests with deliberate errors (e.g., zero uplinks but non‑zero edge bandwidth; missing ToR id). Must fail validation with exit code **1**. Must not be mutated by tests.

- `bom/`  
  Contains a valid doctrine plus a pre-generated BOM YAML (`outputs/cabling_bom.yaml`) derived from `happy/`, for use by `cross-validate`. Tests must not depend on state produced by other tests; use only files in this fixture directory. Must not be mutated by tests.

> All fixture directories are **read-only** during test execution except for explicit test-generated output files (e.g., under `outputs/`). Tests must not mutate or delete any doctrine or fixture files.

---

## Tests

### 1) Help & Command Surface
- `inferno-cli tools cabling --help` output must list all subcommands: `estimate`, `calculate`, `validate`, `cross-validate`.
- **Each subcommand must be invoked with `--help`** (e.g., `inferno-cli tools cabling estimate --help`) and must show all documented options (e.g., `--export`, `--format`, `--policy`, `--spares`, `--strict`) in its help output.
- All help output must be asserted for presence of expected option and argument descriptions.

### 2) `estimate` (heuristic)
- Run in `happy/` fixture with default policy path (or `--policy` override).
- Assert output to stdout contains substrings:
  - `Inferno Cabling Estimator`
  - `Leaf → Node (SFP28 25G):` and `with spares:`
  - policy path echo
- Assert relevant output appears on the correct stream (stdout/stderr) and exit code is **0**.

### 3) `calculate` (deterministic BOM)
- Run in `happy/` with `--export bom.yaml --format yaml`.
- Assert `bom.yaml` exists and can be parsed as YAML; file must contain top-level `meta` and `items` keys.
- Assert at least one `leaf-node` and one `leaf-spine` item are present in the BOM.
- Assert exit code is **0** and all relevant output is on the expected stream (stdout/stderr).

### 4) `validate` (findings & exit codes)
- **PASS case:** Run in `happy/` → expect exit code **0**. Output contains `PASS` and a summary table.
- **WARN case:** Run in `warn_only/` → expect exit code **0**; then with `--strict`, expect exit code **2**. Output contains `WARN` lines and a totals block. When `--export findings.yaml` is used, the file must contain a valid YAML report with top-level `summary` and `findings` arrays.
- **FAIL case:** Run in `fail/` → expect exit code **1**. Output contains `FAIL` lines with stable error codes.
- In all cases, tests must assert both stdout and stderr expectations as relevant, and all exported YAML must be schema-checked for required keys.

### 5) `cross-validate` (BOM reconciliation)
- Use the self‑contained `bom/` fixture (contains doctrine + `outputs/cabling_bom.yaml`).
- Run `cross-validate --bom outputs/cabling_bom.yaml --export outputs/cabling_reconciliation.yaml`.
- **Happy path:** exit code **0**; reconciliation YAML must contain all summary counters at 0.
- **Drift path:** In a temp copy, modify the BOM to remove a `leaf-node` item, then run `cross-validate`; expect exit code **1** and output containing a `MISSING_LINK` finding.
- All YAML exports must be schema-validated for required keys and structure.

### 6) Error handling (missing files)
- In an empty temp directory, run `validate`. Expect a **non‑zero exit code** and a human-readable error message naming the missing file(s) or path(s).
- **No raw stack traces may appear in output** (stdout or stderr); only human-readable errors naming the missing path(s) or invalid inputs are allowed.

---

## Example Test (sketch)
```python
def test_calculate_and_validate_happy(tmp_path: Path):
    wd = _prep_fixture(tmp_path, "happy")
    bom_path = wd / "outputs" / "cabling_bom.yaml"

    # calculate
    res_calc = _run(["tools", "cabling", "calculate", "--export", str(bom_path), "--format", "yaml"], cwd=wd)
    assert res_calc.exit_code == 0, f"Unexpected exit code: {res_calc.exit_code}\nOutput: {res_calc.output}"
    assert bom_path.exists(), "BOM YAML was not created"

    # validate (PASS)
    findings_path = wd / "outputs" / "findings.yaml"
    res_val = _run(["tools", "cabling", "validate", "--export", str(findings_path)], cwd=wd)
    assert res_val.exit_code == 0, f"Unexpected exit code: {res_val.exit_code}\nOutput: {res_val.output}"
    data = yaml.safe_load(findings_path.read_text())
    assert "summary" in data and "findings" in data, "YAML export missing required keys"
    # Example: assert output on both stdout and stderr as needed
    assert "PASS" in res_val.output, "PASS not in output"
```

---

## Implementation Notes
- Keep CLI printing **human‑centric** (short, aligned). Tests should match **stable substrings/regexes**, not full lines.
- Tests must not rely on internet access or external resources.
- Prefer `CliRunner` for speed; only use subprocess when import paths make in‑process invocation hard.
- **All test-generated files must be written only under temp directories (e.g., outputs/), and never mutate or delete doctrine or fixture files.**
- **All assertions must include meaningful messages** for failures.
- **All YAML exports must be loaded and checked for required top-level keys.**
- **No test may depend on non-deterministic values or global state.**

---

## Acceptance Criteria
- All four subcommands are exercised in tests with explicit PASS, WARN, and FAIL paths.
- All CLI commands under test are invoked with `--help` and have their options/arguments coverage asserted.
- Exit codes 0/1/2 are observed and asserted in all relevant tests.
- All `--export` paths produce valid YAML with required top‑level keys, and YAML is schema-validated in tests.
- Tests assert both stdout and stderr as relevant, with meaningful assertion messages.
- No test relies on network access, environment, or non-deterministic state; all fixtures are self-contained.
- No test mutates or deletes doctrine or fixture files outside temp outputs.
- Error handling is verified: no raw stack traces are output, and all errors are human-readable and name missing/invalid paths or inputs.
- This suite becomes part of CI gating for cabling changes.
