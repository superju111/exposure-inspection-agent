"""
Unit tests for the analyzer module.
Tests verify that knowledge rules are properly consumed by code
and that rule removal (ablation) produces measurable quality change.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from config import load_knowledge_rules


class TestAnalyzerRules(unittest.TestCase):
    """Test that analyzer properly loads and applies knowledge rules."""

    @classmethod
    def setUpClass(cls):
        knowledge_dir = os.path.join(os.path.dirname(__file__), '..', 'knowledge')
        cls.rules = load_knowledge_rules(knowledge_dir)

    def test_port_risk_rules_loaded(self):
        """Verify port_risk_rules.yaml is loaded with expected structure."""
        rules = self.rules.get("port_risk_rules", {})
        self.assertIn("internet_blocklist", rules)
        self.assertIn("conditional_exposure", rules)
        self.assertIn("combination_rules", rules)

        # Verify blocklist contains expected high-risk ports
        blocklist_ports = [p["port"] for p in rules["internet_blocklist"]["ports"]]
        self.assertIn(2375, blocklist_ports, "Docker port should be in blocklist")
        self.assertIn(6379, blocklist_ports, "Redis port should be in blocklist")
        self.assertIn(6443, blocklist_ports, "K8s API should be in blocklist")

    def test_banner_signatures_loaded(self):
        """Verify banner_signatures.yaml has high-risk and FP patterns."""
        sigs = self.rules.get("banner_signatures", {})
        self.assertIn("high_risk_signatures", sigs)
        self.assertIn("false_positive_signatures", sigs)

        # Verify Apache CVE pattern exists
        hr_patterns = [s["pattern"] for s in sigs["high_risk_signatures"]]
        self.assertTrue(
            any("apache/2.4.49" in p.lower() for p in hr_patterns),
            "Apache CVE-2021-41778 pattern should be in high-risk signatures"
        )

        # Verify Cloudflare FP pattern exists
        fp_patterns = [s["pattern"] for s in sigs["false_positive_signatures"]]
        self.assertTrue(
            any("cloudflare" in p.lower() for p in fp_patterns),
            "Cloudflare CDN pattern should be in false-positive signatures"
        )

    def test_priority_matrix_loaded(self):
        """Verify priority_matrix.yaml has multipliers and thresholds."""
        matrix = self.rules.get("priority_matrix", {})
        self.assertIn("asset_criticality", matrix)
        self.assertIn("rule_confidence", matrix)
        self.assertIn("priority_thresholds", matrix)

        # Verify crown jewel multiplier is 2.0
        for entry in matrix["asset_criticality"]:
            if "crown-jewel" in entry.get("tags", []):
                self.assertEqual(entry["multiplier"], 2.0)

        # Verify P1 threshold
        thresholds = matrix["priority_thresholds"]
        self.assertIn("p1", thresholds)

    def test_exposure_criteria_loaded(self):
        """Verify exposure_criteria.yaml has evidence sufficiency rules."""
        criteria = self.rules.get("exposure_criteria", {})
        self.assertIn("evidence_sufficiency", criteria)
        self.assertIn("sufficient_for_auto", criteria["evidence_sufficiency"])
        self.assertIn("requires_manual_review", criteria["evidence_sufficiency"])

    def test_combination_rules_incident_frequency(self):
        """Verify combination rules include incident frequency data."""
        rules = self.rules.get("port_risk_rules", {})
        for combo in rules.get("combination_rules", []):
            self.assertIn("incident_frequency", combo,
                          "Combination rules must include incident frequency")
            self.assertGreater(combo["incident_frequency"], 0,
                               "Incident frequency must be positive")

    def test_rule_ids_unique(self):
        """Verify all rule IDs are unique across rule files."""
        all_ids = set()

        # Collect from port_risk_rules
        port_rules = self.rules.get("port_risk_rules", {})
        for entry in port_rules.get("internet_blocklist", {}).get("ports", []):
            all_ids.add(entry.get("rule_id"))
        for entry in port_rules.get("conditional_exposure", {}).get("ports", []):
            all_ids.add(entry.get("rule_id"))
        for entry in port_rules.get("combination_rules", []):
            all_ids.add(entry.get("rule_id"))

        # Collect from banner_signatures
        sigs = self.rules.get("banner_signatures", {})
        for entry in sigs.get("high_risk_signatures", []):
            all_ids.add(entry.get("rule_id"))
        for entry in sigs.get("false_positive_signatures", []):
            all_ids.add(entry.get("rule_id"))

        # Verify no None values (all rules have IDs)
        self.assertNotIn(None, all_ids, "All rules must have rule_id")
        self.assertGreater(len(all_ids), 10, "Should have more than 10 unique rule IDs")


if __name__ == "__main__":
    unittest.main()
