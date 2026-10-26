# dev-k3s-v5 metrics collectors (desired state, applied manually 2026-10-26)

Namespace `monitoring` on dev-k3s-v5 only. Production web-saas-k3s-v5 is unchanged.

- `agent-values.yaml`: same `observability-agent` chart and exporter pins as prod
  (node-exporter v1.12.1, kube-state-metrics v2.20.0, process-exporter 0.8.7), release `dev-observability-agent`.
- `vmagent.yaml`: vmagent v1.101.0 (matches prod VictoriaMetrics v1.101.0) with the prod job set
  (node-exporter, process-exporter, kube-state-metrics, kubelet, cadvisor).

## Label scheme
- `cluster=dev-k3s-v5` (vmagent external label).
- `environment`: `dev` by default (host/unlabelled); series whose `namespace` ends in `-sit` / `-uat`
  get `sit` / `uat`. Convention: such namespaces must also carry label `environment=sit|uat`.
- `namespace`, `pod`, `container`, `node`, `instance`, `nodename` kept as in prod.

## Remote write — BLOCKED
`-remoteWrite.url` currently points at a temporary in-namespace sink (`vmsink`, 2d retention).
observability-k3s-v5.svc.plus only proxies Grafana (:3000); there is no authenticated VictoriaMetrics
write route and no non-prod write credential. Needs a server-side ingest route + dedicated dev write
credential before switching the URL. Deviation: kubelet/cadvisor use `insecure_skip_verify: true`
(K3s kubelet serving cert not verified yet).
