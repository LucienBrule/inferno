import click
from inferno_graph.render import (
    render_full_topology,
    render_logical_circles,
    render_network_topology,
    render_node_topology,
    render_power_topology,
    render_rack_topology,
)


@click.group()
def graph():
    pass


@graph.command()
def rack():
    render_rack_topology().render("inferno_rack_topology.dot")


@graph.command()
def node():
    render_node_topology().render("inferno_node_topology.dot")


@graph.command()
def logical():
    render_logical_circles().render("inferno_logical_topology.dot")


@graph.command()
def full():
    render_full_topology().render("inferno_full_topology.dot")


@graph.command()
def network():
    render_network_topology().render("inferno_network_topology.dot")


@graph.command()
def power():
    render_power_topology().render("inferno_power_topology.dot")
