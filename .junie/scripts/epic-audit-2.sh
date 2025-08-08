#!/usr/bin/env bash

# Inferno Epic Audit v2 — cabling & CLI pre-flight
# Run from repo root: `bash epic-audit-2.sh`

set -euo pipefail
set -x  # echo commands
shopt -s nullglob

BOLD="\033[1m"; DIM="\033[2m"; RED="\033[31m"; YEL="\033[33m"; GRN="\033[32m"; NC="\033[0m"

say() { printf "\n${BOLD}==> %s${NC}\n" "$*"; }
warn() { printf "${YEL}WARN:${NC} %s\n" "$*"; }
fail() { printf "${RED}FAIL:${NC} %s\n" "$*"; exit 1; }
ok() { printf "${GRN}OK:${NC} %s\n" "$*"; }

ROOT_DIR=$(pwd)
OUT_DIR="outputs"
AUDIT_PREFIX="${OUT_DIR}/_audit"
mkdir -p "$OUT_DIR"

# Audit behavior flags
RUN_PYTEST=${RUN_PYTEST:-1}            # 1 = run pytest at end; 0 = skip
REQUIRE_ROUNDTRIP=${REQUIRE_ROUNDTRIP:-0}  # 1 = fail if roundtrip missing; 0 = warn only

have_subcmd() { grep -q "$1" ${AUDIT_PREFIX}_cabling_help.txt; }

