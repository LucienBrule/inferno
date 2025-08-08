import graphviz
from inferno_core.data.circles import circles
from inferno_core.data.nodes import nodes
from inferno_core.data.racks import racks
from inferno_core.models import Node, Rack
from inferno_core.models.circle import Circle


def _render_rack_cluster(rack: Rack, circles: list[Circle], nodes: list[Node]) -> graphviz.Digraph:
    circle_lookup = {c.id: c for c in circles}
    nodes_by_circle = {}
    for node in nodes:
        nodes_by_circle.setdefault(node.circle_id, []).append(node)

    c = graphviz.Digraph(name=f"cluster_{rack.id}")
    c.attr(label=f"{rack.name}\\n({rack.id})", style="rounded", color="black", rankdir="TB")

    # Enforce vertical ordering of localized circle nodes
    for idx in range(len(rack.circle_ids) - 1):
        cid_from = rack.circle_ids[idx]
        cid_to = rack.circle_ids[idx + 1]
        node_from = f"{cid_from}@{rack.id}"
        node_to = f"{cid_to}@{rack.id}"
        c.edge(node_from, node_to, style="invis")

    for cid in rack.circle_ids:
        circle = circle_lookup.get(cid)
        if circle and rack.id in circle.rack_ids:
            circle_node_id = f"{circle.id}@{rack.id}"
            c.node(
                circle_node_id,
                label=f"{circle.name}\\nCircle {circle.circle}",
                shape="ellipse",
                style="filled",
                fillcolor="white",
            )
            # For each node in this circle, if it belongs to this rack, add node and edge.
            has_local_nodes = False
            for node in nodes_by_circle.get(cid, []):
                if node.rack_id == rack.id:
                    has_local_nodes = True
                    c.node(node.id, label=f"{node.hostname}\\n{node.role}", shape="box")
                    c.edge(circle_node_id, node.id)
            # If there are no nodes in this rack for this circle, still show an empty placeholder edge
            if not has_local_nodes:
                empty_id = f"{cid}-{rack.id}-empty"
                c.node(empty_id, label="", shape="point", width="0", height="0", style="invis")
                c.edge(circle_node_id, empty_id, style="invis")

    return c


def _render_logical_circle_links(circles: list[Circle], dot: graphviz.Digraph) -> None:
    sorted_circles = sorted(circles, key=lambda c: c.circle)
    for i in range(1, len(sorted_circles)):
        prev_id = sorted_circles[i - 1].id
        curr_id = sorted_circles[i].id
        dot.edge(prev_id, curr_id, style="dashed", color="grey")


def render_full_topology(
    racks: list[Rack] = racks, circles: list[Circle] = circles, nodes: list[Node] = nodes
) -> graphviz.Digraph:
    dot = graphviz.Digraph("inferno_full_topo", format="svg")
    dot.attr("node", shape="plaintext")

    for rack in racks:
        cluster = _render_rack_cluster(rack, circles, nodes)
        dot.subgraph(cluster)

    # _render_logical_circle_links(circles, dot)

    # Grid layout for racks using invisible anchors
    rack_ids = [r.id for r in racks]
    num_cols = 2  # define number of columns in grid

    # create invisible anchor nodes for each rack cluster
    for rid in rack_ids:
        dot.node(f"{rid}_anchor", label="", shape="point", width="0", height="0", style="invis")

    # group anchors by row to enforce grid alignment
    for i in range(0, len(rack_ids), num_cols):
        row = rack_ids[i : i + num_cols]
        with dot.subgraph() as s:
            s.attr(rank="same")
            for rid in row:
                s.node(f"{rid}_anchor")

    return dot
