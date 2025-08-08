from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import csv
import math
import yaml

from rich.console import Console

# Import shared geometry helpers
from .common import compute_rack_distance_m, apply_slack, select_length_bin

# Import network loader functions
from inferno_core.data.network_loader import load_topology, load_tors, load_nodes, load_site

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


def _calculate_manhattan_distance(rack1_grid: List[int], rack2_grid: List[int], tile_m: float = 1.0) -> float:
    """Calculate Manhattan distance between two racks in meters."""
    return compute_rack_distance_m((rack1_grid[0], rack1_grid[1]), (rack2_grid[0], rack2_grid[1]), tile_m)


def _select_cable_type_and_bin(distance_m: float, link_type: str, policy: Dict[str, Any], length_bins_m: List[int]) -> Tuple[str, int]:
    """Select cable type and length bin based on distance and policy."""
    # Apply slack factor
    slack_factor = policy.get('heuristics', {}).get('slack_factor', 1.2)
    adjusted_distance = apply_slack(distance_m, slack_factor)

    # Find appropriate length bin
    selected_bin = select_length_bin(adjusted_distance, length_bins_m)

    if selected_bin is None:
        selected_bin = max(length_bins_m)  # Use largest bin if distance exceeds all bins

    # Determine cable type based on link type and distance
    media_rules = policy.get('media_rules', {})

    if link_type == '25G':
        rules = media_rules.get('sfp28_25g', {})
        dac_max = rules.get('dac_max_m', 3)
        if adjusted_distance <= dac_max:
            cable_type = rules.get('labels', {}).get('dac', 'SFP28 25G DAC')
        elif adjusted_distance <= 10:
            cable_type = rules.get('labels', {}).get('aoc', 'SFP28 25G AOC')
        else:
            cable_type = rules.get('labels', {}).get('fiber', 'SFP28 25G MMF + SR')
    elif link_type == '100G':
        rules = media_rules.get('qsfp28_100g', {})
        dac_max = rules.get('dac_max_m', 3)
        if adjusted_distance <= dac_max:
            cable_type = rules.get('labels', {}).get('dac', 'QSFP28 100G DAC')
        elif adjusted_distance <= 10:
            cable_type = rules.get('labels', {}).get('aoc', 'QSFP28 100G AOC')
        else:
            cable_type = rules.get('labels', {}).get('fiber', 'QSFP28 100G MMF + SR4')
    elif link_type == 'RJ45':
        rules = media_rules.get('rj45_cat6a', {})
        cable_type = rules.get('label', 'RJ45 Cat6A')
    else:
        cable_type = f"Unknown {link_type}"

    return cable_type, selected_bin


