# Web SaaS dual-mode routing and database handover

The UAT source of truth is:

```text
resources/svc.plus/uat/cloudflare/edge-routing.yaml
```

It defines exactly two runtime modes. `spec.mode` is the desired mode for the environment;
the actual traffic switch is performed only by changing the canonical DNS CNAME target.

```text
VPS mode
DNS → VPS Full Stack → Console / Accounts / Content / Billing
                    → self-managed PostgreSQL

Serverless mode
DNS → Cloudflare Pages → SSR ×5 → edge-gateway ×3
                      → Cloud Run: accounts / content-service / billing-service
                      → Supabase Cloud DB
```

## Canonical DNS contract

UAT keeps stable canonical hostnames and uses a 60-second TTL:

| Canonical hostname | VPS CNAME | Serverless CNAME |
| --- | --- | --- |
| `console-uat.onwalk.net` | `console-vps-uat.onwalk.net` | `console-cloudflare-uat.onwalk.net` |
| `accounts-uat.onwalk.net` | `accounts-vps-uat.onwalk.net` | `accounts-cloudflare-uat.onwalk.net` |

The UAT declaration defaults to `serverless`. DNS is the only top-level traffic switch;
health checks must not silently rewrite the selected mode.

The production naming contract follows the same shape:

| Canonical hostname | VPS CNAME | Serverless CNAME |
| --- | --- | --- |
| `console.svc.plus` | `console-vps-prod.svc.plus` | `console-cloudflare-prod.svc.plus` |
| `accounts.svc.plus` | `accounts-vps-prod.svc.plus` | `accounts-cloudflare-prod.svc.plus` |

Production must be introduced through its own environment-scoped declaration and PR; the UAT
file does not enable production traffic.

## Database handover and async DTS reservation

Both database targets are declared so the two runtime modes can be prepared and switched without
changing application configuration at the last moment:

- VPS mode uses self-managed PostgreSQL.
- Serverless mode uses Supabase Cloud DB.
- `database.dts.enabled` is `false` until an engine, network path, slot/publication policy, and
  cutover runbook have been approved.
- The reserved DTS contract is asynchronous and declares both directions, a shared checkpoint
  Vault reference, a 60-second maximum lag target, and a required quiesce window.
- `single_writer: true` is mandatory. DTS does not imply dual-write or automatic failover.
- Database connection strings, replication credentials, JWT secrets, Cloudflare tokens, and
  service-account keys are never stored in GitOps; consumers resolve them from Vault/OIDC.

Before switching the canonical CNAME, the operator must verify that the target database has caught
up, freeze writes for the cutover window, promote exactly one writer, switch DNS, and then verify
the selected mode. Rollback reverses the same order and must not delete or overwrite checkpoints.

## Consumer contract

Consumers must read the GitOps declaration rather than repository-local environment constants:

- `spec.mode` and `spec.domains` define the two-mode contract.
- `spec.cloudflare` defines the Pages project and zone.
- `spec.serverless.ssr` defines exactly five independently deployable SSR boundaries.
- `spec.serverless.edge_gateway` defines `auth`, `admin`, and `core`; `core` owns `/api/*`.
- `spec.database.modes` and `spec.database.dts` define database targets and the disabled DTS
  reservation.

The edge-gateway keeps its repository-mandated request-level VPS→Cloud Run failover for an
individual request. That is an emergency resilience path, not the DNS mode switch: VPS mode is
selected by canonical DNS, while the normal Serverless deployment chain remains
Pages → SSR → edge-gateway → Cloud Run → Supabase.

Deployment order is separate from request topology:

```text
Supabase → Cloud Run ×3 → SSR ×5 → edge-gateway ×3 → Pages → Verify
```

All declaration changes require a GitOps PR to `main` before the platform orchestrator consumes
them.
