# SIT K3s V6 Contabo host overlay

This overlay selects the manually created external host `sit-k3s-v6` through
the operator's direct SSH inventory input. The connection target is supplied at
execution time and is not copied into Kubernetes service or DNS target
declarations. DNS ownership changes the address behind the logical service
alias. The overlay itself does not perform DNS writes.

The environment root remains `environments/clusters/sit-k3s-v6`. The host-scoped
Flux root is `environments/clusters/sit-k3s-v6/overlays/contabo-vps`. The current
candidate activates PostgreSQL, local observability, Traefik ingress and
ExternalDNS; MCP and Web SaaS remain paused. ExternalDNS is in write mode, but
record cutover remains a separate action. Each release advances every Flux
GitRepository together to a new immutable SIT tag. The old cluster's root
sources stay on `main`.

The PostgreSQL and observability overlays deliberately remove the base static
PersistentVolumes. Their Helm releases create fresh `local-path` claims on this
host, with no binding to the old cluster's PV identity or data.

Vault KV remains on mount `kv` and preserves the existing SIT paths. Cluster JWT
auth is a separate identity concern and must be configured against this target's
K3s issuer before any ExternalSecret consumer is enabled.

For this host, the public AI Desktop route is intended to use SIT Traefik and a
Kubernetes Service that targets the separately managed host service. The route
must remain disabled until the host service is installed and its listener is
reachable from the cluster. DataKit forwarding to an external DataWay remains
off until a SIT-scoped credential is available; the local VictoriaMetrics and
Grafana stack does not depend on that forwarding path. Regional XConnect/XHTTP
Caddy hosts are separate from this cluster and must be selected from their
authoritative inventory before a host playbook is run.

## Rollout gates and ownership

1. GitOps owns this target overlay and the target-specific Kustomize paths. IaC
   currently has no Contabo provider registration or consumer for manual
   external-host ResourceMatrix declarations. This runbook is therefore an
   operator SSH target input, not an IaC/CMDB registration or cloud inventory
   record. Do not invent account, region, or provider resource IDs.
2. The
   root overlay points Flux at this directory while retaining the logical SIT
   cluster root and the existing `config-sit` Git source.
3. The `external-secrets` unit installs the pinned ESO chart and its CRDs. VPA
   is already active. ExternalDNS runs in write mode with the declared domain
   filters. Validate its observed records against the intended Kubernetes
   resources; do not add a hostname resource until its backend is healthy.
4. `security/vault/workload-identities/sit-k3s-v6-contabo-vps-*.yaml` declares
   three target-specific read-only role contracts. The approved Playbooks Vault
   identity owner must configure the dedicated JWT auth mount using the target
   K3s issuer and JWKS, then verify each role's allowed and denied KV paths.
   Flux does not install or configure these Vault roles.
5. Before enabling a service unit, verify each ExternalSecret is Ready from the
   expected Vault mount and key path. PostgreSQL, Grafana administrator access,
   remote-write credentials, and ingress TLS are delivered through ESO. Do not
   reuse production DataKit credentials for SIT.
6. PostgreSQL, local observability, and ingress are active in the current
   rollout. MCP and Web SaaS remain paused. The Contabo observability overlay
   omits external DataKit forwarding until a SIT-scoped DataWay credential is
   available; local VictoriaMetrics and Grafana run independently.
7. DNS cutover remains a separate action. ExternalDNS may create or update
   records declared by watched Kubernetes resources. Add hostname declarations
   only after the route backend passes health checks, then verify the
   authoritative answer and HTTPS response.

## Validation

From the GitOps repository root, Flux-compatible local renders are:

```sh
kubectl kustomize --load-restrictor LoadRestrictionsNone environments/clusters/sit-k3s-v6/overlays/contabo-vps
kubectl kustomize --load-restrictor LoadRestrictionsNone services/sit-k3s-v6/overlays/contabo-vps/external-secrets
kubectl kustomize --load-restrictor LoadRestrictionsNone services/sit-k3s-v6/overlays/contabo-vps/postgresql-sit
kubectl kustomize --load-restrictor LoadRestrictionsNone services/sit-k3s-v6/overlays/contabo-vps/observability-sit
kubectl kustomize --load-restrictor LoadRestrictionsNone services/sit-k3s-v6/overlays/contabo-vps/ingress-sit
```

These commands prove local Kustomize path resolution and patch rendering. They do
not prove Flux reconciliation, Vault role readiness, DNS propagation, service
health, or target-host deployment.
