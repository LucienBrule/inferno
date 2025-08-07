from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import math

from rich.console import Console

console = Console()


# ----------------------------
# Dataclasses (for future structured returns)
# ----------------------------

@dataclass(frozen=True)
class CablingSummary:
    leaf_to_node: int
    leaf_to_spine: int
    mgmt_cat6a: int
    wan_cat6a: int


# ----------------------------
# Public stubs used by CLI
# ----------------------------

#
# Policy loading helpers
# ----------------------------

def _load_yaml(path: str) -> dict:
    try:
        import yaml  # local import to avoid hard dep elsewhere
        p = Path(path)
        if not p.exists():
            return {}
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def load_cabling_policy(path: str) -> dict:
    """Return a normalized policy dict with safe defaults if missing."""
    data = _load_yaml(path)
    defaults = (data.get("defaults") or {})
    media = (data.get("media_rules") or {})

    # Safe defaults
    nodes_25g_per_node = int(defaults.get("nodes_25g_per_node", 1))
    mgmt_rj45_per_node = int(defaults.get("mgmt_rj45_per_node", 1))
    wan_cat6a_count = int(defaults.get("wan_cat6a_count", 2))
    tor_uplink_qsfp28_per_tor = int(defaults.get("tor_uplink_qsfp28_per_tor", 2))
    spares_fraction = float(defaults.get("spares_fraction", 0.10))

    site = (data.get("site-defaults") or {})
    num_racks = int(site.get("num_racks", 4))
    nodes_per_rack = int(site.get("nodes_per_rack", 4))
    uplinks_per_rack = int(site.get("uplinks_per_rack", 2))
    mgmt_rj45_site = int(site.get("mgmt_rj45_per_node", mgmt_rj45_per_node))
    wan_cat6a_site = int(site.get("wan_cat6a", 2))

    def _bins(key: str, label_key: str = None) -> list[int]:
        m = media.get(key) or {}
        bins = m.get("bins_m") or [1, 2, 3, 5, 7, 10]
        try:
            return [int(x) for x in bins]
        except Exception:
            return [1, 2, 3, 5, 7, 10]

    return {
        "defaults": {
            "nodes_25g_per_node": nodes_25g_per_node,
            "mgmt_rj45_per_node": mgmt_rj45_per_node,
            "wan_cat6a_count": wan_cat6a_count,
            "tor_uplink_qsfp28_per_tor": tor_uplink_qsfp28_per_tor,
            "spares_fraction": spares_fraction,
        },
        "site_defaults": {
            "num_racks": num_racks,
            "nodes_per_rack": nodes_per_rack,
            "uplinks_per_rack": uplinks_per_rack,
            "mgmt_rj45_per_node": mgmt_rj45_site,
            "wan_cat6a": wan_cat6a_site,
        },
        "bins": {
            "sfp28": _bins("sfp28_25g"),
            "qsfp28": _bins("qsfp28_100g"),
            "rj45": _bins("rj45_cat6a"),
        },
    }


def _with_spares(count: int, spares_fraction: float) -> int:
    return int(math.ceil(count * (1.0 + spares_fraction)))
def estimate_cabling_heuristic(
    *,
    policy_path: str = "doctrine/network/cabling-policy.yaml",
    spares_fraction: float = 0.10,
    length_bins_m: Optional[List[int]] = None,
    # heuristic knobs (kept for DX; later replaced by policy file)
    num_racks: int = 4,
    nodes_per_rack: int = 4,
    uplinks_per_rack: int = 2,
    mgmt_rj45_per_node: int = 1,
    wan_cat6a: int = 2,
    include_spine_links: bool = True,
) -> None:
    """Quick heuristic counts by class (no site geometry required).

    Loads defaults from `policy_path` when present.
    """
    if length_bins_m is None:
        length_bins_m = [1, 2, 3, 5, 7, 10]

    # Load policy and override planning knobs for counts
    policy = load_cabling_policy(policy_path)
    p_def = policy.get("defaults", {})
    p_bins = policy.get("bins", {})

    p_site = policy.get("site_defaults", {})

    num_racks_eff = int(p_site.get("num_racks", num_racks))
    nodes_per_rack_eff = int(p_site.get("nodes_per_rack", nodes_per_rack))
    uplinks_per_rack_eff = int(p_site.get("uplinks_per_rack", uplinks_per_rack))
    mgmt_rj45_per_node_eff_site = int(p_site.get("mgmt_rj45_per_node", mgmt_rj45_per_node))
    wan_cat6a_eff_site = int(p_site.get("wan_cat6a", wan_cat6a))

    nodes_25g_per_node_eff = int(p_def.get("nodes_25g_per_node", 1))
    mgmt_rj45_per_node_eff = int(p_def.get("mgmt_rj45_per_node", mgmt_rj45_per_node_eff_site))
    wan_cat6a_eff = int(p_def.get("wan_cat6a_count", wan_cat6a_eff_site))
    uplinks_per_rack_eff = int(p_def.get("tor_uplink_qsfp28_per_tor", uplinks_per_rack_eff))
    spares_fraction_eff = float(p_def.get("spares_fraction", spares_fraction))

    # Use policy bins for display
    sfp28_bins = p_bins.get("sfp28", length_bins_m)
    qsfp28_bins = p_bins.get("qsfp28", length_bins_m)
    rj45_bins = p_bins.get("rj45", length_bins_m)

    # Compute base counts
    total_leaf_to_node = num_racks_eff * nodes_per_rack_eff * nodes_25g_per_node_eff
    total_leaf_to_spine = num_racks_eff * uplinks_per_rack_eff if include_spine_links else 0
    total_mgmt = num_racks_eff * nodes_per_rack_eff * mgmt_rj45_per_node_eff
    total_wan = wan_cat6a_eff

    # With spares (rounded up)
    total_leaf_to_node_sp = _with_spares(total_leaf_to_node, spares_fraction_eff)
    total_leaf_to_spine_sp = _with_spares(total_leaf_to_spine, spares_fraction_eff)
    total_mgmt_sp = _with_spares(total_mgmt, spares_fraction_eff)
    total_wan_sp = _with_spares(total_wan, spares_fraction_eff)

    console.print("\n[bold cyan]Inferno Cabling Estimator (heuristic)[/bold cyan]\n")
    console.print(f"[yellow]Leaf → Node (SFP28 25G):[/yellow] {total_leaf_to_node}  [dim](with spares: {total_leaf_to_node_sp})[/dim]")
    console.print(f"[yellow]Leaf → Spine (QSFP28 100G):[/yellow] {total_leaf_to_spine}  [dim](with spares: {total_leaf_to_spine_sp})[/dim]")
    console.print(f"[yellow]Mgmt (RJ45 Cat6A):[/yellow] {total_mgmt}  [dim](with spares: {total_mgmt_sp})[/dim]")
    console.print(f"[yellow]WAN (RJ45 Cat6A):[/yellow] {total_wan}  [dim](with spares: {total_wan_sp})[/dim]")

    console.print(
        "\n[dim]Policy:[/dim] {p}\n[dim]Bins — SFP28:[/dim] {b1}  [dim]QSFP28:[/dim] {b2}  [dim]RJ45:[/dim] {b3}\n".format(
            p=policy_path,
            b1=",".join(map(str, sfp28_bins)),
            b2=",".join(map(str, qsfp28_bins)),
            b3=",".join(map(str, rj45_bins)),
        )
    )
    console.print(
        "[dim]Assumes {r} racks × {n} nodes per rack; {u} QSFP28 uplinks per ToR; {m} RJ45 mgmt per node; {w} WAN trunks (from policy/site-defaults).[/dim]\n".format(
            r=num_racks_eff, n=nodes_per_rack_eff, u=uplinks_per_rack_eff, m=mgmt_rj45_per_node_eff, w=wan_cat6a_eff
        )
    )


