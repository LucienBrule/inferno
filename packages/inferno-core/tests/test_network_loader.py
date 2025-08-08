"""
Unit tests for network_loader module.

Tests cover happy path, error cases, type coercion, and missing files
as specified in TASK.cabling.loader.md.
"""

import pytest
from inferno_core.data.network_loader import (
    load_nodes,
    load_site,
    load_topology,
    load_tors,
)
from inferno_core.models.records import (
    NicRec,
    NodeRec,
    SiteRec,
    SpineRec,
    TopologyRec,
    TorRec,
)


class TestLoadTopology:
    """Test topology loader."""

    def test_happy_path(self, tmp_path):
        """Test successful topology loading."""
        topology_yaml = """
spine:
  id: spine-1
  model: mellanox-sn2700
  ports:
    qsfp28_total: 32
racks:
  - rack_id: rack-1
    tor_id: tor-1
    uplinks_qsfp28: 2
  - rack_id: rack-2
    tor_id: tor-2
    uplinks_qsfp28: 2
wan:
  uplinks_cat6a: 2
"""
        topology_file = tmp_path / "topology.yaml"
        topology_file.write_text(topology_yaml)

        result = load_topology(topology_file)

        assert isinstance(result, TopologyRec)
        assert result.spine.id == "spine-1"
        assert result.spine.model == "mellanox-sn2700"
        assert result.spine.ports.qsfp28_total == 32
        assert len(result.racks) == 2
        assert result.racks[0].rack_id == "rack-1"
        assert result.racks[0].tor_id == "tor-1"
        assert result.racks[0].uplinks_qsfp28 == 2
        assert result.wan.uplinks_cat6a == 2

    def test_type_coercion(self, tmp_path):
        """Test that string numbers are coerced to integers."""
        topology_yaml = """
spine:
  id: spine-1
  model: mellanox-sn2700
  ports:
    qsfp28_total: "32"
racks:
  - rack_id: rack-1
    tor_id: tor-1
    uplinks_qsfp28: "2"
wan:
  uplinks_cat6a: "2"
"""
        topology_file = tmp_path / "topology.yaml"
        topology_file.write_text(topology_yaml)

        result = load_topology(topology_file)

        assert result.spine.ports.qsfp28_total == 32
        assert result.racks[0].uplinks_qsfp28 == 2
        assert result.wan.uplinks_cat6a == 2

    def test_missing_required_field(self, tmp_path):
        """Test error when required field is missing."""
        topology_yaml = """
spine:
  model: mellanox-sn2700
  ports:
    qsfp28_total: 32
racks:
  - rack_id: rack-1
    tor_id: tor-1
    uplinks_qsfp28: 2
wan:
  uplinks_cat6a: 2
"""
        topology_file = tmp_path / "topology.yaml"
        topology_file.write_text(topology_yaml)

        with pytest.raises(ValueError):
            load_topology(topology_file)

    def test_file_not_found(self):
        """Test error when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_topology("nonexistent.yaml")

    def test_invalid_yaml(self, tmp_path):
        """Test error with malformed YAML."""
        topology_file = tmp_path / "topology.yaml"
        topology_file.write_text("invalid: yaml: content: [")

        with pytest.raises(ValueError):
            load_topology(topology_file)


class TestLoadTors:
    """Test ToRs loader."""

    def test_happy_path_with_spine(self, tmp_path):
        """Test successful ToRs loading with spine."""
        tors_yaml = """
tors:
  - id: tor-1
    rack_id: rack-1
    model: sn2410
    ports:
      sfp28_total: 48
      qsfp28_total: 8
  - id: tor-2
    rack_id: rack-2
    model: sn2410
    ports:
      sfp28_total: 48
      qsfp28_total: 8
spine:
  id: spine-1
  model: sn2700
  ports:
    qsfp28_total: 32