def _build_network_links(topology: Dict[str, Any], site: Optional[Dict[str, Any]], policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build network links with distances and cable types."""
    links = []

    # Build rack position lookup
    rack_positions = {}
    if site and 'racks' in site:
        for rack in site['racks']:
            rack_positions[rack['id']] = rack['grid']

    # Get spine rack position
    spine_rack = None
    if site and 'spine' in site:
        spine_rack = site['spine'].get('rack_id')

    # Process spine to leaf connections
    spines = topology.get('spines', [])
    leafs = topology.get('leafs', [])

    for spine in spines:
        spine_interfaces = spine.get('interfaces', [])
        for interface in spine_interfaces:
            if 'connects_to' in interface:
                # Parse connection (e.g., "tor-west-1:qsfp28-1")
                connection_parts = interface['connects_to'].split(':')
                if len(connection_parts) == 2:
                    leaf_id, leaf_port = connection_parts

                    # Find the leaf
                    leaf = next((l for l in leafs if l['id'] == leaf_id), None)
                    if leaf:
                        leaf_rack = leaf.get('rack_id')

                        # Calculate distance
                        distance_m = 3.0  # Default fallback
                        if spine_rack and leaf_rack and spine_rack in rack_positions and leaf_rack in rack_positions:
                            heuristics = policy.get('heuristics', {})
                            tile_m = heuristics.get('tile_m', 1.0)
                            distance_m = _calculate_manhattan_distance(
                                rack_positions[spine_rack],
                                rack_positions[leaf_rack],
                                tile_m
                            )
                        elif site is None:
                            # Use heuristic distances from policy
                            heuristics = policy.get('heuristics', {})
                            if spine_rack == leaf_rack:
                                distance_m = heuristics.get('same_rack_leaf_to_node_m', 1.5)
                            else:
                                distance_m = heuristics.get('adjacent_rack_leaf_to_spine_m', 3)

                        # Determine link type
                        link_type = interface.get('type', '100G')

                        # Select cable type and bin
                        cable_type, length_bin = _select_cable_type_and_bin(distance_m, link_type, policy, [1, 2, 3, 5, 7, 10])

                        links.append({
                            'from': f"{spine['id']}:{interface['name']}",
                            'to': f"{leaf_id}:{leaf_port}",
                            'type': link_type,
                            'distance_m': distance_m,
                            'cable_type': cable_type,
                            'length_bin': length_bin,
                            'category': 'spine_to_leaf'
                        })

    # Add WAN connections if specified
    if site and 'spine' in site and 'wan_handoff' in site['spine']:
        wan_handoff = site['spine']['wan_handoff']
        wan_count = wan_handoff.get('count', 2)
        wan_type = wan_handoff.get('type', 'RJ45')

        for i in range(wan_count):
            cable_type, length_bin = _select_cable_type_and_bin(2.0, wan_type, policy, [1, 2, 3, 5, 7, 10])
            links.append({
                'from': f"spine-wan-{i+1}",
                'to': f"wan-router:{i+1}",
                'type': wan_type,
                'distance_m': 2.0,
                'cable_type': cable_type,
                'length_bin': length_bin,
                'category': 'wan'
            })

    return links


def _aggregate_cable_bom(links: List[Dict[str, Any]], policy: Dict[str, Any], spares_fraction: float, length_bins_m: List[int]) -> Dict[str, Any]:
    """Aggregate links into BOM by cable type and length bin."""
    bom = {}

    # Count cables by type and length bin
    for link in links:
        cable_type = link['cable_type']
        length_bin = link['length_bin']

        if cable_type not in bom:
            bom[cable_type] = {}

        if length_bin not in bom[cable_type]:
            bom[cable_type][length_bin] = 0

        bom[cable_type][length_bin] += 1

    # Apply spares
    for cable_type in bom:
        for length_bin in bom[cable_type]:
            original_count = bom[cable_type][length_bin]
            bom[cable_type][length_bin] = _with_spares(original_count, spares_fraction)

    return bom


def _validate_bom(topology: Dict[str, Any], tors: Dict[str, Any], nodes: Dict[str, Any], links: List[Dict[str, Any]], policy: Dict[str, Any]) -> List[str]:
    """Validate BOM against port capacities and other constraints."""
    warnings = []

    # Check for missing data
    if not topology.get('spines'):
        warnings.append("No spines defined in topology")
    if not topology.get('leafs'):
        warnings.append("No leafs defined in topology")

    # Check link distances against cable type limits
    for link in links:
        distance = link['distance_m']
        cable_type = link['cable_type']

        # Basic distance checks
        if distance > 10 and 'DAC' in cable_type:
            warnings.append(f"DAC cable selected for {distance:.1f}m link (max recommended: 3m)")
        elif distance > 100:
            warnings.append(f"Very long link: {distance:.1f}m may exceed cable specifications")

    return warnings


def _export_bom(bom: Dict[str, Any], warnings: List[str], export_path: str, export_format: str, policy: Dict[str, Any]) -> None:
    """Export BOM to YAML or CSV format."""
    # Prepare metadata
    metadata = {
        'generated_by': 'inferno-cli tools cabling calculate',
        'policy_applied': policy.get('version', 'unknown'),
        'spares_fraction': policy.get('defaults', {}).get('spares_fraction', 0.1),
        'slack_factor': policy.get('defaults', {}).get('slack_factor', 1.2),
        'warnings': warnings
    }

    if export_format.lower() == 'csv':
        # Export as CSV
        with open(export_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Cable Type', 'Length Bin (m)', 'Quantity'])

            for cable_type in sorted(bom.keys()):
                for length_bin in sorted(bom[cable_type].keys()):
                    quantity = bom[cable_type][length_bin]
                    writer.writerow([cable_type, length_bin, quantity])
    else:
        # Export as YAML
        output_data = {
            'metadata': metadata,
            'bom': bom
        }

        with open(export_path, 'w') as yamlfile:
            yaml.dump(output_data, yamlfile, default_flow_style=False, sort_keys=True)


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
    """Deterministic BOM by reading manifests and policy.
    
    Loads topology, site, and policy data to calculate exact cable requirements
    based on physical distances and network connections.
    """
    console.print("\n[bold cyan]Cabling BOM Calculator[/bold cyan]")

    # Load all required data using raw YAML loading
    try:
        topology = _load_yaml(topology_path)
        tors = _load_yaml(tors_path) if Path(tors_path).exists() else {}
        nodes = _load_yaml(nodes_path) if Path(nodes_path).exists() else {}
        site = _load_yaml(site_path) if site_path and Path(site_path).exists() else None
        policy = load_cabling_policy(policy_path)
    except Exception as e:
        console.print(f"[red]Error loading data: {e}[/red]")
        return

    console.print(f"[green]✓[/green] Loaded topology: {len(topology.get('leafs', []))} ToRs, {len(topology.get('spines', []))} spines")
    console.print(f"[green]✓[/green] Loaded site: {len(site.get('racks', []) if site else [])} racks")

    # Build network graph and calculate distances
    links = _build_network_links(topology, site, policy)
    console.print(f"[green]✓[/green] Calculated {len(links)} network links")

    # Aggregate by cable type and length bin
    bom = _aggregate_cable_bom(links, policy, spares_fraction, length_bins_m)

    # Validate the results
    warnings = _validate_bom(topology, tors, nodes, links, policy)
    if warnings:
        console.print(f"[yellow]⚠[/yellow]  {len(warnings)} validation warnings")
        for warning in warnings:
            console.print(f"  [yellow]•[/yellow] {warning}")

    # Export the BOM
    _export_bom(bom, warnings, export_path, export_format, policy)
    console.print(f"[green]✓[/green] Exported BOM to {export_path}")


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
# ----------------------------
# roundtrip_bom: BOM summary and roundtrip YAML
# ----------------------------
def roundtrip_bom(*, bom_path: str, export_path: str, strict: bool = False) -> None:
    """
    Reads a BOM YAML file, computes a summary, and writes a summary YAML to export_path.
    Raises RuntimeError if the BOM file is missing or invalid.
    """
    import yaml
    from pathlib import Path
    try:
        # Use existing loader for consistency
        bom = _load_yaml(bom_path)
    except Exception as e:
        raise RuntimeError(f"Failed to load BOM file '{bom_path}': {e}")
    if not isinstance(bom, dict) or not bom:
        raise RuntimeError(f"BOM file '{bom_path}' is missing or invalid.")
    # BOM is expected to have a 'bom' key (per _export_bom), but fallback to root if not
    bom_dict = bom.get("bom") if "bom" in bom else bom
    if not isinstance(bom_dict, dict) or not bom_dict:
        raise RuntimeError(f"BOM file '{bom_path}' does not contain a valid BOM dictionary.")
    # Compute summary
    total_line_items = 0
    total_cables = 0
    cable_types_set = set()
    for cable_type, bins in bom_dict.items():
        cable_types_set.add(cable_type)
        if isinstance(bins, dict):
            for bin_qty in bins.values():
                total_line_items += 1
                try:
                    total_cables += int(bin_qty)
                except Exception:
                    pass
    cable_types = sorted(cable_types_set)
    output = {
        "metadata": {
            "generated_by": "inferno-tools.cabling.roundtrip_bom",
            "source_bom": bom_path,
            "strict": strict,
        },
        "summary": {
            "total_line_items": total_line_items,
            "total_cables": total_cables,
            "cable_types": cable_types,
        },
        "findings": [],
    }
    # Ensure parent directory exists
    Path(export_path).parent.mkdir(parents=True, exist_ok=True)
    with open(export_path, "w", encoding="utf-8") as f:
        yaml.dump(output, f, default_flow_style=False, sort_keys=True)

