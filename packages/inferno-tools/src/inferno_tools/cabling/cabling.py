from typing import Optional

from . import estimate_cabling_heuristic
from rich.console import Console

console = Console()


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
    console.print(
        "[dim]Implementation pending: port capacity checks, NIC coverage, and oversubscription warnings.[/dim]\n"
    )


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
    console.print(
        "[dim yellow]Deprecated:[/dim yellow] use `inferno-cli tools cabling estimate` (policy-driven) instead.\n"
    )

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


# ----------------------------
# roundtrip_bom: BOM summary and roundtrip YAML
# ----------------------------
