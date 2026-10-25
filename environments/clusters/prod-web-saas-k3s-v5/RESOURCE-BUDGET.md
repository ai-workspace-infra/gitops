# Single-node resource profile

Refs #593. Capacity assumption: 2 vCPU / 4 GiB. This profile is a conservative
first adjustment, not a measured daily peak or a guarantee that simultaneous
memory limits fit physical RAM. Admission/scheduling uses requests; aggregate
limits describe shared burst allowances. Do not alter Grafana thresholds to
hide overcommit.

Targets against actual node allocatable capacity: CPU requests <=65%, memory
requests <=80%, configured CPU limits <=250%, configured memory limits <=200%.
These are target-profile review envelopes, not cluster-wide enforced quotas.
Unchanged system components with missing limits do not contribute to finite
limit sums. CPU is compressible; memory is not. Keep system/rollout headroom
and validate memory pressure, throttling, OOM and service health before promotion.
The available telemetry history is short; review a full representative load
window before tightening further. PostgreSQL and Vault memory stay unchanged.

| Component | CPU request / limit | Memory request / limit |
| --- | --- | --- |
| Flux helm-controller | 50m / 200m | 64Mi / 256Mi |
| Flux kustomize-controller | 75m / 250m | 128Mi / 384Mi |
| Flux source-controller | 50m / 250m | 96Mi / 256Mi |
| Flux notification-controller | 25m / 100m | 64Mi / 128Mi |
| Node exporter | 25m / 150m | 64Mi / 128Mi |
| Process exporter | 25m / 200m | 48Mi / 128Mi |
| Kube-state-metrics | 10m / 50m | 48Mi / 128Mi |
| Grafana | 50m / 400m | 512Mi / 1Gi |
| VictoriaMetrics | 50m / 400m | 384Mi / 768Mi |
| VictoriaLogs | 10m / 50m | 32Mi / 128Mi |
| VictoriaTraces | 25m / 100m | 192Mi / 384Mi |
| OTel | 25m / 200m | 128Mi / 256Mi |
| Plugin init | 10m / 200m | 64Mi / 384Mi |
| Console | 50m / 300m | 192Mi / 384Mi |
| Accounts | 25m / 200m | 64Mi / 256Mi |
| Billing | 15m / 100m | 48Mi / 192Mi |
| Content | 25m / 150m | 64Mi / 256Mi |
| Caddy | 15m / 100m | 48Mi / 128Mi |

Agent and application values are consumed by the existing immutable charts.
Stack 1.1.5 has no per-container resources values contract, so its existing
Helm post-renderer applies resource-only strategic merge patches by container
name. Do not add silently ignored resources values. Preserve images, commands,
probes, identities, persistence and replicas.

`controller-resources.yaml` intentionally applies resource-only SSA overlays to
existing bootstrap-managed Deployments. `ssa: Merge` preserves other owned
fields; `prune: disabled` prevents removing this profile from deleting Flux.
The bootstrap owner retains controller images/RBAC/arguments. A future bootstrap
replay may reset defaults temporarily; this GitOps profile reconciles its resource
fields again. Validate the existing controller names before enabling it.

Because pruning is disabled, reverting to a tag from before this profile does
not restore controller resource fields. Roll back those fields explicitly in a
reviewed follow-up declaration (former bootstrap defaults were 1 CPU / 1 GiB
limits, 64Mi requests and 100m CPU requests, except source-controller 50m).
Never delete Flux to roll back resource tuning. Application/agent/stack values
can revert through their previous declarations. Stage controller, exporter and
application rollouts and verify health before the memory-request increase for
the persistent observability stack; this document does not authorize a deployment.

Resource dashboard totals select only Pending/Running/Unknown Pods and match
Pod UID, excluding completed/failed operational Pods without deleting history.
Hidden/missing metrics and unchanged unbounded components are not healthy zero.

References: [Kubernetes resource semantics](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/),
[Flux SSA merge and prune](https://fluxcd.io/flux/components/kustomize/kustomizations/#controlling-the-apply-behavior-of-resources).

This PR does not advance the production Source/tag. The existing observability-only
promotion adapter rejects root/controller/application differences; a future
promotion must use a reviewed scope appropriate to these resource declarations,
not bypass that guard.
