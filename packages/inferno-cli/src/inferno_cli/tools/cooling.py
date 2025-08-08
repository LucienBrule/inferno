import click
from inferno_tools.cooling import (
    estimate_cooling_by_circuit,
    estimate_cooling_by_load,
    estimate_cooling_measured,
)


@click.group()
def cli() -> None:
    pass


@cli.group()
def cooling() -> None:
    pass


@cooling.command("by-circuit")
@click.option(
    "--headroom",
    type=float,
    default=1.25,
    show_default=True,
    help="Thermal headroom multiplier (e.g., 1.25 for +25%).",
)
@click.option(
    "--ups-efficiency",
    type=float,
    default=0.92,
    show_default=True,
    help="UPS efficiency factor (e.g., 0.92 for 92%).",
)
def cooling_by_circuit(headroom: float, ups_efficiency: float) -> None:
    """Estimate cooling assuming full branch circuit capacity per rack."""
    estimate_cooling_by_circuit(headroom=headroom, ups_efficiency=ups_efficiency)


@cooling.command("by-load")
@click.option(
    "--budget-path",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/power/rack-power-budget.yaml",
    show_default=True,
    help="Path to rack power budget (YAML or MD).",
)
@click.option(
    "--headroom",
    type=float,
    default=1.25,
    show_default=True,
    help="Thermal headroom multiplier (e.g., 1.25 for +25%).",
)
@click.option(
    "--ups-efficiency",
    type=float,
    default=0.92,
    show_default=True,
    help="UPS efficiency factor (e.g., 0.92 for 92%).",
)
def cooling_by_load(budget_path: str, headroom: float, ups_efficiency: float) -> None:
    """Estimate cooling from modeled rack loads (YAML/MD budget)."""
    estimate_cooling_by_load(budget_path=budget_path, headroom=headroom, ups_efficiency=ups_efficiency)


@cooling.command("measured")
def cooling_measured() -> None:
    """Estimate cooling using telemetry (placeholder)."""
    estimate_cooling_measured()
