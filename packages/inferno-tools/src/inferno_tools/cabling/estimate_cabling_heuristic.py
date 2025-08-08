from typing import Optional, List

from inferno_core.data.cabling_policy import load_cabling_policy
from inferno_tools.cabling import _with_spares
from rich.console import Console

console = Console()

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
    console.print(
        f"[yellow]"
        f"Leaf → Node (SFP28 25G):"
        f"[/yellow]"
        f" {total_leaf_to_node}  "
        f"[dim]"
        f"(with spares: {total_leaf_to_node_sp})"
        f"[/dim]"
    )
    console.print(
        f"[yellow]"
        f"Leaf → Spine (QSFP28 100G):"
        f"[/yellow]"
        f" {total_leaf_to_spine} "
        f"[dim]"
        f"(with spares: {total_leaf_to_spine_sp})"
        f"[/dim]"
    )
    console.print(f"[yellow]Mgmt (RJ45 Cat6A):[/yellow] {total_mgmt}  [dim](with spares: {total_mgmt_sp})[/dim]")
    console.print(f"[yellow]WAN (RJ45 Cat6A):[/yellow] {total_wan}  [dim](with spares: {total_wan_sp})[/dim]")

    console.print(
        "\n"
        "[dim]"
        "Policy:"
        "[/dim]"
        " {p}\n"
        "[dim]Bins — SFP28:[/dim]"
        " {b1}  "
        "[dim]QSFP28:[/dim]"
        " {b2}  "
        "[dim]RJ45:[/dim]"
        " {b3}\n".format(
            p=policy_path,
            b1=",".join(map(str, sfp28_bins)),
            b2=",".join(map(str, qsfp28_bins)),
            b3=",".join(map(str, rj45_bins)),
        )
    )
    console.print(
        f"[dim]"
        f"Assumes {num_racks_eff} racks × {nodes_per_rack_eff} nodes per rack;"
        f" {uplinks_per_rack_eff} QSFP28 uplinks per ToR; {mgmt_rj45_per_node_eff} RJ45 mgmt per node;"
        f" {wan_cat6a_eff} WAN trunks (from policy/site-defaults)."
        f"[/dim]\n"
    )