def calculate_cabling_bom(
    *,
    topology_path: str,
    nodes_path: str,
    tors_path: str,
    site_path: Optional[str],
    policy_path: str,
    spares_fraction: float,
    length_bins_m: List[int],
    export_path: str,
    export_format: str,
) -> None:
    """Deterministic BOM by reading manifests and policy (stub).

    This stub just prints the parameters it received so you can verify
    CLI wiring. The real implementation will parse YAML and produce a
    BOM aggregated by media type and length bin, with validation notes.
    """
    console.print("\n[bold cyan]Cabling BOM (calculate) — stub[/bold cyan]")
    console.print(f"topology: {topology_path}")
    console.print(f"nodes:    {nodes_path}")
    console.print(f"tors:     {tors_path}")
    console.print(f"site:     {site_path or '(none)'}")
    console.print(f"policy:   {policy_path}")
    console.print(f"spares:   {spares_fraction}")
    console.print(f"bins(m):  {length_bins_m}")
    console.print(f"export:   {export_path} ({export_format})\n")
    console.print("[dim]Implementation pending: manifest ingestion, geometry, media selection, binning, and export.[/dim]\n")


def validate_cabling(
    *,
    topology_path: str,
    nodes_path: str,
    tors_path: str,
) -> None:
    """Sanity-check manifests vs port budgets and NIC declarations (stub)."""
    console.print("\n[bold cyan]Cabling Validation — stub[/bold cyan]")
    console.print(f"topology: {topology_path}")
    console.print(f"nodes:    {nodes_path}")
    console.print(f"tors:     {tors_path}\n")
    console.print("[dim]Implementation pending: port capacity checks, NIC coverage, and oversubscription warnings.[/dim]\n")


def visualize_cabling(
    *,
    site_path: Optional[str],
    output_path: str,
) -> None:
    """Render a simple SVG of rack grid and link classes (stub)."""
    console.print("\n[bold cyan]Cabling Visualization — stub[/bold cyan]")
    console.print(f"site:   {site_path or '(none)'}")
    console.print(f"output: {output_path}\n")
    console.print("[dim]Implementation pending: SVG layout using site geometry and link classes.[/dim]\n")


# ----------------------------
# Back-compat shim (legacy name)
# ----------------------------
def estimate_cabling(
        num_racks: int = 4,
        nodes_per_rack: int = 4,
        uplinks_per_rack: int = 2,
        trunk_cables: int = 2,
        include_spine_links: bool = True,
):
    # DEPRECATED: Kept for early experiments. Prefer `estimate_cabling_heuristic()`.
    console.print("[dim yellow]Deprecated:[/dim yellow] use `inferno-cli tools cabling estimate` (policy-driven) instead.\n")

    # Map legacy knobs into the modern estimator, but allow policy/site-defaults to override.
    estimate_cabling_heuristic(
        policy_path="doctrine/network/cabling-policy.yaml",
        spares_fraction=0.10,
        length_bins_m=None,
        num_racks=num_racks,
        nodes_per_rack=nodes_per_rack,
        uplinks_per_rack=uplinks_per_rack,
        mgmt_rj45_per_node=1,
        wan_cat6a=trunk_cables,
        include_spine_links=include_spine_links,
    )
    return
