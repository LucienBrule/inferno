from inferno_core.data.nodes import load_nodes
from rich.console import Console
from rich.table import Table

console = Console()


def render_rack_layout(rack_id: str, rack_u: int = 42):
    """Render a vertical rack view with chassis assignments."""
    nodes = load_nodes()
    rack_nodes = [n for n in nodes if n.rack_id == rack_id and n.chassis]

    # Sort by U position if present
    rack_nodes.sort(key=lambda n: n.chassis.u_position or 0, reverse=True)

    layout = ["[ ]"] * rack_u  # Top-down (U42 at top, U1 at bottom)

    for node in rack_nodes:
        u_start = node.chassis.u_position
        u_height = node.chassis.height_u
        for i in range(u_height):
            idx = rack_u - u_start - i
            if 0 <= idx < rack_u:
                layout[idx] = "[█]" if i == 0 else "[■]"

    table = Table(title=f"Rack Layout: {rack_id} ({rack_u}U)", box=None, show_header=False)
    table.add_column("U")
    table.add_column("Occupied")

    for i in range(rack_u):
        table.add_row(f"{rack_u - i:02}", layout[i])

    console.print(table)
