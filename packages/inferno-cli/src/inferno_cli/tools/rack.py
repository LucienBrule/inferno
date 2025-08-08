import click
from inferno_tools.layout import render_rack_layout


@click.group()
def cli() -> None:
    pass


@cli.group()
def rack() -> None:
    pass


@rack.command()
@click.option("--rack-id", type=int, default=1, show_default=True, help="Rack identifier to render.")
@click.option("--rack-u", type=int, default=42, show_default=True, help="Rack height in U.")
def layout(rack_id: int, rack_u: int) -> None:
    """Render a front elevation layout for a rack."""
    render_rack_layout(rack_id=rack_id, rack_u=rack_u)