req_cmd() { command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"; }

say "Environment & versions"
req_cmd uv
uv --version || true
uv run python -V || true
uv run python - <<'PY'
import sys
print('python:', sys.version)
try:
    import click; print('click:', click.__version__)
except Exception as e:
    print('click: <missing>', e)
try:
    import yaml; print('pyyaml:', yaml.__version__)
except Exception as e:
    print('pyyaml: <missing>', e)
for mod in ('inferno_cli','inferno_tools','inferno_core'):
    try:
        __import__(mod)
        print(mod, 'import: OK')
    except Exception as e:
        print(mod, 'import: FAIL', e)
PY

say "CLI surface check"
uv run inferno-cli --help >/dev/null
uv run inferno-cli tools cabling --help | tee ${AUDIT_PREFIX}_cabling_help.txt
# Ensure subcommands exist
HAS_ROUNDTRIP=0
for sub in estimate calculate validate cross-validate roundtrip; do
  if ! grep -q "$sub" ${AUDIT_PREFIX}_cabling_help.txt; then
    warn "Subcommand missing in help: $sub"
    [[ "$sub" == "roundtrip" ]] && HAS_ROUNDTRIP=0 || true
  else
    [[ "$sub" == "roundtrip" ]] && HAS_ROUNDTRIP=1 || true
  fi
done
if [[ $REQUIRE_ROUNDTRIP -eq 1 && $HAS_ROUNDTRIP -eq 0 ]]; then
  fail "roundtrip subcommand required but not present"
fi
ok "CLI help rendered"

say "Finding codes and engine seams"
# Grep families; warn on miss, don't fail build
RG="rg -n --no-heading"; GREP="grep -RIn"
if ! command -v rg >/dev/null 2>&1; then RG="$GREP"; fi
$RG "validate_redundancy\(|REDUNDANCY_" packages || warn "No redundancy symbols found"
$RG "validate_oversubscription\(|OVERSUB_" packages || warn "No oversubscription symbols found"
$RG "roundtrip_bom\(|ROUNDTRIP_" packages || warn "No roundtrip symbols found"
$RG "cross[_-]validate\(|CROSS_" packages || warn "No cross-validate symbols found"
$RG "compute_rack_distance_m|apply_slack|select_length_bin|nic_line_rate_gbps" packages || warn "Shared helper(s) not found"
$RG "SITE_GEOMETRY_|POLICY_|BOM_|LOAD_YAML_|REF_" packages || warn "Some finding families not present"

say "Manifests presence"
POLICY=doctrine/network/cabling-policy.yaml
TOPO=doctrine/network/topology.yaml
TORS=doctrine/network/tors.yaml
NODES=doctrine/naming/nodes.yaml
SITE=doctrine/site.yaml
POWER=doctrine/power/rack-power-budget.yaml

for f in "$POLICY" "$TOPO" "$TORS" "$NODES" "$POWER"; do
  [[ -f "$f" ]] || fail "Missing required doctrine file: $f"
  ok "Found $f"
done
[[ -f "$SITE" ]] || warn "Optional geometry file missing: $SITE (geometry fallbacks will be used)"

say "Quick-parse manifests via project loader"
uv run python - <<PY
from pathlib import Path
from inferno_core.data.loader import load_yaml_file
files = [
    'doctrine/network/cabling-policy.yaml',
    'doctrine/network/topology.yaml',
    'doctrine/network/tors.yaml',
    'doctrine/naming/nodes.yaml',
    'doctrine/power/rack-power-budget.yaml',
]
for p in files:
    data = load_yaml_file(Path(p))
    t = type(data).__name__
    print(f"ok:{p} -> {t}")
PY

say "CLI smoke: estimate (heuristic)"
set +e
uv run inferno-cli tools cabling estimate --policy "$POLICY" | tee ${AUDIT_PREFIX}_estimate.txt
EST_RC=$?
set -e
if [[ $EST_RC -ne 0 ]]; then
  warn "estimate subcommand exited $EST_RC"
  if grep -qi "cannot import name 'estimate_cabling_heuristic'" ${AUDIT_PREFIX}_estimate.txt; then
    warn "Hint: re-export estimate_cabling_heuristic in inferno_tools.cabling.__init__ or fix CLI import path."
  fi
else
  grep -E "Leaf.+Node|with spares|Policy:" ${AUDIT_PREFIX}_estimate.txt >/dev/null || warn "Estimate output missing expected substrings"
fi

say "CLI smoke: calculate + validate (happy path)"
BOM="${AUDIT_PREFIX}_bom.yaml"
FIND="${AUDIT_PREFIX}_findings.yaml"
uv run inferno-cli tools cabling calculate --export "$BOM" --format yaml || fail "calculate failed"
head -n 30 "$BOM" || true
uv run inferno-cli tools cabling validate --export "$FIND" || true
head -n 40 "$FIND" || true
if ! grep -q "summary:" "$FIND"; then warn "Findings export lacks summary"; fi

say "Roundtrip + Cross-validate (if available)"
ROUND="${AUDIT_PREFIX}_roundtrip.yaml"
REC="${AUDIT_PREFIX}_reconcile.yaml"
if [[ $HAS_ROUNDTRIP -eq 1 ]]; then
  if uv run inferno-cli tools cabling roundtrip --bom "$BOM" --export "$ROUND"; then
    ok "roundtrip executed"
    head -n 30 "$ROUND" || true
  else
    warn "roundtrip subcommand returned non-zero (engine may be a stub)"
  fi
else
  warn "roundtrip subcommand missing; skipping roundtrip check"
fi
if uv run inferno-cli tools cabling cross-validate --bom "$BOM" --export "$REC"; then
  ok "cross-validate executed"
  head -n 30 "$REC" || true
else
  warn "cross-validate subcommand returned non-zero (engine may be a stub)"
fi

say "Exit code plumbing sanity (strict mode)"
set +e
uv run inferno-cli tools cabling validate --strict --export "$FIND" > ${AUDIT_PREFIX}_strict.txt 2>&1
STRICT_RC=$?
tail -n 5 ${AUDIT_PREFIX}_strict.txt || true
set -e
if [[ $STRICT_RC -eq 0 || $STRICT_RC -eq 2 ]]; then
  ok "strict validate exit code acceptable: $STRICT_RC"
else
  warn "strict validate returned $STRICT_RC (expected 0 or 2 depending on WARNs)"
fi

if [[ $RUN_PYTEST -eq 1 ]]; then
  say "Pytest quick run (project root)"
  set +e
  uv run pytest -q | tee ${AUDIT_PREFIX}_pytest.txt
  PY_RC=${PIPESTATUS[0]}
  set -e
  if [[ $PY_RC -eq 0 ]]; then
    ok "pytest: all tests passed"
  else
    warn "pytest exited $PY_RC (see ${AUDIT_PREFIX}_pytest.txt)"
  fi
fi

say "Summary"
echo "Outputs:"
ls -1 ${OUT_DIR}/_audit_* 2>/dev/null || true
ok "Audit complete"
