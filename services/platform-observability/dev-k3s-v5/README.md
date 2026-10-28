# Self-hosted observability collectors for dev-k3s-v5

This directory declares the self-hosted VictoriaMetrics collection path for
the `dev-k3s-v5/sit` environment. Flux owns this directory through the
cluster's `platform-observability` Kustomization. The existing DataKit release
uses its separate Kustomization under `datakit/` and can coexist with these
components.

`agent-values.yaml` enables node-exporter, kube-state-metrics and
process-exporter. `vmagent.yaml` grants read-only discovery/scrape access,
scrapes those exporters plus kubelet/cAdvisor, and writes to the local
VictoriaMetrics `vmsink` service. That sink uses a 2-day ephemeral volume, so
it is suitable for temporary SIT visibility and does not provide durable or
central retention. No central production Grafana endpoint or credential is
configured here.

DataKit values, its Secret reference, and Guance collection behavior stay
unchanged in the separate Kustomization.

Runtime acceptance still requires checking Flux reconciliation, all exporter
and vmagent workloads, scrape target health, and fresh `kube_node_info` plus
workload/cAdvisor samples with the expected labels. Static declarations alone
do not establish that collection is live.