"""
        tors_file = tmp_path / "tors.yaml"
        tors_file.write_text(tors_yaml)

        tors, spine = load_tors(tors_file)

        assert len(tors) == 2
        assert isinstance(tors[0], TorRec)
        assert tors[0].id == "tor-1"
        assert tors[0].rack_id == "rack-1"
        assert tors[0].model == "sn2410"
        assert tors[0].ports.sfp28_total == 48
        assert tors[0].ports.qsfp28_total == 8

        assert spine is not None
        assert isinstance(spine, SpineRec)
        assert spine.id == "spine-1"
        assert spine.model == "sn2700"
        assert spine.ports.qsfp28_total == 32

    def test_happy_path_without_spine(self, tmp_path):
        """Test successful ToRs loading without spine."""
        tors_yaml = """
tors:
  - id: tor-1
    rack_id: rack-1
    model: sn2410
    ports:
      sfp28_total: 48
      qsfp28_total: 8
"""
        tors_file = tmp_path / "tors.yaml"
        tors_file.write_text(tors_yaml)

        tors, spine = load_tors(tors_file)

        assert len(tors) == 1
        assert spine is None

    def test_type_coercion(self, tmp_path):
        """Test that string numbers are coerced to integers."""
        tors_yaml = """
tors:
  - id: tor-1
    rack_id: rack-1
    model: sn2410
    ports:
      sfp28_total: "48"
      qsfp28_total: "8"
spine:
  id: spine-1
  model: sn2700
  ports:
    qsfp28_total: "32"
"""
        tors_file = tmp_path / "tors.yaml"
        tors_file.write_text(tors_yaml)

        tors, spine = load_tors(tors_file)

        assert tors[0].ports.sfp28_total == 48
        assert tors[0].ports.qsfp28_total == 8
        assert spine.ports.qsfp28_total == 32

    def test_wrong_structure(self, tmp_path):
        """Test error when file has wrong structure (list instead of dict)."""
        tors_yaml = """
- id: tor-1
  rack_id: rack-1
  model: sn2410
"""
        tors_file = tmp_path / "tors.yaml"
        tors_file.write_text(tors_yaml)

        with pytest.raises(ValueError):
            load_tors(tors_file)

    def test_missing_required_field(self, tmp_path):
        """Test error when required field is missing."""
        tors_yaml = """
tors:
  - rack_id: rack-1
    model: sn2410
    ports:
      sfp28_total: 48
      qsfp28_total: 8
"""
        tors_file = tmp_path / "tors.yaml"
        tors_file.write_text(tors_yaml)

        with pytest.raises(ValueError):
            load_tors(tors_file)


class TestLoadNodes:
    """Test nodes loader."""

    def test_happy_path_with_nics(self, tmp_path):
        """Test successful nodes loading with NICs."""
        nodes_yaml = """
- id: node-1
  hostname: inferno-n1
  rack_id: rack-1
  nics:
    - type: SFP28
      count: 1
    - type: RJ45
      count: 1
- id: node-2
  rack_id: rack-1
"""
        nodes_file = tmp_path / "nodes.yaml"
        nodes_file.write_text(nodes_yaml)

        result = load_nodes(nodes_file)

        assert len(result) == 2
        assert isinstance(result[0], NodeRec)
        assert result[0].id == "node-1"
        assert result[0].hostname == "inferno-n1"
        assert result[0].rack_id == "rack-1"
        assert len(result[0].nics) == 2
        assert isinstance(result[0].nics[0], NicRec)
        assert result[0].nics[0].type == "SFP28"
        assert result[0].nics[0].count == 1
        assert result[0].nics[1].type == "RJ45"
        assert result[0].nics[1].count == 1

        # Second node without hostname and nics
        assert result[1].id == "node-2"
        assert result[1].hostname is None
        assert result[1].rack_id == "rack-1"
        assert len(result[1].nics) == 0

    def test_missing_optional_fields_defaults(self, tmp_path):
        """Test that missing optional fields get proper defaults."""
        nodes_yaml = """
- id: node-1
  rack_id: rack-1
