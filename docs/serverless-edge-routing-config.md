# Web SaaS runtime modes, routing, and database handover

The UAT source of truth is:

```text
resources/svc.plus/uat/cloudflare/edge-routing.yaml
```

The declaration exposes exactly three runtime modes:

```text
runtime.mode = vps | serverless | hybrid
```

```text
VPS mode
DNS → VPS Full Stack → Console / Accounts / Content / Billing
                    → self-managed PostgreSQL

Serverless mode
DNS → Cloudflare Pages → SSR ×5 → edge-gateway ×3
                      → Cloud Run: accounts / content-service / billing-service
                      → Supabase Cloud DB

Hybrid mode
DNS → Cloudflare edge → edge-gateway
                    → VPS primary → Cloud Run request-level fallback
```

## Runtime contract

`spec.runtime` is the single runtime control plane:

- `mode` selects `vps`, `serverless`, or `hybrid`.
- `routing.dns` owns canonical DNS targets and the 60-second TTL.
- `routing.load-balancer` declares the hybrid request-failover strategy.
- `routing.weight` is reserved for explicit traffic weighting; it is not changed implicitly by
  health checks.
- `services` maps Console, Accounts, Content, and Billing to their mode-specific runtimes.
- `data` declares primary/replica roles and the migration reservation.

UAT currently declares `runtime.mode: hybrid`, with VPS weight 100 and Serverless weight 0. This
keeps the required VPS→Cloud Run request-level failover explicit. A pure `serverless` rollout or
DNS-only `vps` rollout is a deliberate GitOps change.

## Canonical DNS contract

Canonical hostnames remain stable; only their CNAME targets change:

| Canonical hostname | VPS CNAME | Serverless CNAME |
| --- | --- | --- |
| `console-uat.onwalk.net` | `console-vps-uat.onwalk.net` | `console-cloudflare-uat.onwalk.net` |
| `accounts-uat.onwalk.net` | `accounts-vps-uat.onwalk.net` | `accounts-cloudflare-uat.onwalk.net` |

DNS is the top-level switch for `vps` and `serverless`. `hybrid` adds request-level failover at
edge-gateway: VPS is tried first for 2500 ms, then Cloud Run is retried on timeout, connection
failure, or a 5xx response. The edge-gateway failover is not a silent DNS mutation.

The production naming contract follows the same shape:

| Canonical hostname | VPS CNAME | Serverless CNAME |
| --- | --- | --- |
| `console.svc.plus` | `console-vps-prod.svc.plus` | `console-cloudflare-prod.svc.plus` |
| `accounts.svc.plus` | `accounts-vps-prod.svc.plus` | `accounts-cloudflare-prod.svc.plus` |

Production must be introduced through its own environment-scoped declaration and PR; the UAT
file does not enable production traffic.

## Database handover and async DTS reservation

`spec.runtime.data` reserves both database targets:

- `vps` uses self-managed PostgreSQL;
- `serverless` uses Supabase Cloud DB;
- `primary` and `replica` identify the current writer and prepared standby by mode;
- `migration.enabled` is `false` until an engine, network path, slot/publication policy, and
  cutover runbook have been approved;
- the reserved migration is asynchronous, bidirectional, single-writer, and capped at a
  60-second lag target with a required quiesce window;
- connection strings, replication credentials, JWT secrets, Cloudflare tokens, and service
  account keys are never stored in GitOps.

Before a mode or DNS cutover, the operator must validate lag, freeze writes, promote exactly one
writer, apply the selected DNS/runtime mode, and run verification. Rollback reverses those steps
without overwriting or deleting migration checkpoints.

## Consumer contract

Consumers must read this GitOps declaration rather than repository-local environment constants:

- `spec.runtime` defines mode, routing, services, and data handover;
- `spec.domains` defines the canonical `vps` and `serverless` CNAME targets;
- `spec.cloudflare` defines the Pages project and zone;
- `spec.serverless.ssr` defines exactly five independently deployable SSR boundaries;
- `spec.serverless.edge_gateway` defines `auth`, `admin`, and `core`; `core` owns `/api/*`.

All declaration changes require a GitOps PR to `main` before the platform orchestrator consumes
them.
