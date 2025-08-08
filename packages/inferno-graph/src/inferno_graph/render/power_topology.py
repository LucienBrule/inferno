import graphviz
from inferno_core.data.power import feeds, pdus, ups
from inferno_core.models.power import PDU, UPS, PowerFeed


def render_power_topology(
    feeds: list[PowerFeed] = feeds, ups_list: list[UPS] = ups, pdus_list: list[PDU] = pdus
) -> graphviz.Digraph:
    """
    Render the power topology for each rack:
    - The main power feed (L6-30R) supplies the UPS and the direct PDU (feed B).
    - The UPS output then feeds the UPS-backed PDU (feed A).
    """
    dot = graphviz.Digraph("inferno_power_topology", format="svg")
    dot.attr(rankdir="TB")

    for feed in feeds:
        # Determine rack for this feed (assume one-to-one)
        rack_id = feed.rack_ids[0] if feed.rack_ids else "unknown"
        cluster_name = f"cluster_{rack_id}"
        with dot.subgraph(name=cluster_name) as c:
            c.attr(label=f"Rack: {rack_id}", style="rounded", color="gray", rankdir="LR")

            # Power feed node
            feed_node = f"feed@{feed.id}"
            c.node(
                feed_node,
                label=f"{feed.id}\\n{feed.circuit_type}\\n{feed.voltage}V/{feed.amperage}A",
                shape="box",
                style="filled",
                fillcolor="orange",
            )

            # UPS node (feed A source)
            ups = next((u for u in ups_list if u.rack_id == rack_id), None)
            if ups:
                ups_node = f"ups@{ups.id}"
                c.node(
                    ups_node, label=f"{ups.id}\\n{ups.model}", shape="ellipse", style="filled", fillcolor="lightblue"
                )
                # Edge: feed -> UPS
                c.edge(feed_node, ups_node)

            # PDU nodes
            for pdu in [p for p in pdus_list if p.rack_id == rack_id]:
                pdu_node = f"pdu@{pdu.id}"
                c.node(
                    pdu_node,
                    label=f"{pdu.id}\\nFeed {pdu.feed}",
                    shape="ellipse",
                    style="filled",
                    fillcolor="lightgreen",
                )
                if pdu.feed.upper() == "A" and ups:
                    # PDU-A is fed by the UPS
                    c.edge(ups_node, pdu_node)
                else:
                    # PDU-B is fed directly from the main feed
                    c.edge(feed_node, pdu_node)

    return dot
