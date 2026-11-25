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

    def test_low_latency_edge_tuning_persisted_in_prod_and_uat(self):
        for rel in (
            "topology/prod/selfhost/xconnect-regional-pools.yaml",
            "topology/uat/selfhost/xconnect-regional-pool.yaml",
        ):
            with open(REPO_ROOT / rel) as f:
                data = yaml.safe_load(f)
            nm = data.get("spec", {}).get("node_maintenance", {})
            sysctl = nm.get("sysctl", {})
            self.assertEqual(sysctl.get("tcp_slow_start_after_idle"), 0)
            self.assertEqual(sysctl.get("tcp_notsent_lowat"), 131072)
            haproxy = nm.get("haproxy", {})
            self.assertEqual(haproxy.get("bufsize"), 65536)
            self.assertEqual(haproxy.get("h2_initial_window_size"), 4194304)
            self.assertEqual(haproxy.get("pipesize"), 262144)
            self.assertTrue(haproxy.get("http_no_delay"))
            fluxgate = nm.get("fluxgate", {})
            self.assertEqual(fluxgate.get("version"), "0.2.1")
            self.assertEqual(fluxgate.get("h2_stream_window_size"), 4194304)
            self.assertEqual(fluxgate.get("h2_connection_window_size"), 16777216)
            xray = nm.get("xray", {})
            self.assertEqual(xray.get("buffer_size_kb"), 128)
            self.assertEqual(xray.get("uplink_only_timeout_seconds"), 15)
            self.assertEqual(xray.get("downlink_only_timeout_seconds"), 30)
            journald = nm.get("journald", {})
            self.assertEqual(journald.get("system_max_use"), "64M")
            self.assertEqual(journald.get("system_max_file_size"), "8M")
            self.assertEqual(journald.get("max_retention"), "3day")
            self.assertEqual(journald.get("runtime_max_use"), "16M")
            self.assertEqual(journald.get("service_memory_high"), "24M")
            self.assertEqual(journald.get("service_memory_max"), "48M")
            vector = nm.get("vector", {})
            self.assertIs(vector.get("system_logs_enabled"), False)
            self.assertEqual(vector.get("billing_disk_buffer_max_bytes"), 268435488)
            self.assertEqual(vector.get("prometheus_batch_max_events"), 250)
            self.assertEqual(vector.get("prometheus_buffer_max_events"), 500)
            self.assertEqual(vector.get("sink_batch_max_bytes"), 262144)
            self.assertEqual(vector.get("tokio_worker_threads"), 1)
            self.assertEqual(vector.get("malloc_arena_max"), 2)
            self.assertIn("thp:never", vector.get("malloc_conf", ""))
            self.assertIn("narenas:1", vector.get("malloc_conf", ""))
            self.assertEqual(vector.get("memory_high"), "72M")
            self.assertEqual(vector.get("memory_max"), "128M")

if __name__ == "__main__":
    unittest.main()
