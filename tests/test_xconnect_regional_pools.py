import unittest
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

class XConnectRegionalPoolsTest(unittest.TestCase):
    def test_sg_pool_removed_and_iac_status_updated(self):
        pool_file = REPO_ROOT / "topology/prod/selfhost/xconnect-regional-pools.yaml"
        self.assertTrue(pool_file.exists())
        with open(pool_file) as f:
            data = yaml.safe_load(f)
        
        spec = data.get("spec", {})
        self.assertEqual(spec.get("provisioning", {}).get("iac_status"), "active_for_jp_us")
        
        pool_names = [p["name"] for p in spec.get("pools", [])]
        self.assertNotIn("sg", pool_names)
        self.assertIn("jp", pool_names)
        self.assertIn("us", pool_names)

    def test_akamai_xconnect_hosts_exclude_sg(self):
        akamai_file = REPO_ROOT / "resources/svc.plus/prod/akamai/xconnect.yaml"
        self.assertTrue(akamai_file.exists())
        with open(akamai_file) as f:
            data = yaml.safe_load(f)
            
        hosts = [h["name"] for h in data.get("hosts", [])]
        self.assertNotIn("sg", hosts)
        self.assertIn("jpn-tky", hosts)
        self.assertIn("us-ca", hosts)

if __name__ == "__main__":
    unittest.main()
