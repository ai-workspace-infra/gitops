"""UAT GCP Spot VMs must use OS Login.

The UAT GCP project enforces the requireOsLogin organization policy: GCP
rejects enable-oslogin=FALSE (HTTP 412) and ignores metadata SSH keys. These
are the manifests the Toolkit routes for the UAT Hybrid GCP lanes.
"""

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
UAT_GCP_SPOT_MANIFESTS = (
    "resources/onwalk.net/uat/gcp/web-saas.yaml",
    "resources/svc.plus/uat/gcp/ai-workspace.yaml",
    "resources/svc.plus/uat/gcp/agent-proxy-us.yaml",
)


class UatGcpOsLoginTest(unittest.TestCase):
    def test_every_routed_uat_gcp_spot_vm_enables_os_login(self):
        for relative in UAT_GCP_SPOT_MANIFESTS:
            document = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
            self.assertEqual(document["kind"], "GCPWorkloadNamespace", relative)
            self.assertEqual(document["metadata"]["environment"], "uat", relative)
            spot_vms = document["spec"]["resources"]["spot_vms"]
            self.assertTrue(spot_vms, relative)
            for vm in spot_vms:
                with self.subTest(manifest=relative, vm=vm["name"]):
                    self.assertIs(vm.get("enable_oslogin"), True)


if __name__ == "__main__":
    unittest.main()
