"""UAT AWS Debian hosts are reached as `admin`, never root.

Debian AMIs disable root SSH and answer "Please login as the user admin";
Daily 36800539711 (attempt 6) timed out waiting for root on jp-xconnect.
These are the AWS manifests the UAT Hybrid matrix routes.
"""

import os
import unittest
from pathlib import Path

import yaml
from jinja2 import Template

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "topology" / "uat" / "hybrid" / "resource-matrix.yaml"


class UatAwsLoginUserTest(unittest.TestCase):
    def test_routed_aws_debian_hosts_log_in_as_admin(self):
        matrix = yaml.safe_load(MATRIX.read_text(encoding="utf-8"))
        rows = [row for row in matrix.get("rows", matrix.get("resources", []))
                if isinstance(row, dict) and row.get("provider") == "aws-cloud"]
        if not rows:
            rows = [obj for obj in _objects(matrix) if obj.get("provider") == "aws-cloud" and "namespace" in obj]
        self.assertTrue(rows, "the UAT Hybrid matrix routes at least one AWS lane")
        for row in rows:
            path = ROOT / "resources" / "svc.plus" / "uat" / "aws" / f"{row['namespace']}.yaml"
            with self.subTest(manifest=str(path.relative_to(ROOT))):
                rendered = Template(path.read_text(encoding="utf-8")).render(env=os.environ)
                hosts = yaml.safe_load(rendered)["hosts"]
                self.assertTrue(hosts)
                for host in hosts:
                    if "debian" in str(host.get("os_name", "")).lower():
                        self.assertEqual(host.get("ansible_user"), "admin", host["name"])


def _objects(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _objects(item)
    elif isinstance(value, list):
        for item in value:
            yield from _objects(item)


if __name__ == "__main__":
    unittest.main()
