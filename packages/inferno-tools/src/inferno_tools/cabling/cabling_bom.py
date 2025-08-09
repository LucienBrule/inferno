import csv
from typing import List, Optional, Dict

from inferno_core.codebase.debug import spy_trace
from inferno_core.models.cable_bom import CableBOMSummary
from inferno_core.models.unified_topology import NetworkTopology
from inferno_core.models.tor import Tor
from inferno_core.models.records import NodeRec
from inferno_core.models.records import SiteRec
from inferno_core.models.cabling_policy import CablingPolicy, MediaLabels, MediaRule
from inferno_core.models.records import LinkRec

from inferno_core.data.cabling_policy import load_cabling_policy_typed
from inferno_core.data.network import load_network_topology
from inferno_core.data.network_loader import load_site, load_nodes
from inferno_core.data.tors import load_tors_typed
from inferno_tools.cabling import with_spares, build_network_links
from inferno_tools.cabling.cabling import console


@spy_trace
def _get(obj, key, default=None):
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


@spy_trace
def _getitem(obj, key, default=None):
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key)
    except Exception:
        return default


# links: [{'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 0.0, 'from': 'spine-1:eth1/1', 'length_bin': 1, 'to': 'tor-west-1:qsfp28-1', 'type': '100G'}, {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 1.0, 'from': 'spine-1:eth1/2', 'length_bin': 2, 'to': 'tor-east-1:qsfp28-1', 'type': '100G'}, {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 1.0, 'from': 'spine-1:eth1/3', 'length_bin': 2, 'to': 'tor-north-1:qsfp28-1', 'type': '100G'}, {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 2.0, 'from': 'spine-1:eth1/4', 'length_bin': 3, 'to': 'tor-crypt-1:qsfp28-1', 'type': '100G'}]


def _aggregate_cable_bom(
    links: List[LinkRec], policy: CablingPolicy, spares_fraction: float, length_bins_m: List[int]
) -> Dict[str, Dict[int, int]]:
    bom: Dict[str, Dict[int, int]] = {}
    for (
        link
    ) in (
        links
    ):  # {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 0.0, 'from': 'spine-1:eth1/1', 'length_bin': 1, 'to': 'tor-west-1:qsfp28-1', 'type': '100G'}
        cable_type = _getitem(link, "cable_type")
        length_bin = _getitem(link, "length_bin")
        if cable_type is None or length_bin is None:
            continue
        bom.setdefault(str(cable_type), {})
        bom[str(cable_type)][int(length_bin)] = bom[str(cable_type)].get(int(length_bin), 0) + 1
    for ctype, bins in bom.items():
        for b, qty in list(bins.items()):
            bins[b] = with_spares(qty, spares_fraction)
    return bom


def _validate_bom(
    topology: NetworkTopology,
    tors: List[Tor],
    nodes: List[NodeRec],
    links: List[dict[str, str | int | float | None]],
    policy: CablingPolicy,
) -> List[str]:
    """

    :type links: [{'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 0.0, 'from': 'spine-1:eth1/1', 'length_bin': 1, 'to': 'tor-west-1:qsfp28-1', 'type': '100G'}, {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 1.0, 'from': 'spine-1:eth1/2', 'length_bin': 2, 'to': 'tor-east-1:qsfp28-1', 'type': '100G'}, {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 1.0, 'from': 'spine-1:eth1/3', 'length_bin': 2, 'to': 'tor-north-1:qsfp28-1', 'type': '100G'}, {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 2.0, 'from': 'spine-1:eth1/4', 'length_bin': 3, 'to': 'tor-crypt-1:qsfp28-1', 'type': '100G'}]
    """
    warnings: List[str] = []
    spines = topology.spines if topology.spines else []
    leafs = topology.leafs if topology.leafs else []
    if not spines:
        warnings.append("No spines defined in topology")
    if not leafs:
        warnings.append("No leafs defined in topology")
    for link in links:
        distance = _getitem(link, "distance_m", 0.0) or 0.0
        cable_type = str(_getitem(link, "cable_type", ""))
        if distance > 10 and "DAC" in cable_type:
            warnings.append(f"DAC cable selected for {distance:.1f}m link (max recommended: 3m)")
        elif distance > 100:
            warnings.append(f"Very long link: {distance:.1f}m may exceed cable specifications")
    return warnings


