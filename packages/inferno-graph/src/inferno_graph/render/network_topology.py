
from inferno_core.data.network import network_topology
import graphviz
from inferno_core.models.network import NetworkTopology


def render_network_topology(
        topology: NetworkTopology = network_topology
) -> graphviz.Digraph:
    """
    Render the leaf–spine network topology:
    - Spine clusters in lightblue.
    - Leaf clusters in lightgreen.
    """
    dot = graphviz.Digraph("inferno_network_topology", format="svg")
    dot.attr(rankdir="LR")  # Fixed: Use keyword argument instead of positional

    # Render spines as clusters
    for spine in topology.spines:
        with dot.subgraph(
                name=f"cluster_{spine.id}",
                graph_attr={
                    "label": f"{spine.model} ({spine.id})",
                    "style": "rounded",
                    "color": "lightblue",
                    "rankdir": "TB",
                },
        ) as c:
            for iface in spine.interfaces:
                node_id = f"{spine.id}@{iface.name}"
                c.node(node_id, label=f"{iface.name}\\n{iface.type}", shape="ellipse")
                # Draw uplink edge to leaf interface
                target = iface.connects_to.replace(":", "@")
                dot.edge(node_id, target, style="solid")

    # Render leafs as clusters
    for leaf in topology.leafs:
        with dot.subgraph(
                name=f"cluster_{leaf.id}",
                graph_attr={
                    "label": f"{leaf.model} ({leaf.id})",
                    "style": "rounded",
                    "color": "lightgreen",
                    "rankdir": "TB",
                },
        ) as c:
            for iface in leaf.interfaces:
                node_id = f"{leaf.id}@{iface.name}"
                c.node(node_id, label=f"{iface.name}\\n{iface.type}", shape="box")
                target = iface.connects_to.replace(":", "@")
                dot.edge(node_id, target, style="solid")

    return dot