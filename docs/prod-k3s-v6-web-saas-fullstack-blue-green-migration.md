# prod-k3s-v6: web-saas-fullstack chart migration via blue/green namespaces (reserved design)

Status: design reservation only. No PROD manifests are changed by this note; PROD stays on
`oci://ghcr.io/ai-workspace-infra/distributed-web-saas-fullstack` at its pinned digests until the
migration below is executed under a separate, explicitly approved change.

## Why not an in-place switch

The chart was renamed `distributed-web-saas-fullstack` -> `web-saas-fullstack` (artifacts#278).
Flux helm-controller treats a chart-name change on an existing HelmRelease as a new release:
it uninstalls and reinstalls instead of upgrading. On SIT (gitops#887, 2026-11-11) this caused a
short outage of ingress, web-saas and PostgreSQL; the PostgreSQL PVC survived only because the
StatefulSet volumeClaimTemplate PVC and the `Retain` PV policy are not deleted by Helm uninstall.
PROD must not take that path in place.

Until migration, artifacts CI keeps publishing the compatibility name
`distributed-web-saas-fullstack` with contents identical to `web-saas-fullstack` (except the
Chart name), so PROD can keep bumping digests under the old name without a reinstall.

## Reserved pattern

For each PROD unit (`ingress-prod`, `web-saas-prod`; `postgresql-prod` last and separately):

1. **Green namespace**: add a parallel unit, e.g. `services/prod-k3s-v6/web-saas-prod-green/`, with
   namespace `web-saas-prod-green`, its own OCIRepository pointing at
   `oci://ghcr.io/ai-workspace-infra/web-saas-fullstack` (pinned digest), the same values, and
   `global.expectedNamespace: web-saas-prod-green`. Blue (`web-saas-prod`) is untouched.
2. **Secrets**: green gets its own ExternalSecret/SecretStore bindings (Vault role scoped to the
   green namespace); no secret copying by hand.
3. **Verify green** without public traffic: HelmRelease Ready, pods Running, Flagger canaries
   Succeeded, smoke tests through a green-only host or port-forward.
4. **Cut over** at the ingress layer (route weight or backend switch from blue to green
   Services), keeping blue running for rollback.
5. **Rollback** = switch the route back to blue. **Retire blue** only after an agreed soak
   period, by removing the blue unit from Git (no manual deletes, no Flux prune shortcuts).

### PostgreSQL

`postgresql-prod` holds state, so blue/green there means a second instance in
`postgresql-prod-green` restored from a verified backup (or replicated), a read-only window or
replication cutover for the switch, and an explicit data-acceptance check before blue is retired.
Never point two releases at the same PVC. Take and verify a backup before any step.

## Preconditions before executing

- Explicit approval for the PROD change and a maintenance window.
- Confirm PROD PV reclaim policies and a fresh, restorable PostgreSQL backup.
- Ingress capacity for both colors; VPA is not installed on PROD (VPA objects render nothing there).
