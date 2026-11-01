from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "delivery/candidates/web-saas-uat.yaml"


class ArtifactCandidatePolicyTest(unittest.TestCase):
    def setUp(self):
        self.document = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
        self.spec = self.document["spec"]

    def test_daily_is_uat_only_and_never_production_eligible(self):
        self.assertEqual(self.document["kind"], "ArtifactCandidatePolicy")
        self.assertEqual(self.spec["environment"], "uat")
        self.assertEqual(self.spec["candidate"]["id_prefix"], "daily-build")
        self.assertTrue(self.spec["candidate"]["immutable"])
        self.assertFalse(self.spec["candidate"]["production_eligible"])

    def test_components_are_unique_and_have_fixed_owner_contracts(self):
        components = self.spec["components"]
        names = [component["name"] for component in components]
        self.assertEqual(len(names), len(set(names)))
        self.assertNotIn("organization", self.spec)
        for component in components:
            with self.subTest(component=component["name"]):
                source = component["source"]
                self.assertRegex(source["repository"], r"^[a-z0-9-]+/[a-z0-9._-]+$")
                self.assertRegex(source["workflow"], r"^[a-z0-9._-]+\.ya?ml$")
                self.assertEqual(source["trigger"], "tag")
                artifact = component["artifact"]
                self.assertIn(artifact["kind"], {"oci-image", "github-release"})
                if artifact["kind"] == "oci-image":
                    self.assertTrue(artifact["require_digest"])
                    self.assertTrue(artifact["reference"].startswith("ghcr.io/"))
                else:
                    self.assertGreater(len(artifact["required_assets"]), 0)

    def test_no_prod_or_secret_values(self):
        text = POLICY.read_text(encoding="utf-8")
        self.assertNotRegex(text, re.compile(r"(?i)(password|private_key|token):"))
        self.assertNotIn("v202", text)
        self.assertNotIn("prod-v", text)

    def test_uat_dispatch_is_fail_closed_until_owner_is_ready(self):
        dispatch = self.spec["uat_dispatch"]
        if dispatch["status"] == "ready":
            self.assertTrue(dispatch["owner_repository"])
            self.assertTrue(dispatch["owner_workflow"])
            self.assertIn(dispatch["owner_key"], {"orchestrator", "gitops", "artifacts", "iac", "playbooks"})
            self.assertTrue(dispatch["receipt_artifact"])
        else:
            self.assertEqual(dispatch["status"], "pending-owner")
            self.assertEqual(dispatch["owner_repository"], "")
            self.assertEqual(dispatch["owner_workflow"], "")
            self.assertEqual(dispatch["owner_key"], "")
            self.assertEqual(dispatch["receipt_artifact"], "")


if __name__ == "__main__":
    unittest.main()

