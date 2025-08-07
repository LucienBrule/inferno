
import click
from typing import Optional


@click.group()
def cli() -> None:
    """Inferno cabling tools."""
    pass


@cli.group()
def cabling() -> None:
    """Cabling planning commands."""
    pass


@cabling.command("estimate")
@click.option(
    "--policy",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/network/cabling-policy.yaml",
    show_default=True,
    help="Policy file to control defaults: NIC counts, bins, heuristics.",
)
@click.option(
    "--spares",
    type=float,
    default=0.10,
    show_default=True,
    help="Extra percentage to order as spares (e.g., 0.10 = 10%).",
)
@click.option(
    "--lengths",
    type=str,
    default="1,2,3,5,7,10",
    show_default=True,
    help="Length bins in meters, comma-separated (used for DAC/AOC binning).",
)
def estimate(policy: str, spares: float, lengths: str) -> None:
    """Quick heuristic counts by class (no site geometry required)."""
    try:
        from inferno_tools.cabling import estimate_cabling_heuristic
        bins = [int(x) for x in lengths.split(",") if x.strip()]
        estimate_cabling_heuristic(
            policy_path=policy,
            spares_fraction=spares,
            length_bins_m=bins,
        )
    except Exception as e:
        click.echo(f"[estimator] Not implemented yet: {e}")


@cabling.command("calculate")
@click.option(
    "--topology",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/network/topology.yaml",
    show_default=True,
    help="Path to network topology YAML (leaf/spine, uplinks, WAN).",
)
@click.option(
    "--nodes",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/naming/nodes.yaml",
    show_default=True,
    help="Path to nodes YAML (rack placement, NICs).",
)
@click.option(
    "--tors",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/network/tors.yaml",
    show_default=True,
    help="Path to ToR inventory YAML (port capacities).",
)
@click.option(
    "--site",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/site.yaml",
    show_default=False,
    help="Optional site geometry YAML for precise lengths (grid positions, U placements).",
)
@click.option(
    "--policy",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/network/cabling-policy.yaml",
    show_default=True,
    help="Cabling policy YAML (bins/media rules, defaults).",
)
@click.option(
    "--spares",
    type=float,
    default=0.10,
    show_default=True,
    help="Extra percentage per line item (e.g., 0.10 = 10%).",
)
@click.option(
    "--lengths",
    type=str,
    default="1,2,3,5,7,10",
    show_default=True,
    help="Length bins in meters, comma-separated.",
)
@click.option(
    "--export",
    type=click.Path(path_type=str, dir_okay=False),
    default="outputs/cabling_bom.yaml",
    show_default=True,
    help="Write BOM to this path (YAML/CSV).",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["yaml", "csv"], case_sensitive=False),
    default="yaml",
    show_default=True,
    help="Export format.",
)
def calculate(
    topology: str,
    nodes: str,
    tors: str,
    site: Optional[str],
    policy: str,
    spares: float,
    lengths: str,
    export: str,
    fmt: str,
) -> None:
    """Deterministic BOM by reading manifests and policy."""
    try:
        from inferno_tools.cabling import calculate_cabling_bom
        bins = [int(x) for x in lengths.split(",") if x.strip()]
        calculate_cabling_bom(
            topology_path=topology,
            nodes_path=nodes,
            tors_path=tors,
            site_path=site,
            policy_path=policy,
            spares_fraction=spares,
            length_bins_m=bins,
            export_path=export,
            export_format=fmt.lower(),
        )
    except Exception as e:
        click.echo(f"[calculate] Not implemented yet: {e}")


@cabling.command("validate")
@click.option(
    "--topology",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/network/topology.yaml",
    show_default=True,
    help="Path to network topology YAML.",
)
@click.option(
    "--nodes",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/naming/nodes.yaml",
    show_default=True,
    help="Path to nodes YAML.",
)
@click.option(
    "--tors",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/network/tors.yaml",
    show_default=True,
    help="Path to ToR inventory YAML.",
)
def validate(topology: str, nodes: str, tors: str) -> None:
    """Sanity-check manifests vs port budgets and NIC declarations."""
    try:
        from inferno_tools.cabling import validate_cabling
        validate_cabling(topology_path=topology, nodes_path=nodes, tors_path=tors)
    except Exception as e:
        click.echo(f"[validate] Not implemented yet: {e}")


@cabling.command("visualize")
@click.option(
    "--site",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/site.yaml",
    show_default=False,
    help="Optional site geometry YAML.",
)
@click.option(
    "--output",
    type=click.Path(path_type=str, dir_okay=False),
    default="outputs/cabling.svg",
    show_default=True,
    help="Write a quick SVG sketch of racks and link classes.",
)
def visualize(site: Optional[str], output: str) -> None:
    """Render a simple SVG of rack grid and link classes (optional)."""
    try:
        from inferno_tools.cabling import visualize_cabling
        visualize_cabling(site_path=site, output_path=output)
    except Exception as e:
        click.echo(f"[visualize] Not implemented yet: {e}")
