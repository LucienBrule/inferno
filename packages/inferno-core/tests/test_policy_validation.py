"""
Comprehensive tests for policy validation functionality.

Tests all edge cases and validation rules A-I as specified in TASK.cabling.policy-edgecases.md
"""

from pathlib import Path

import pytest
import yaml
from inferno_core.validation.cabling import validate_policy_sanity


class TestPolicyValidation:
    """Test comprehensive policy validation with all edge cases."""

    @pytest.fixture
    def fixtures_dir(self):
        """Path to policy test fixtures."""
        return Path(__file__).parent / "fixtures" / "cabling" / "policy"

    def load_policy_fixture(self, fixtures_dir: Path, filename: str) -> dict:
        """Load a policy fixture file."""
        fixture_path = fixtures_dir / filename
        with open(fixture_path, "r") as f:
            return yaml.safe_load(f)

    def test_happy_path_no_findings(self, fixtures_dir):
        """Test valid policy produces no findings."""
        policy = self.load_policy_fixture(fixtures_dir, "happy.yaml")
        findings = validate_policy_sanity(policy)

        # Should have no FAIL or WARN findings for a valid policy
        fail_findings = [f for f in findings if f.severity == "FAIL"]
        [f for f in findings if f.severity == "WARN"]

        assert len(fail_findings) == 0, f"Expected no FAIL findings, got: {[f.code for f in fail_findings]}"
        # Note: We might have WARN findings for missing media types due to built-in defaults

    def test_spares_out_of_range(self, fixtures_dir):
        """Test spares_fraction > 1.0 → FAIL POLICY_SPARES_RANGE."""
        policy = self.load_policy_fixture(fixtures_dir, "spares_out_of_range.yaml")
        findings = validate_policy_sanity(policy)

        spares_findings = [f for f in findings if f.code == "POLICY_SPARES_RANGE"]
        assert len(spares_findings) == 1
        assert spares_findings[0].severity == "FAIL"
        assert "1.5" in spares_findings[0].message
        assert "between 0.0 and 1.0" in spares_findings[0].message

    def test_spares_type_error(self, fixtures_dir):
        """Test spares_fraction: "ten" → FAIL POLICY_SPARES_TYPE."""
        policy = self.load_policy_fixture(fixtures_dir, "spares_type.yaml")
        findings = validate_policy_sanity(policy)

        spares_findings = [f for f in findings if f.code == "POLICY_SPARES_TYPE"]
        assert len(spares_findings) == 1
        assert spares_findings[0].severity == "FAIL"
        assert "ten" in spares_findings[0].message
        assert "not coercible to float" in spares_findings[0].message

    def test_bins_empty(self, fixtures_dir):
        """Test empty bins_m → FAIL POLICY_BINS_EMPTY."""
        policy = self.load_policy_fixture(fixtures_dir, "bins_empty.yaml")
        findings = validate_policy_sanity(policy)

        bins_findings = [f for f in findings if f.code == "POLICY_BINS_EMPTY"]
        assert len(bins_findings) == 1
        assert bins_findings[0].severity == "FAIL"
        assert "sfp28_25g" in bins_findings[0].message
        assert "cannot be empty" in bins_findings[0].message

    def test_bins_unsorted(self, fixtures_dir):
        """Test unsorted bins [1,3,2] → FAIL POLICY_BINS_UNSORTED."""
        policy = self.load_policy_fixture(fixtures_dir, "bins_unsorted.yaml")
        findings = validate_policy_sanity(policy)

        bins_findings = [f for f in findings if f.code == "POLICY_BINS_UNSORTED"]
        assert len(bins_findings) == 1
        assert bins_findings[0].severity == "FAIL"
        assert "sfp28_25g" in bins_findings[0].message
        assert "strictly ascending" in bins_findings[0].message

    def test_bins_duplicate(self, fixtures_dir):
        """Test duplicate bins [1,2,2,3] → FAIL POLICY_BINS_DUPLICATE."""
        policy = self.load_policy_fixture(fixtures_dir, "bins_duplicate.yaml")
        findings = validate_policy_sanity(policy)

        bins_findings = [f for f in findings if f.code == "POLICY_BINS_DUPLICATE"]
        assert len(bins_findings) == 1
        assert bins_findings[0].severity == "FAIL"
        assert "sfp28_25g" in bins_findings[0].message
        assert "duplicate values" in bins_findings[0].message
        assert "2" in str(bins_findings[0].context.get("duplicates", []))

    def test_dac_invalid(self, fixtures_dir):
        """Test dac_max_m: 0 → FAIL POLICY_DAC_MAX_INVALID."""
        policy = self.load_policy_fixture(fixtures_dir, "dac_invalid.yaml")
        findings = validate_policy_sanity(policy)

        dac_findings = [f for f in findings if f.code == "POLICY_DAC_MAX_INVALID"]
        assert len(dac_findings) == 1
        assert dac_findings[0].severity == "FAIL"
        assert "sfp28_25g" in dac_findings[0].message
        assert "integer ≥ 1" in dac_findings[0].message

    def test_media_missing_defaulted(self, fixtures_dir):
        """Test missing qsfp28_100g → WARN POLICY_MEDIA_MISSING_DEFAULTED."""
        policy = self.load_policy_fixture(fixtures_dir, "media_missing_defaulted.yaml")
        findings = validate_policy_sanity(policy)

        media_findings = [f for f in findings if f.code == "POLICY_MEDIA_MISSING_DEFAULTED"]
        # Should have at least one for qsfp28_100g
        qsfp_findings = [f for f in media_findings if "qsfp28_100g" in f.message]
        assert len(qsfp_findings) == 1
        assert qsfp_findings[0].severity == "WARN"
        assert "missing from policy" in qsfp_findings[0].message
        assert "built-in defaults" in qsfp_findings[0].message

    def test_rj45_over_100m(self, fixtures_dir):
        """Test RJ45 bins > 100m → WARN POLICY_RJ45_BINS_GT_100M."""
        policy = self.load_policy_fixture(fixtures_dir, "rj45_over100.yaml")
        findings = validate_policy_sanity(policy)

        rj45_findings = [f for f in findings if f.code == "POLICY_RJ45_BINS_GT_100M"]
        assert len(rj45_findings) == 1
        assert rj45_findings[0].severity == "WARN"
        assert "150" in str(rj45_findings[0].context.get("bins_over_100m", []))
        assert "negotiate lower speeds" in rj45_findings[0].message

    def test_defaults_negative(self, fixtures_dir):
        """Test negative default value → FAIL POLICY_DEFAULT_NEGATIVE."""
        policy = self.load_policy_fixture(fixtures_dir, "defaults_negative.yaml")
        findings = validate_policy_sanity(policy)

        default_findings = [f for f in findings if f.code == "POLICY_DEFAULT_NEGATIVE"]
        assert len(default_findings) == 1
        assert default_findings[0].severity == "FAIL"
        assert "nodes_25g_per_node" in default_findings[0].message
        assert "must be ≥ 0" in default_findings[0].message
        assert "-1" in default_findings[0].message

    def test_redundancy_invalid(self, fixtures_dir):
        """Test invalid redundancy value → FAIL POLICY_REDUNDANCY_INVALID."""
        policy = self.load_policy_fixture(fixtures_dir, "redundancy_invalid.yaml")
        findings = validate_policy_sanity(policy)

        redundancy_findings = [f for f in findings if f.code == "POLICY_REDUNDANCY_INVALID"]
        assert len(redundancy_findings) == 1
        assert redundancy_findings[0].severity == "FAIL"
        assert "node_dual_homing" in redundancy_findings[0].message
        assert "boolean" in redundancy_findings[0].message

    def test_oversub_invalid(self, fixtures_dir):
        """Test invalid oversubscription ratio → FAIL POLICY_OVERSUB_INVALID."""
        policy = self.load_policy_fixture(fixtures_dir, "oversub_invalid.yaml")
        findings = validate_policy_sanity(policy)

        oversub_findings = [f for f in findings if f.code == "POLICY_OVERSUB_INVALID"]
        assert len(oversub_findings) == 1
        assert oversub_findings[0].severity == "FAIL"
        assert "max_leaf_to_spine_ratio" in oversub_findings[0].message
        assert "must be > 0" in oversub_findings[0].message

    def test_heuristics_invalid(self, fixtures_dir):
        """Test invalid heuristics value → FAIL POLICY_HEURISTICS_INVALID."""
        policy = self.load_policy_fixture(fixtures_dir, "heuristics_invalid.yaml")
        findings = validate_policy_sanity(policy)

        heuristics_findings = [f for f in findings if f.code == "POLICY_HEURISTICS_INVALID"]
        assert len(heuristics_findings) == 1
        assert heuristics_findings[0].severity == "FAIL"
        assert "slack_factor" in heuristics_findings[0].message
        assert "≥ 1.0" in heuristics_findings[0].message
        assert "0.9" in heuristics_findings[0].message

    def test_finding_structure(self, fixtures_dir):
        """Test that findings have proper structure and required fields."""
        policy = self.load_policy_fixture(fixtures_dir, "spares_out_of_range.yaml")
        findings = validate_policy_sanity(policy)

        assert len(findings) > 0, "Should have at least one finding"

        for finding in findings:
            # Check required fields
            assert hasattr(finding, "severity")
            assert hasattr(finding, "code")
            assert hasattr(finding, "message")
            assert hasattr(finding, "context")

            # Check severity is valid
            assert finding.severity in ["FAIL", "WARN", "INFO"]

            # Check code is not empty
            assert finding.code
            assert isinstance(finding.code, str)

            # Check message is not empty
            assert finding.message
            assert isinstance(finding.message, str)

            # Check context is dict
            assert isinstance(finding.context, dict)

    def test_all_error_codes_covered(self, fixtures_dir):
        """Test that all required error codes are implemented."""
        expected_codes = {
            "POLICY_SPARES_RANGE",
            "POLICY_SPARES_TYPE",
            "POLICY_BINS_EMPTY",
            "POLICY_BINS_UNSORTED",
            "POLICY_BINS_DUPLICATE",
            "POLICY_DAC_MAX_INVALID",
            "POLICY_MEDIA_MISSING_DEFAULTED",
            "POLICY_RJ45_BINS_GT_100M",
            "POLICY_DEFAULT_NEGATIVE",
            "POLICY_REDUNDANCY_INVALID",
            "POLICY_OVERSUB_INVALID",
            "POLICY_HEURISTICS_INVALID",
        }

        # Collect all codes from all test fixtures
        fixture_files = [
            "spares_out_of_range.yaml",
            "spares_type.yaml",
            "bins_empty.yaml",
            "bins_unsorted.yaml",
            "bins_duplicate.yaml",
            "dac_invalid.yaml",
            "media_missing_defaulted.yaml",
            "rj45_over100.yaml",
            "defaults_negative.yaml",
            "redundancy_invalid.yaml",
            "oversub_invalid.yaml",
            "heuristics_invalid.yaml",
        ]

        found_codes = set()
        for fixture_file in fixture_files:
            policy = self.load_policy_fixture(fixtures_dir, fixture_file)
            findings = validate_policy_sanity(policy)
            for finding in findings:
                found_codes.add(finding.code)

        # Check that all expected codes are found
        missing_codes = expected_codes - found_codes
        assert len(missing_codes) == 0, f"Missing error codes: {missing_codes}"


class TestPolicyValidationIntegration:
    """Integration tests for policy validation in the broader validation flow."""

    def test_policy_validation_in_main_flow(self):
        """Test that policy validation is integrated into the main validation flow."""
        # This would test that validate_policy_sanity is called from run_cabling_validation
        # For now, we can verify the function exists and is importable
        from inferno_core.validation.cabling import (
            run_cabling_validation,
            validate_policy_sanity,
        )

        # Verify functions exist
        assert callable(run_cabling_validation)
        assert callable(validate_policy_sanity)