"""
        nodes_file = tmp_path / "nodes.yaml"
        nodes_file.write_text(nodes_yaml)

        result = load_nodes(nodes_file)

        assert len(result) == 1
        assert result[0].hostname is None
        assert result[0].nics == []

    def test_type_coercion(self, tmp_path):
        """Test that string counts are coerced to integers."""
        nodes_yaml = """
- id: node-1
  rack_id: rack-1
  nics:
    - type: SFP28
      count: "2"
"""
        nodes_file = tmp_path / "nodes.yaml"
        nodes_file.write_text(nodes_yaml)

        result = load_nodes(nodes_file)

        assert result[0].nics[0].count == 2

    def test_wrong_structure(self, tmp_path):
        """Test error when file has wrong structure (dict instead of list)."""
        nodes_yaml = """
id: node-1
rack_id: rack-1
"""
        nodes_file = tmp_path / "nodes.yaml"
        nodes_file.write_text(nodes_yaml)

        with pytest.raises(ValueError):
            load_nodes(nodes_file)

    def test_missing_required_field(self, tmp_path):
        """Test error when required field is missing."""
        nodes_yaml = """
- id: node-1
"""
        nodes_file = tmp_path / "nodes.yaml"
        nodes_file.write_text(nodes_yaml)

        with pytest.raises(ValueError):
            load_nodes(nodes_file)


class TestLoadSite:
    """Test site loader."""

    def test_happy_path(self, tmp_path):
        """Test successful site loading."""
        site_yaml = """
racks:
  - id: rack-1
    grid: [0, 0]
    tor_position_u: 42
  - id: rack-2
    grid: [1, 0]
"""
        site_file = tmp_path / "site.yaml"
        site_file.write_text(site_yaml)

        result = load_site(site_file)

        assert isinstance(result, SiteRec)
        assert len(result.racks) == 2
        assert result.racks[0].id == "rack-1"
        assert result.racks[0].grid == (0, 0)
        assert result.racks[0].tor_position_u == 42
        assert result.racks[1].id == "rack-2"
        assert result.racks[1].grid == (1, 0)
        assert result.racks[1].tor_position_u is None

    def test_grid_coercion_string(self, tmp_path):
        """Test that grid strings are coerced to tuples."""
        site_yaml = """
racks:
  - id: rack-1
    grid: "1,2"
"""
        site_file = tmp_path / "site.yaml"
        site_file.write_text(site_yaml)

        result = load_site(site_file)

        assert result.racks[0].grid == (1, 2)

    def test_missing_optional_fields(self, tmp_path):
        """Test that missing optional fields default to None."""
        site_yaml = """
racks:
  - id: rack-1
"""
        site_file = tmp_path / "site.yaml"
        site_file.write_text(site_yaml)

        result = load_site(site_file)

        assert result.racks[0].grid is None
        assert result.racks[0].tor_position_u is None

    def test_file_not_found_returns_none(self):
        """Test that missing site.yaml returns None (not an error)."""
        result = load_site("nonexistent.yaml")
        assert result is None

    def test_invalid_grid_format(self, tmp_path):
        """Test error with invalid grid format."""
        site_yaml = """
racks:
  - id: rack-1
    grid: "invalid"
"""
        site_file = tmp_path / "site.yaml"
        site_file.write_text(site_yaml)

        with pytest.raises(ValueError):
            load_site(site_file)

    def test_type_coercion_tor_position(self, tmp_path):
        """Test that tor_position_u strings are coerced to integers."""
        site_yaml = """
racks:
  - id: rack-1
    tor_position_u: "42"
"""
        site_file = tmp_path / "site.yaml"
        site_file.write_text(site_yaml)

        result = load_site(site_file)

        assert result.racks[0].tor_position_u == 42


class TestErrorHandling:
    """Test error handling across all loaders."""

    def test_empty_yaml_file(self, tmp_path):
        """Test error with empty YAML file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")

        with pytest.raises(ValueError):
            load_topology(empty_file)

    def test_null_yaml_file(self, tmp_path):
        """Test error with null YAML file."""
        null_file = tmp_path / "null.yaml"
        null_file.write_text("null")

        with pytest.raises(ValueError):
            load_topology(null_file)
