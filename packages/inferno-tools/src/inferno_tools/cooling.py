from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import yaml
from inferno_core.data.power import load_feeds
from rich.console import Console

console = Console()


# ----------------------------
# Constants
# ----------------------------

SAFETY_FACTOR = 1.25
UPS_EFFICIENCY = 0.92
CONTINUOUS_LOAD_FACTOR = 0.80
DEFAULT_VOLTAGE = 240.0
DEFAULT_AMPERAGE = 30.0
DEFAULT_BUDGET_PATH = Path("doctrine/power/rack-power-budget.yaml")

# ----------------------------
# Unit conversions
# ----------------------------


def watts_to_btu_per_hr(watts: float) -> float:
    """Convert watts to BTU/hr (1 watt = 3.412 BTU/hr)."""
    return watts * 3.412


def btu_per_hr_to_tons(btu_hr: float) -> float:
    """Convert BTU/hr to cooling tons (1 ton = 12,000 BTU/hr)."""
    return btu_hr / 12000.0


# ----------------------------
# Public API
# ----------------------------


def estimate_cooling_by_circuit(
    *,
    headroom: float = SAFETY_FACTOR,
    ups_efficiency: float = UPS_EFFICIENCY,
    voltage: float = DEFAULT_VOLTAGE,
    amperage: float = DEFAULT_AMPERAGE,
    continuous_factor: float = CONTINUOUS_LOAD_FACTOR,
) -> None:
    """Estimate cooling per rack and site total using branch circuit capacity assumptions."""
    feeds = load_feeds()

    results: List[Tuple[str, float, float]] = []  # (label, BTU/hr, tons)

    for feed in feeds:
        # 80% continuous load rule
        continuous_kw = voltage * amperage * continuous_factor / 1000.0
        # Account for UPS inefficiency (source watts actually drawn to supply that load)
        actual_kw = continuous_kw / ups_efficiency
        btu_hr = watts_to_btu_per_hr(actual_kw * 1000.0) * headroom
        results.append((feed.id, btu_hr, btu_per_hr_to_tons(btu_hr)))

    total_btu = sum(b for _, b, _ in results)
    total_tons = sum(t for _, _, t in results)

    console.print("\n[bold cyan]Inferno Cooling Estimator[/bold cyan]\n")
    for rack_id, btu, tons in results:
        console.print(
            f"[green]{rack_id}[/green]: [yellow]{int(btu):,} BTU/hr[/yellow] → [magenta]{tons:.1f} tons[/magenta]"
        )

    console.print(
        f"\n[bold]Total:[/bold] {int(total_btu):,} BTU/hr → [bold magenta]{total_tons:.1f} tons[/bold magenta]\n"
    )

    if headroom == 1.0:
        headroom_note = ""
    else:
        pct = (headroom - 1) * 100
        headroom_note = f", {pct:+.0f}% headroom"
    footnote = (
        f"Note: by-circuit = 240V/30A @ 80% load, 92% UPS eff.{headroom_note}.\n"
        f"      by-load = modeled rack watts from doctrine/power/rack-power-budget.yaml"
        + (f" ({pct:+.0f}% headroom)" if headroom != 1.0 else "")
        + "."
    )
    console.print(f"[dim]{footnote}[/dim]")


def estimate_cooling_by_load(
    budget_path: Path | str = DEFAULT_BUDGET_PATH,
    *,
    headroom: float = SAFETY_FACTOR,
    ups_efficiency: float = UPS_EFFICIENCY,
) -> None:
    """Estimate cooling per rack and site total by parsing modeled rack loads from YAML."""
    feeds = load_feeds()

    yaml_path = Path(budget_path) if isinstance(budget_path, str) else budget_path
    if not yaml_path.exists():
        console.print(f"[yellow]Budget YAML not found at {yaml_path}; falling back to by-circuit.[/yellow]")
        estimate_cooling_by_circuit()
        return

    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        console.print(f"[yellow]Error reading {yaml_path}: {e}; falling back to by-circuit.[/yellow]")
        estimate_cooling_by_circuit()
        return

    racks = data.get("racks", [])
    if not isinstance(racks, list) or not racks:
        console.print(f"[yellow]No racks found in {yaml_path}; falling back to by-circuit.[/yellow]")
        estimate_cooling_by_circuit()
        return

    # Map feed_id -> modeled watts
    loads: Dict[str, float] = {}
    for r in racks:
        feed_id = r.get("feed_id")
        watts = r.get("estimated_draw_w")
        if isinstance(feed_id, str) and isinstance(watts, int | float):
            loads[feed_id] = float(watts)

    if not loads:
        console.print(f"[yellow]No per-rack loads present in {yaml_path}; falling back to by-circuit.[/yellow]")
        estimate_cooling_by_circuit()
        return

    results: List[Tuple[str, float, float]] = []
    for feed in feeds:
        watts = float(loads.get(feed.id, 0.0))
        btu_hr = watts_to_btu_per_hr(watts) * headroom
        results.append((feed.id, btu_hr, btu_per_hr_to_tons(btu_hr)))

    total_btu = sum(b for _, b, _ in results)
    total_tons = sum(t for _, _, t in results)

    console.print("\n[bold cyan]Inferno Cooling Estimator[/bold cyan]\n")
    for rack_id, btu, tons in results:
        console.print(
            f"[green]{rack_id}[/green]: [yellow]{int(btu):,} BTU/hr[/yellow] → [magenta]{tons:.1f} tons[/magenta]"
        )

    console.print(
        f"\n[bold]Total:[/bold] {int(total_btu):,} BTU/hr → [bold magenta]{total_tons:.1f} tons[/bold magenta]\n"
    )

    if headroom == 1.0:
        headroom_note = ""
    else:
        pct = (headroom - 1) * 100
        headroom_note = f", {pct:+.0f}% headroom"
    footnote = (
        f"Note: by-circuit = 240V/30A @ 80% load, 92% UPS eff.{headroom_note}.\n"
        f"      by-load = modeled rack watts from doctrine/power/rack-power-budget.yaml"
        + (f" ({pct:+.0f}% headroom)" if headroom != 1.0 else "")
        + "."
    )
    console.print(f"[dim]{footnote}[/dim]")


def estimate_cooling_measured() -> None:
    """Placeholder for future SNMP/Redfish integration."""
    console.print("[yellow]Measured mode not yet implemented — planned SNMP/Redfish integration.[/yellow]")


def estimate_cooling_per_rack(
    mode: str = "by-circuit",
    budget_path: Path | str = DEFAULT_BUDGET_PATH,
) -> None:
    """Estimate cooling per rack and site total.

    Modes:
      - by-circuit: Use branch circuit capacity assumptions (current default behavior).
      - by-load: Parse modeled rack loads from doctrine/power/rack-power-budget.yaml.
      - measured: Placeholder for future SNMP/Redfish integration.
    """
    if mode == "by-circuit":
        estimate_cooling_by_circuit()
    elif mode == "by-load":
        estimate_cooling_by_load(budget_path)
    elif mode == "measured":
        estimate_cooling_measured()
    else:
        console.print(f"[red]Unknown mode: {mode}[/red]")
        return
