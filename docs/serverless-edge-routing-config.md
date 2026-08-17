# Web SaaS runtime modes, routing, and database handover

The environment- and mode-specific runtime topology sources of truth follow this matrix:

```text
topology/<env>/serverless/runtime-topology.yaml
topology/<env>/selfhost/runtime-topology.yaml
topology/<env>/hybrid/runtime-topology.yaml
```

where `<env>` is `sit`, `uat`, or `prod`. Each environment has its own domains, origins, Worker
names, Pages project, and database topology; consumers must select the declaration matching both
the requested environment and runtime mode.

The mode directories intentionally are not nested under `cloudflare/`. These declarations cover
the complete runtime topology—DNS, VPS Full Stack, Cloud Run, Supabase Cloud DB, and Cloudflare
boundaries—so the path must not be interpreted as a Cloudflare-only preparation requirement.

The declaration exposes exactly three runtime modes:

```text
runtime.mode = selfhost | serverless | hybrid
```

```text
Selfhost mode
DNS → VPS Full Stack → Console / Accounts / Content / Billing
                    → self-managed PostgreSQL

Serverless mode
DNS → Cloudflare Pages → SSR ×5 → edge-gateway ×3
                      → Cloud Run: accounts / content-service / billing-service
                      → Supabase Cloud DB

Hybrid mode
DNS → Cloudflare edge → edge-gateway
                    → selfhost primary → Cloud Run request-level fallback
```

## Runtime contract

Each file is a complete `EdgeRoutingConfig`; `spec.runtime` is its single runtime control plane:

- `mode` selects `selfhost`, `serverless`, or `hybrid`. `selfhost` is the runtime mode name;
  the physical target remains the existing VPS Full Stack.
- `routing.dns` owns canonical DNS targets and the 60-second TTL.
- `routing.load-balancer` declares the hybrid request-failover strategy.
- `routing.weight` is reserved for explicit traffic weighting; it is not changed implicitly by
  health checks.
- `services` maps Console, Accounts, Content, and Billing to their mode-specific runtimes.
- `data` declares primary/replica roles and the migration reservation.

The three UAT pre-configurations are intentionally explicit:

- `selfhost`: DNS targets the VPS Full Stack, with selfhost as the database primary.
- `serverless`: DNS targets Cloudflare Pages / edge-gateway, with Supabase as the database primary.
- `hybrid`: selfhost is the request-level primary and Cloud Run is the edge-gateway fallback.

The active traffic choice is made by selecting the matching declaration in the orchestrator; the
pipeline must never validate or deploy against a different mode file.

## Canonical DNS contract

Canonical hostnames remain stable; only their CNAME targets change:

| Canonical hostname | VPS CNAME | Serverless CNAME |
| --- | --- | --- |
| `console-uat.onwalk.net` | `console-vps-uat.onwalk.net` | `console-cloudflare-uat.onwalk.net` |
| `accounts-uat.onwalk.net` | `accounts-vps-uat.onwalk.net` | `accounts-cloudflare-uat.onwalk.net` |

DNS is the top-level switch for `selfhost` and `serverless`. `hybrid` adds request-level failover at
edge-gateway: selfhost is tried first for 2500 ms, then Cloud Run is retried on timeout, connection
failure, or a 5xx response. The edge-gateway failover is not a silent DNS mutation.

## Cloudflare boundary split

The Portal is deliberately built as five independent OpenNext SSR Workers, three independent
edge-gateway Workers, and one Pages project. This split is required to keep each Cloudflare Worker
artifact below the 3 MiB limit; the boundaries must not be recombined into a monolithic Worker.

| Boundary | Worker / Pages project | Routes | Deployment unit |
| --- | --- | --- | --- |
| SSR public pages | `frontend-ssr-public-uat` | `/*`, `/_edge/public/*` | Independent lightweight Worker |
| SSR content pages | `frontend-ssr-content-uat` | `/blogs*`, `/docs*`, `/download*` | Independent lightweight Worker |
| SSR identity pages | `frontend-ssr-auth-uat` | `/login*`, `/register*`, etc. | Independent lightweight Worker |
| SSR console | `frontend-ssr-console-uat` | `/panel*`, `/dashboard*` | Independent lightweight Worker |
| SSR workspace | `frontend-ssr-workspace-uat` | `/ai-workspace*`, `/editor*`, etc. | Independent lightweight Worker |
| API auth | `edge-gateway-auth-uat` | `accounts-cloudflare-uat.onwalk.net/api/auth/*` | Independent lightweight Worker |
| API admin | `edge-gateway-admin-uat` | `accounts-cloudflare-uat.onwalk.net/api/admin/*` | Independent lightweight Worker |
| API core | `edge-gateway-core-uat` | `accounts-cloudflare-uat.onwalk.net/api/*` fallback | Independent lightweight Worker |
| Static assets | `ai-workspace-portal-uat` | `/static/*`, `/assets/*` | Pages deployment |

The canonical names and complete route suffixes are declared in `spec.serverless.ssr` and
`spec.serverless.edge_gateway`; the table is a human-readable summary of that contract.

The production naming contract follows the same shape:

| Canonical hostname | VPS CNAME | Serverless CNAME |
| --- | --- | --- |
| `console.svc.plus` | `console-vps-prod.svc.plus` | `console-cloudflare-prod.svc.plus` |
| `accounts.svc.plus` | `accounts-vps-prod.svc.plus` | `accounts-cloudflare-prod.svc.plus` |

Production must be introduced through its own environment-scoped declaration and PR; the UAT
file does not enable production traffic.

## Database handover and async DTS reservation

`spec.runtime.data` reserves both database targets:

- `selfhost` uses self-managed PostgreSQL;
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
- `spec.domains` defines the canonical `selfhost` and `serverless` CNAME targets;
- `spec.cloudflare` defines the Pages project and zone;
- `spec.serverless.ssr` defines exactly five independently deployable SSR boundaries;
- `spec.serverless.edge_gateway` defines `auth`, `admin`, and `core`; `core` owns `/api/*`.

All declaration changes require a GitOps PR to `main` before the platform orchestrator consumes
them. Keep the three mode documents structurally aligned when changing shared domains, service
names, database migration reservations, or Cloudflare boundary names.