def _export_bom(
    bom: Dict[str, Dict[int, int]], warnings: List[str], export_path: str, export_format: str, policy: CablingPolicy
) -> None:
    # derive metadata from model-ish policy
    version = _get(policy, "version", "unknown")
    defaults = _get(policy, "defaults", None)
    heuristics = _get(policy, "heuristics", None)
    spares_fraction = _get(defaults, "spares_fraction", 0.1)
    slack_factor = _get(heuristics, "slack_factor", 1.2)

    metadata = {
        "generated_by": "inferno-cli tools cabling calculate",
        "policy_applied": version,
        "spares_fraction": spares_fraction,
        "slack_factor": slack_factor,
        "warnings": warnings,
    }

    if export_format.lower() == "csv":
        with open(export_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Cable Type", "Length Bin (m)", "Quantity"])
            for cable_type in sorted(bom.keys()):
                for length_bin in sorted(bom[cable_type].keys()):
                    writer.writerow([cable_type, length_bin, bom[cable_type][length_bin]])
    else:
        # local import to keep yaml scoped to this function only
        import yaml  # type: ignore

        output_data = {"metadata": metadata, "bom": bom}
        with open(export_path, "w") as yamlfile:
            yaml.dump(output_data, yamlfile, default_flow_style=False, sort_keys=True)


@spy_trace
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

    topology = load_network_topology(topology_path)
    tors = load_tors_typed(tors_path)
    nodes = load_nodes(nodes_path)
    site = load_site(site_path)
    policy = load_cabling_policy_typed(policy_path)

    console.print(f"[green]✓[/green] Loaded topology: {len(topology.leafs)} ToRs, {len(topology.spines)} spines")
    site_racks = site.racks if isinstance(site.racks, list) else []
    console.print(f"[green]✓[/green] Loaded site: {len(site_racks)} racks")

    # Build network graph and calculate distances
    links = build_network_links(
        topology, site, policy
    )  # [{'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 0.0, 'from': 'spine-1:eth1/1', 'length_bin': 1, 'to': 'tor-west-1:qsfp28-1', 'type': '100G'}, {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 1.0, 'from': 'spine-1:eth1/2', 'length_bin': 2, 'to': 'tor-east-1:qsfp28-1', 'type': '100G'}, {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 1.0, 'from': 'spine-1:eth1/3', 'length_bin': 2, 'to': 'tor-north-1:qsfp28-1', 'type': '100G'}, {'cable_type': 'QSFP28 100G DAC', 'category': 'spine_to_leaf', 'distance_m': 2.0, 'from': 'spine-1:eth1/4', 'length_bin': 3, 'to': 'tor-crypt-1:qsfp28-1', 'type': '100G'}]
    console.print(f"[green]✓[/green] Calculated {len(links)} network links")

    # Aggregate by cable type and length bin
    bom = _aggregate_cable_bom(links, policy, spares_fraction, length_bins_m)
    console.print(f"[green]√[/green] Aggregated BOM into {len(bom)} cable types and {len(links)} length bins")

    # Validate the results
    warnings = _validate_bom(topology, tors, nodes, links, policy)
    if warnings:
        console.print(f"[yellow]⚠[/yellow]  {len(warnings)} validation warnings")
        for warning in warnings:
            console.print(f"  [yellow]•[/yellow] {warning}")
    else:
        console.print(f"[green]✓[/green] Cable BOM generated with no validation warnings.")

    # Export the BOM
    _export_bom(bom, warnings, export_path, export_format, policy)
    console.print(f"[green]✓[/green] Exported BOM to {export_path}")


@spy_trace
def roundtrip_bom(*, bom_path: str, export_path: str, strict: bool = False) -> CableBOMSummary:
    """
    Reads a BOM YAML file, computes a summary, and writes a summary YAML to export_path.
    Raises RuntimeError if the BOM file is missing or invalid.
    """
    from pathlib import Path
    import yaml

    try:
        raw = yaml.safe_load(Path(bom_path).read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to load BOM file '{bom_path}': {e}")
    if not isinstance(raw, dict) or not raw:
        raise RuntimeError(f"BOM file '{bom_path}' is missing or invalid.")
    bom_dict = raw.get("bom") if isinstance(raw.get("bom"), dict) else raw
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
    return CableBOMSummary.from_dict(output)
