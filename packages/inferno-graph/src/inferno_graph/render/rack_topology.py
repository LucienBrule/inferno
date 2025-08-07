import graphviz

from inferno_core.data.circles import circles
from inferno_core.data.racks import racks
from inferno_core.models import Rack
from inferno_core.models.circle import Circle


def render_rack_topology(
        racks: list[Rack] = racks,
        circles: list[Circle] = circles
) -> graphviz.Digraph:
    dot = graphviz.Digraph("inferno_physical_topo", format="svg")
    dot.attr("node", shape="rectangle")

    circle_lookup = {circle.id: circle for circle in circles}

    for rack in racks:
        label_lines = [f"{rack.name} ({rack.id})", f"Location: {rack.location}", "Circles:"]
        for cid in rack.circle_ids:
            role = circle_lookup.get(cid).role if cid in circle_lookup else "unknown"
            label_lines.append(f" - {cid} ({role})")
        dot.node(rack.id, label="\n".join(label_lines))

    return dot
