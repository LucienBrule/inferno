import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

from inferno_core.data.cabling_policy import _load_yaml, load_cabling_policy
from inferno_tools.cabling import _with_spares, _build_network_links
from inferno_tools.cabling.cabling import console


def _aggregate_cable_bom(
        links: List[Dict[str, Any]], policy: Dict[str, Any], spares_fraction: float, length_bins_m: List[int]
) -> Dict[str, Any]:
    """Aggregate links into BOM by cable type and length bin."""
    bom = {}

    # Count cables by type and length bin
    for link in links:
        cable_type = link["cable_type"]
        length_bin = link["length_bin"]

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


def _validate_bom(
        topology: Dict[str, Any],
        tors: Dict[str, Any],
        nodes: Dict[str, Any],
        links: List[Dict[str, Any]],
        policy: Dict[str, Any],
) -> List[str]:
    """Validate BOM against port capacities and other constraints."""
    warnings = []

    # Check for missing data
    if not topology.get("spines"):
        warnings.append("No spines defined in topology")
    if not topology.get("leafs"):
        warnings.append("No leafs defined in topology")

    # Check link distances against cable type limits
    for link in links:
        distance = link["distance_m"]
        cable_type = link["cable_type"]

        # Basic distance checks
        if distance > 10 and "DAC" in cable_type:
            warnings.append(f"DAC cable selected for {distance:.1f}m link (max recommended: 3m)")
        elif distance > 100:
            warnings.append(f"Very long link: {distance:.1f}m may exceed cable specifications")

    return warnings


def _export_bom(
        bom: Dict[str, Any], warnings: List[str], export_path: str, export_format: str, policy: Dict[str, Any]
) -> None:
    """Export BOM to YAML or CSV format."""
    # Prepare metadata
    metadata = {
        "generated_by": "inferno-cli tools cabling calculate",
        "policy_applied": policy.get("version", "unknown"),
        "spares_fraction": policy.get("defaults", {}).get("spares_fraction", 0.1),
        "slack_factor": policy.get("defaults", {}).get("slack_factor", 1.2),
        "warnings": warnings,
    }

    if export_format.lower() == "csv":
        # Export as CSV
        with open(export_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Cable Type", "Length Bin (m)", "Quantity"])

            for cable_type in sorted(bom.keys()):
                for length_bin in sorted(bom[cable_type].keys()):
                    quantity = bom[cable_type][length_bin]
                    writer.writerow([cable_type, length_bin, quantity])
    else:
        # Export as YAML
        output_data = {"metadata": metadata, "bom": bom}

        with open(export_path, "w") as yamlfile:
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

    console.print(
        f"[green]✓[/green]"
        f" Loaded topology: {len(topology.get('leafs', []))}"
        f" ToRs, {len(topology.get('spines', []))} spines"
    )
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


def roundtrip_bom(*, bom_path: str, export_path: str, strict: bool = False) -> None:
    """
    Reads a BOM YAML file, computes a summary, and writes a summary YAML to export_path.
    Raises RuntimeError if the BOM file is missing or invalid.
    """
    from pathlib import Path

    import yaml

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
