# dev-k3s-v5 metrics collectors (declaration; runtime state not verified)

Namespace `monitoring` on dev-k3s-v5 only. Production web-saas-k3s-v5 is unchanged.

- `agent-values.yaml`: same `observability-agent` chart and exporter pins as prod
  (node-exporter v1.12.1, kube-state-metrics v2.20.0, process-exporter 0.8.7), release `dev-observability-agent`.
- `vmagent.yaml`: vmagent v1.101.0 (matches prod VictoriaMetrics v1.101.0) with the prod job set
  (node-exporter, process-exporter, kube-state-metrics, kubelet, cadvisor).

## Label scheme
- `cluster=dev-k3s-v5` (vmagent external label).
- Host and unmapped namespaces retain `environment=dev`.
- The explicit referral namespace rule targets the merged SIT Namespace from
  GitOps #606: `release.svc.plus/lane=sit`,
  `release.svc.plus/feature=xconnect-referral`. `release.svc.plus/environment=dev` denotes
  the infrastructure tier; `lane` supplies the measurement phase. Candidate and
  environment remain independent. No candidate label is emitted by this static
  declaration. Only a trusted owner runtime receipt binding namespace UID, full
  candidate and actual imageIDs may supply it; #599 metadata is not runtime proof.
- Do not infer phase from a namespace suffix. Unknown namespaces stay `dev`
  without a fabricated feature or candidate. New controlled namespace metadata
  requires a reviewed rule snapshot from the execution owner.
- Dev K3s V5 is strictly allocated for temporary SIT feature lanes only (g6-standard-2
  2C4G, per `docs/dev-sit-only-2c4g-transition.md` and GitOps #608). Persistent UAT
  is deployed entirely in Serverless mode (Cloudflare Pages + Cloud Run + Supabase Free)
  per `topology/uat/serverless/runtime-topology.yaml`. No UAT workload or namespace exists
  on Dev K3s V5; UAT monitoring is decoupled and handled by the Serverless observability
  plane, not by this cluster's vmagent.
- The former shell renderer was removed: it read unrelated `websaas.io` keys,
  and executable renderers do not belong in this declarations-only repository.
- `namespace`, `pod`, `container`, `node`, `instance`, `nodename` are preserved.
  Node series do not acquire a synthetic namespace/feature label.

## Deployment gates
This is a patch of the existing #601 declaration, not an independently deployable
release. No Dev identity or supported non-production ingest identity has been
verified. Do not deploy, merge, change production routing, or copy credentials.
The local sink is an explicit blocked placeholder, not central Grafana ingestion.
Current canonical StarsL supports cluster/environment, but its environment
choices derive from `kube_node_info`; host series marked `dev` do not enumerate
`sit`/`uat`. Selecting a phase can hide node metrics. Verify the live read-only
contract before claiming the requested combined view; do not duplicate node
series into phases to make the dashboard appear healthy.

## Remote write — BLOCKED
`-remoteWrite.url` currently points at a temporary in-namespace sink (`vmsink`, 2d retention).
An authenticated central Dev write route and dedicated write identity have not been
verified; this declaration does not establish whether an unobserved server-side route exists.
Do not switch the URL or claim central ingestion until the approved non-production route and
runtime injection are reviewed and verified. Kubelet/cadvisor use
`insecure_skip_verify: true`; K3s serving-certificate validation remains unresolved.
## DataKit via Flux HelmRelease

`datakit/` declares Flux ownership of the existing DataKit Helm release in the DEV K3s cluster. It configures Caddy metrics and feature-lane business Pod stdout/stderr logs for Guance while retaining the PostgreSQL exporter scrape. See `datakit/README.md` for ownership, migration, rollback, and acceptance details. This declaration does not enable or claim central VictoriaMetrics/Grafana ingestion.
