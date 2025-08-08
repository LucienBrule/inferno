from dataclasses import dataclass
from pathlib import Path

from inferno_core.codebase.deprecation import deprecated


@dataclass(frozen=True)
class CablingSummary:
    leaf_to_node: int
    leaf_to_spine: int
    mgmt_cat6a: int
    wan_cat6a: int



@deprecated(
    message="inferno_tools.cabling.cabling._load_yaml is deprecated. Use inferno_core.data.cabling.load_cabling_policy instead.",
    since="0.1.0",
    alternative="inferno_core.data.cabling.load_cabling_policy",
    remove_in="0.2.0",
)
def _load_yaml(path: str) -> dict:
    try:
        import yaml  # local import to avoid hard dep elsewhere

        p = Path(path)
        if not p.exists():
            return {}
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


@deprecated(
    message="inferno_tools.cabling.cabling.load_cabling_policy is deprecated.",
    since="0.1.0",
    alternative="inferno_core.data.cabling.load_cabling_policy",
    remove_in="0.2.0",
    verbose=True,
    print_args=True,
    print_stack=True
)
def load_cabling_policy(path: str) -> dict:
    """Return a normalized policy dict with safe defaults if missing."""
    data = _load_yaml(path)
    defaults = data.get("defaults") or {}
    media = data.get("media_rules") or {}

    # Safe defaults
    nodes_25g_per_node = int(defaults.get("nodes_25g_per_node", 1))
    mgmt_rj45_per_node = int(defaults.get("mgmt_rj45_per_node", 1))
    wan_cat6a_count = int(defaults.get("wan_cat6a_count", 2))
    tor_uplink_qsfp28_per_tor = int(defaults.get("tor_uplink_qsfp28_per_tor", 2))
    spares_fraction = float(defaults.get("spares_fraction", 0.10))

    site = data.get("site-defaults") or {}
    num_racks = int(site.get("num_racks", 4))
    nodes_per_rack = int(site.get("nodes_per_rack", 4))
    uplinks_per_rack = int(site.get("uplinks_per_rack", 2))
    mgmt_rj45_site = int(site.get("mgmt_rj45_per_node", mgmt_rj45_per_node))
    wan_cat6a_site = int(site.get("wan_cat6a", 2))

    def _bins(key: str, label_key: str | None = None) -> list[int]:
        m = media.get(key) or {}
        bins = m.get("bins_m") or [1, 2, 3, 5, 7, 10]
        try:
            return [int(x) for x in bins]
        except Exception:
            return [1, 2, 3, 5, 7, 10]

    return {
        "defaults": {
            "nodes_25g_per_node": nodes_25g_per_node,
            "mgmt_rj45_per_node": mgmt_rj45_per_node,
            "wan_cat6a_count": wan_cat6a_count,
            "tor_uplink_qsfp28_per_tor": tor_uplink_qsfp28_per_tor,
            "spares_fraction": spares_fraction,
        },
        "site_defaults": {
            "num_racks": num_racks,
            "nodes_per_rack": nodes_per_rack,
            "uplinks_per_rack": uplinks_per_rack,
            "mgmt_rj45_per_node": mgmt_rj45_site,
            "wan_cat6a": wan_cat6a_site,
        },
        "bins": {
            "sfp28": _bins("sfp28_25g"),
            "qsfp28": _bins("qsfp28_100g"),
            "rj45": _bins("rj45_cat6a"),
        },
    }
