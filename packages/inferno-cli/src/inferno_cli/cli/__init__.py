import click
from inferno_cli.graph.graph import graph
from inferno_cli.tools.tools import tools


@click.group()
def cli():
    pass


# add cli groups here

cli.add_command(graph)
cli.add_command(tools)
