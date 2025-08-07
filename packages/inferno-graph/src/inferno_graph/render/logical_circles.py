import graphviz

from inferno_core.data import circles
from inferno_core.models.circle import Circle


def render_logical_circles(circles: list[Circle] = circles) -> graphviz.Digraph:
    dot = graphviz.Digraph("inferno_logical", format="svg")
    dot.attr("node", shape="circle")

    sorted_circles = sorted(circles, key=lambda c: c.circle)
    for i, circle in enumerate(sorted_circles):
        label = f"{circle.name}\\n(Circle {circle.circle})"
        dot.node(circle.id, label=label)
        if i > 0:
            dot.edge(sorted_circles[i - 1].id, circle.id)

    return dot
