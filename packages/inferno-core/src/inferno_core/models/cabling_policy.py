# inferno_core/models/cabling_policy.py
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, AliasChoices, ConfigDict

# ---- leaf structs ----

class MediaLabels(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dac: Optional[str] = None
    aoc: Optional[str] = None
    fiber: Optional[str] = None
    # RJ45 policy uses a single "label"
    label: Optional[str] = None

class MediaRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dac_max_m: Optional[float] = None
    bins_m: List[int] = Field(default_factory=lambda: [1, 2, 3, 5, 7, 10])
    labels: Optional[MediaLabels] = None

class PolicyDefaults(BaseModel):
    model_config = ConfigDict(extra="ignore")
    nodes_25g_per_node: int = 1
    mgmt_rj45_per_node: int = 1
    tor_uplink_qsfp28_per_tor: int = 2
    spares_fraction: float = 0.10
    # this existed in your legacy normalizer; keep it optional for compatibility
    wan_cat6a_count: Optional[int] = None

class SiteDefaults(BaseModel):
    model_config = ConfigDict(extra="ignore")
    num_racks: int = 4
    nodes_per_rack: int = 4
    uplinks_per_rack: int = 2
    mgmt_rj45_per_node: int = 1
    wan_cat6a: int = 2

class Redundancy(BaseModel):
    model_config = ConfigDict(extra="ignore")
    node_dual_homing: bool = False
    tor_uplinks_min: int = 2

class Oversubscription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    max_leaf_to_spine_ratio: float = 4.0
    warn_margin_fraction: float = 0.25

class Heuristics(BaseModel):
    model_config = ConfigDict(extra="ignore")
    same_rack_leaf_to_node_m: float = 2.0
    adjacent_rack_leaf_to_spine_m: float = 10.0
    non_adjacent_rack_leaf_to_spine_m: float = 30.0
    slack_factor: float = 1.2
    tile_m: float = 1.0

# ---- root policy ----

class CablingPolicy(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    defaults: PolicyDefaults = Field(default_factory=PolicyDefaults)

    # Accept both `site_defaults` and `site-defaults` in YAML
    site_defaults: SiteDefaults = Field(
        default_factory=SiteDefaults,
        validation_alias=AliasChoices("site_defaults", "site-defaults"),
    )

    media_rules: Dict[str, MediaRule] = Field(default_factory=dict)
    redundancy: Optional[Redundancy] = None
    oversubscription: Optional[Oversubscription] = None
    heuristics: Optional[Heuristics] = None

    # Optional bucket for line rates — leave flexible (keys like "SFP+" are awkward as attrs)
    line_rates: Dict[str, int] | None = None

    # Convenience accessors matching what your estimator expects today
    @property
    def bins(self) -> Dict[str, List[int]]:
        mr = self.media_rules or {}
        return {
            "sfp28": (mr.get("sfp28_25g") or MediaRule()).bins_m,
            "qsfp28": (mr.get("qsfp28_100g") or MediaRule()).bins_m,
            "rj45": (mr.get("rj45_cat6a") or MediaRule()).bins_m,
        }