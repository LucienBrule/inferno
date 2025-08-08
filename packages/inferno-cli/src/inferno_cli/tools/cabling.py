from typing import Optional

import click


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
@click.option(
    "--policy",
    type=click.Path(path_type=str, dir_okay=False, exists=False),
    default="doctrine/network/cabling-policy.yaml",
    show_default=True,
    help="Path to cabling policy YAML.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as failures (exit code 2).",
)
@click.option(
    "--export",
    type=click.Path(path_type=str, dir_okay=False),
    help="Export validation findings to YAML file.",
)
def validate(topology: str, nodes: str, tors: str, policy: str, strict: bool, export: Optional[str]) -> None:
    """Sanity-check manifests vs port budgets and NIC declarations."""
    import sys

    import yaml
    from rich.console import Console
    from rich.table import Table

    console = Console()

    try:
        from inferno_core.validation.cabling import run_cabling_validation

        console.print("\n[bold cyan]Cabling Validation[/bold cyan]")

        # Run comprehensive validation including policy checks
        report = run_cabling_validation(policy_path=policy)

        # Export findings if requested
        if export:
            with open(export, "w") as f:
                yaml.dump(report.model_dump(), f, default_flow_style=False, sort_keys=True)
            console.print(f"[green]✓[/green] Findings exported to {export}")

        # Print summary table
        table = Table(title="Validation Summary")
        table.add_column("Severity", style="cyan")
        table.add_column("Count", justify="right")

        table.add_row("PASS", str(report.summary.get("pass", 0)), style="green")
        table.add_row("INFO", str(report.summary.get("info", 0)), style="blue")
        table.add_row("WARN", str(report.summary.get("warn", 0)), style="yellow")
        table.add_row("FAIL", str(report.summary.get("fail", 0)), style="red")

        console.print(table)

        # Print detailed findings grouped by section
        if report.findings:
            console.print("\n[bold]Policy Validation:[/bold]")
            policy_findings = [f for f in report.findings if f.code.startswith("POLICY_")]

            if policy_findings:
                for finding in policy_findings:
                    severity_color = {"FAIL": "red", "WARN": "yellow", "INFO": "blue"}.get(finding.severity, "white")

                    console.print(
                        f"[{severity_color}]{finding.severity}[/{severity_color}] {finding.code}: {finding.message}"
                    )
            else:
                console.print("[green]✓ Policy validation passed[/green]")

            # Print other findings
            other_findings = [f for f in report.findings if not f.code.startswith("POLICY_")]
            if other_findings:
                console.print("\n[bold]Topology Validation:[/bold]")
                for finding in other_findings:
                    severity_color = {"FAIL": "red", "WARN": "yellow", "INFO": "blue"}.get(finding.severity, "white")

                    console.print(
                        f"[{severity_color}]{finding.severity}[/{severity_color}] {finding.code}: {finding.message}"
                    )
        else:
            console.print("\n[green]✓ All validation checks passed[/green]")

        # Determine exit code based on validation rules
        fail_count = report.summary.get("fail", 0)
        warn_count = report.summary.get("warn", 0)

        if fail_count > 0:
            console.print(f"\n[red]✗[/red] Validation failed with {fail_count} errors")
            sys.exit(1)
        elif strict and warn_count > 0:
            console.print(f"\n[yellow]⚠[/yellow] Validation completed with {warn_count} warnings (strict mode)")
            sys.exit(2)
        else:
            console.print("\n[green]✓[/green] Validation completed successfully")
            sys.exit(0)

    except Exception as e:
        console.print(f"[red]Error during validation: {e}[/red]")
        sys.exit(1)


@cabling.command("cross-validate")
@click.option(
    "--bom",
    type=click.Path(path_type=str, dir_okay=False, exists=True),
    default="outputs/cabling_bom.yaml",
    show_default=True,
    help="Path to BOM YAML file to validate against topology/policy.",
)
@click.option(
    "--export",
    type=click.Path(path_type=str, dir_okay=False),
    default="outputs/cabling_reconciliation.yaml",
    show_default=True,
    help="Write reconciliation report to this path.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as failures (exit code 2).",
)
def cross_validate(bom: str, export: str, strict: bool) -> None:
    """Cross-validate BOM against topology/policy intent."""
    import sys

    import yaml
    from rich.console import Console
    from rich.table import Table

    console = Console()

    try:
        from inferno_tools.cabling.cross_validate import cross_validate_bom

        console.print("\n[bold cyan]Cabling Cross-Validation[/bold cyan]")

        # Run cross-validation
        report = cross_validate_bom(bom_path=bom)

        # Export report
        with open(export, "w") as f:
            yaml.dump(report.model_dump(), f, default_flow_style=False, sort_keys=True)

        # Print summary table
        table = Table(title="Cross-Validation Summary")
        table.add_column("Check", style="cyan")
        table.add_column("Count", justify="right")

        table.add_row("Missing Links", str(report.summary["missing"]))
        table.add_row("Phantom Items", str(report.summary["phantom"]))
        table.add_row("Media Mismatches", str(report.summary["mismatched_media"]))
        table.add_row("Bin Mismatches", str(report.summary["mismatched_bin"]))
        table.add_row("Count Mismatches", str(report.summary["count_mismatch"]))

        console.print(table)

        # Print detailed findings
        if report.findings:
            console.print("\n[bold]Detailed Findings:[/bold]")
            for finding in report.findings:
                severity_color = {"FAIL": "red", "WARN": "yellow", "INFO": "blue"}.get(finding.severity, "white")

                console.print(
                    f"[{severity_color}]{finding.severity}[/{severity_color}] {finding.code}: {finding.message}"
                )
        else:
            console.print("\n[green]✓ No issues found - BOM matches topology/policy intent[/green]")

        console.print(f"\n[green]✓[/green] Report exported to {export}")

        # Determine exit code
        fail_count = len([f for f in report.findings if f.severity == "FAIL"])
        warn_count = len([f for f in report.findings if f.severity == "WARN"])

        if fail_count > 0:
            sys.exit(1)
        elif strict and warn_count > 0:
            sys.exit(2)
        else:
            sys.exit(0)

    except Exception as e:
        console.print(f"[red]Error during cross-validation: {e}[/red]")
        sys.exit(1)


@cabling.command("roundtrip")
@click.option(
    "--bom",
    type=click.Path(path_type=str, dir_okay=False, exists=True),
    default="outputs/cabling_bom.yaml",
    show_default=True,
    help="Path to BOM YAML file to process.",
)
@click.option(
    "--export",
    type=click.Path(path_type=str, dir_okay=False),
    default="outputs/cabling_roundtrip.yaml",
    show_default=True,
    help="Write roundtrip report to this path.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as failures (exit code 2).",
)
def roundtrip(bom: str, export: str, strict: bool) -> None:
    """Perform roundtrip processing on BOM."""
    import sys

    from rich.console import Console

    console = Console()
    console.print("\n[bold cyan]Cabling Roundtrip[/bold cyan]")

    try:
        from inferno_tools.cabling import roundtrip_bom

        roundtrip_bom(bom_path=bom, export_path=export, strict=strict)
        console.print(f"\n[green]✓[/green] Roundtrip report exported to {export}")
    except ImportError as e:
        console.print(f"[roundtrip] Not implemented yet: {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[roundtrip] Not implemented yet: {e}")
        sys.exit(1)


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
