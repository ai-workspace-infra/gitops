# Observability Baseline & Public Identity/Schema Contract (OBS-00)

- **Parent Issue**: [`ai-workspace-infra/gitops#557`](https://github.com/ai-workspace-infra/gitops/issues/557)
- **Task Issue**: [`ai-workspace-infra/gitops#558`](https://github.com/ai-workspace-infra/gitops/issues/558)
- **Captured Time**: `2026-10-25 19:05:06 CST (+0800)` to `2026-10-25 19:06:20 CST (+0800)` (`Asia/Shanghai`)
- **Baseline Git SHAs**:
  - `gitops`: `95a2c6f3112ba1cfe29c23b32253957484cafb97`
  - `playbooks`: `a7a01ac734968aa6e5f7baec0e172ae06a0b461d`
  - `iac_modules`: `3f049e5eae7cdd0358188dd318599a17176df04b`
  - `artifacts`: `a7ba34f38973d0777c1231200f8b85fcf52f5a9c`
  - `platform-ops-toolkit`: `78407c5cfede2a6eff9b693c143323599b63c19f`

---

## 1. Live Read-Only Endpoint & Stack Baseline (`2026-10-25 19:05 CST`)

| Check Item | Target / Source | Observed Value (Read-Only) | Status / Note |
| :--- | :--- | :--- | :--- |
| **Canonical Domain DNS** | `observability.svc.plus` | `CNAME observability-k3s-v5.svc.plus.` → `A 104.105.141.213` (TTL 60s) | Live DNS points to K3s V5 ingress (`104.105.141.213`); former source host `35.221.181.68` (`observability-shared-0`) was deleted on `2026-10-24`. |
| **Target K3s Domain DNS** | `observability-k3s-v5.svc.plus` | `A 104.105.141.213` (TTL 300s) | Matches `web-saas-k3s-v5` (`akamai-cloud:manbuzhe2026:jp-tyo-3`). |
| **`GET /api/health` (Canonical)** | `https://observability.svc.plus/api/health` | `HTTP/2 200` (`via: 1.1 Caddy`), `{"database":"ok","version":"13.2.4","commit":"0e79aef9d91abf3bdadae9af15763029072fb45b"}` | Observed at `2026-10-25T11:05:40Z` (`19:05:40 CST`). |
| **`GET /api/health` (Target K3s)** | `https://observability-k3s-v5.svc.plus/api/health` | `HTTP/2 200` (`via: 1.1 Caddy`), `{"database":"ok","version":"13.2.4","commit":"0e79aef9d91abf3bdadae9af15763029072fb45b"}` | Observed at `2026-10-25T11:05:45Z` (`19:05:45 CST`). |
| **`GET /login` (Target K3s)** | `https://observability-k3s-v5.svc.plus/login` | `HTTP/2 200` (`content-type: text/html; charset=UTF-8`) | Observed at `2026-10-25T11:05:53Z` (`19:05:53 CST`). |
| **`GET /api/datasources` (Unauth)** | `https://observability.svc.plus/api/datasources` | `HTTP/2 401` | Unauthenticated query access is properly rejected; live query verification requires authenticated acceptance (`OBS-05`), so unverified runtime queries are marked `NOT_RUN`. |
| **Flux HelmRelease** | `services/platform-observability/prod/release.yaml` | `HelmRelease/platform-observability` in namespace `platform-observability` | Consumes `platform-observability-values` + `source-grafana-values`. |
| **OCI Chart Digest** | `oci://ghcr.io/ai-workspace-infra/observability-stack` | `sha256:6c9edd8ad04a06ec73ea0a6967e6653c4e1f1048487b88c7e5e9a43c077f7174` | Source chart in `artifacts`: `oci/charts/open-platform/charts/observability-stack`. |
| **Component Versions** | `services/platform-observability/prod/values.yaml` | Grafana `13.2.4`, OTel Collector `0.114.0`, VictoriaMetrics `v1.101.0`, VictoriaLogs `v1.52.0`, VictoriaTraces `v0.1.0` | Plugins: `victoriametrics-logs-datasource@0.33.1`, `marcusolsson-treemap-panel@2.1.1`, `aiworkspace-xconnectuserdiagnostics-app@0.1.0`. |

### Canonical vs Non-Canonical Datasource UIDs

1. **`victoriametrics`** (`prometheus`, `http://127.0.0.1:8428`, `isDefault: true`) — **Provisioned** in `source-grafana-datasources.yaml`.
2. **`victorialogs`** (`victoriametrics-logs-datasource`, `http://127.0.0.1:9428`, derivedField `Trace ID` → `victoriatraces`) — **Provisioned** in `source-grafana-datasources.yaml`.
3. **`victoriatraces`** (`jaeger`, `http://127.0.0.1:10428/select/jaeger`, `tracesToLogs` → `victorialogs`, `tracesToMetrics` → `victoriametrics`) — **Provisioned** in `source-grafana-datasources.yaml`.
4. **`cmdb_postgres`** (`postgres`) — **Missing (`FAIL`)**: Referenced by all 6 panels in `cmdb-resource-overview`, but not declared in `source-grafana-datasources.yaml` (and `topology/shared/cmdb/observability-uat.yaml` declares `cmdb_postgres_uat`). Assigned to `OBS-01` & `OBS-04`.
5. **`WAYOn0FGz`** (`prometheus`) — **Invalid Legacy UID (`FAIL`)**: Hardcoded in row panels `187` and `189` of `StarsL-JOB-node`. Assigned to `OBS-04`.

---

## 2. 17 Dashboards & 256 Expanded Panels Inventory

From `services/platform-observability/prod/imported-grafana/` (`source-grafana-inventory.yaml`, `source-grafana-general-0.yaml`, `source-grafana-b3e84e3d474a-0.yaml`) plus the retained K3s cluster overview `services/platform-observability/prod/dashboards.yaml` (`web-saas-k3s-v5-overview`):

- **Total Dashboards**: `17` (`16` imported in `General` + `1` retained in `Platform`; folder `dfzrqnab9cpa8e` / `Observability Alerts` in `source-grafana-b3e84e3d474a-0.yaml` is empty with no alert rules or notification channels).
- **Total Expanded Panels**: `256` (`240` top-level panels + `16` nested panels inside collapsed row `189` of `StarsL-JOB-node`; note `homepage-navigation` row `28` also nests `4` panels).
- **Baseline Status Summary**:
  - `PASS`: `0` (Strict enforcement: unauthenticated/unverified runtime panels are never marked `PASS`)
  - `FAIL`: `92` (Static datasource, RBAC, metric name, label `env` vs `environment`, missing producer, or prohibited `or vector(...)` defects)
  - `NOT_RUN`: `124` (Requires host/cluster collector verification and authenticated Grafana query execution)
  - `N/A`: `40` (Pure structural `row` or static documentation `text` panels without queries)

| # | Dashboard UID | Title | Folder | Top Panels | Expanded Panels | Variables | Links | Primary Owner Tasks |
| :- | :--- | :--- | :--- | :-: | :-: | :-: | :-: | :--- |
| 1 | `StarsL-JOB-node` | Node Exporter Dashboard 20240520 通用JOB分组版 | `General` | 7 | 23 | 8 | 3 | `OBS-02`, `OBS-04` |
| 2 | `agent-ai-observability` | Agent / AI Application Observability | `General` | 19 | 19 | 5 | 3 | `OBS-03`, `OBS-04` |
| 3 | `ai-aggregator-overview` | AI Aggregator Overview | `General` | 10 | 10 | 2 | 0 | `OBS-02`, `OBS-04` |
| 4 | `begqoward2epsf` | Xray Dashboard | `General` | 15 | 15 | 3 | 1 | `OBS-02`, `OBS-04` |
| 5 | `blackbox-exporter-overview` | Blackbox Exporter & SSL Probe Overview | `General` | 9 | 9 | 2 | 0 | `OBS-02`, `OBS-04` |
| 6 | `cmdb-resource-overview` | CMDB · 多云资源总览 | `General` | 6 | 6 | 0 | 0 | `OBS-01`, `OBS-04` |
| 7 | `homepage-navigation` | 平台导航与总览 (Navigation Homepage) | `General` | 25 | 29 | 7 | 0 | `OBS-01`, `OBS-02`, `OBS-04` |
| 8 | `k6-performance-capacity-overview` | k6 Performance & Capacity Stress Test Dashboard | `General` | 23 | 23 | 6 | 0 | `OBS-04` |
| 9 | `postgres-exporter-overview` | PostgreSQL Database Overview | `General` | 8 | 8 | 3 | 0 | `OBS-02`, `OBS-04` |
| 10 | `process-exporter-with-tree` | process exporter dashboard with treemap | `General` | 15 | 15 | 2 | 0 | `OBS-02` |
| 11 | `serverless-fullstack-architecture` | 全栈无服务器与边缘架构总览 (Serverless & Edge Full-Stack Topology) | `General` | 38 | 38 | 7 | 0 | `OBS-01`, `OBS-02`, `OBS-04` |
| 12 | `victoria-logs-overview` | Victoria Logs Overview | `General` | 13 | 13 | 5 | 0 | `OBS-02`, `OBS-03`, `OBS-04` |
| 13 | `victoria-traces-overview` | VictoriaTraces Distributed Tracing APM | `General` | 11 | 11 | 3 | 0 | `OBS-03`, `OBS-04` |
| 14 | `xconnect-comprehensive` | XConnect 综合监控 | `General` | 24 | 24 | 3 | 1 | `OBS-02`, `OBS-04` |
| 15 | `xconnect-user-connection-diagnostics` | XConnect 用户慢连接诊断 | `General` | 1 | 1 | 0 | 0 | `OBS-04` |
| 16 | `xhttp-edge-reliability` | XHTTP Edge Reliability | `General` | 6 | 6 | 1 | 0 | `OBS-02`, `OBS-04` |
| 17 | `web-saas-k3s-v5-overview` | Web-SaaS K3s V5 PROD Cluster Overview | `Platform` | 6 | 6 | 1 | 0 | `OBS-03` |

---

## 3. Key Static Defects Identified in Baseline (`FAIL`)

1. **Undeclared Datasource UIDs (`OBS-01`, `OBS-04`)**:
   - `cmdb-resource-overview` panels `1..6` reference `postgres:cmdb_postgres`, which is absent from `source-grafana-datasources.yaml`.
   - `StarsL-JOB-node` row panels `187` and `189` reference legacy `prometheus:WAYOn0FGz`.
2. **K3s Collector RBAC & Metric Name Mismatch (`OBS-03`)**:
   - `services/platform-observability/prod/collector-identity.yaml` restricts `ClusterRole/web-saas-k3s-v5-node-stats` (`nodes/stats`, `nodes/metrics`, `nodes`) to `resourceNames: [localhost]`, preventing `kubeletstats` from reading node stats when the node name is `web-saas-k3s-v5`.
   - `web-saas-k3s-v5-overview` panels `1..3` query `k8s_node_cpu_utilization_ratio` and `container_memory_working_set_bytes`, whereas OTel `kubeletstats` emits `k8s_node_cpu_utilization` and `k8s_container_memory_working_set_bytes`.
   - `otel-collector.yml` in `observability-stack` lacks a containerd/CRI Pod log (`filelog`) receiver and `k3s` journald log collector.
3. **Prohibited `or vector(...)` & Synthetic Metric Masking (`OBS-04`)**:
   - `homepage-navigation` panel `3` queries literal `1` seven times; panel `5` and panel `30` use `or vector(0)`.
   - `k6-performance-capacity-overview` panel `3` uses `or vector(0)`.
   - `serverless-fullstack-architecture` panels `4, 5, 6, 7, 8` use synthetic fallbacks (`clamp_min(sum(rate(probe_duration_seconds...)) * 10, 1.2)`, `probe_duration_seconds * 100`, `or vector(0)`, `or vector(3)`, `or vector(12.5)`).
   - `victoria-traces-overview` panels `4, 5` hardcode `job="victoria-traces"` (whereas `prometheus.yml` scrapes `127.0.0.1:10428` under `job="victoriametrics"`) and mask the empty result with `or vector(0)`.
4. **Label & Variable Schema Drift (`OBS-02`, `OBS-03`, `OBS-04`)**:
   - `observability-stack` (`values.yaml` & `otel-collector.yml`) and `ai-aggregator-overview` / `k6-performance-capacity-overview` use canonical label `environment`, whereas `homepage-navigation`, `agent-ai-observability`, `blackbox-exporter-overview`, and `serverless-fullstack-architecture` filter by `env`.
   - `victoria-logs-overview` defines an `$environment` variable that is omitted from all 11 panel queries, and hardcodes a legacy `$host` list (`jp-k3s-vultr.svc.plus`, etc.) missing `web-saas-k3s-v5` and active XConnect nodes.
   - `StarsL-JOB-node` panel `200` queries undefined recording rules `cpu:usage:rate1m` and `mem:usage:rate1m`; panel `206` target `F` hardcodes `job="node_exporter"`.
   - `xconnect-comprehensive` panel `1` and `xconnect-user-connection-diagnostics` panel `1` link to `/grafana/a/aiworkspace-xconnectuserdiagnostics-app` instead of `/a/aiworkspace-xconnectuserdiagnostics-app` (`rootUrl: https://observability-k3s-v5.svc.plus/`).

---

## 4. Files in This Directory

- [`dashboard-coverage.csv`](./dashboard-coverage.csv): Full 256-panel coverage matrix across all 17 dashboards (`dashboard_uid,panel_id,title,datasource_uid,query,required_metric_or_field,source,resource_key,environment,freshness_limit,status,evidence,owner_task`).
- [`resource-coverage.csv`](./resource-coverage.csv): Redacted 39-row multi-environment resource coverage matrix across `prod`, `shared`, `uat`, and `sit` (`environment,provider_account_region,resource_id,runtime_form,collector,target_backend,expected_signals,last_data_time,status,owner_task`).
- [`identity-and-schema-contract.yaml`](./identity-and-schema-contract.yaml): Canonical resource key specification (`{provider}:{account_or_project}:{region}:{resource_id}`), CMDB (`cmdb.v1`, `cmdb.observations.v1`, `cmdb-postgresql-v1`) and telemetry (`victoriametrics`, `victorialogs`, `victoriatraces`) field mappings, freshness thresholds, and task ownership boundaries.
