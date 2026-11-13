# SIT K3s V6 Contabo host overlay

This overlay selects the manually created external host `sit-k3s-v6` through
the operator's direct SSH inventory input. The host endpoint is
`5.189.172.69` for SSH and must not be copied into Kubernetes service or DNS
target declarations. The logical service target is `sit-k3s-v6.svc.plus`; DNS
ownership changes the address behind that alias. The overlay itself contains no
public IP and does not perform DNS writes.

The environment root remains `environments/clusters/sit-k3s-v6`. The host-scoped
Flux root is `environments/clusters/sit-k3s-v6/overlays/contabo-vps`; the first
phase installs namespaces, External Secrets, and `cluster-identities-sit` (the
RBAC graph that `k3s_identity` waits on). VPA is active after r3. The Contabo
ExternalDNS unit is enabled separately with `--dry-run`; it reads the existing
SIT Cloudflare token through ESO and must not write records. PostgreSQL,
observability, MCP, ingress, and Web SaaS remain suspended. Every GitRepository
in this overlay is pinned to the release tag `sit-k3s-v6-contabo-r5`, created
on the merge commit containing this overlay. The old cluster's root sources
stay on `main`.

The PostgreSQL and observability overlays deliberately remove the base static
PersistentVolumes. Their Helm releases create fresh `local-path` claims on this
host, with no binding to the old cluster's PV identity or data.

Vault KV remains on mount `kv` and preserves the existing SIT paths. Cluster JWT
auth is a separate identity concern and must be configured against this target's
K3s issuer before any ExternalSecret consumer is enabled.

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
   is already active. This overlay enables only ExternalDNS among the remaining
   units, with an explicit `--dry-run` argument and domain filters for
   `onwalk.net` and `svc.plus`; all other application Kustomizations remain
   suspended. The ExternalDNS Vault role is limited to reading the existing
   `feature-dns` credential. Verify Cloudflare zone-read access and dry-run
   logs. DNS record changes remain a separate, later action.
4. `security/vault/workload-identities/sit-k3s-v6-contabo-vps-*.yaml` declares
   three target-specific read-only role contracts. The approved Playbooks Vault
   identity owner must configure the dedicated JWT auth mount using the target
   K3s issuer and JWKS, then verify each role's allowed and denied KV paths.
   Flux does not install or configure these Vault roles.
5. Before enabling a service unit, verify each ExternalSecret is Ready from the
   expected `kv` mount and unchanged key path. Preserve the base references:
   `CICD/domains/svc.plus`, `CICD/observability`, and `sit/platform/mcp`.
   The `platform-mcp-reader` policy also includes
   `kv/data/sit/platform/observability`; verify whether that read remains needed
   and authorized when configuring the replacement role.
6. Enable service units incrementally in dependency order. PostgreSQL and
   observability overlays delete the old static PV declarations so Helm creates
   new claims. Do not enable web SaaS until its required Vault fields are
   migrated from plaintext placeholders and verified.
7. Keep ExternalDNS in dry-run while validating DNS intent. Change DNS only
   after ingress and service acceptance. Keep the alias `sit-k3s-v6.svc.plus`
   aimed at the old target until the new endpoint passes HTTPS, application,
   and rollback checks; then update the authoritative DNS record in its
   separately owned workflow.

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
