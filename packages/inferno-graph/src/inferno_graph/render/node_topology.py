import graphviz

from inferno_core.data import racks, nodes
from inferno_core.models import Rack, Node


def render_node_topology(
        racks: list[Rack] = racks,
        nodes: list[Node] = nodes
) -> graphviz.Digraph:
    dot = graphviz.Digraph("inferno_node_topo", format="svg")
    dot.attr("node", shape="rectangle")

    nodes_by_rack = {rack.id: [] for rack in racks}
    for node in nodes:
        nodes_by_rack.setdefault(node.rack_id, []).append(node)

    for rack in racks:
        rack_label = f"{rack.name} ({rack.id})"
        dot.node(rack.id, label=rack_label)
        for node in nodes_by_rack.get(rack.id, []):
            node_label = f"{node.hostname}\\n{node.role}"
            dot.node(node.id, label=node_label, shape="ellipse")
            dot.edge(rack.id, node.id)

    return dot
