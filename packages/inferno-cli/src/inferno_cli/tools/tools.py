import click

from .cabling import cabling
from .cooling import cooling
from .rack import rack


@click.group()
def tools() -> None:
    """Utility commands for rack layout, cooling, and cabling."""
    pass


tools.add_command(cooling)
tools.add_command(cabling)
tools.add_command(rack)
