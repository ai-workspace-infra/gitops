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
DNS → Frontend Router → Pages (static) / SSR ×5 (dynamic) / edge-gateway ×3 (API)
                                                       → Cloud Run: accounts / content-service / billing-service
                                                       → Supabase Cloud DB (Cloud Run runtime only)

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
- `serverless`: DNS targets the Frontend Router and Edge Gateway, with Supabase as the database primary.
- `hybrid`: selfhost is the request-level primary and Cloud Run is the edge-gateway fallback.

The active traffic choice is made by selecting the matching declaration in the orchestrator; the
pipeline must never validate or deploy against a different mode file.

## Canonical DNS contract

Canonical hostnames remain stable; only their CNAME targets change. In addition, every complete
runtime profile declares five mode-qualified public service entrances using the form
`<service>-<mode>-<environment>.<base-domain>`:

| Canonical hostname | Selfhost CNAME | Serverless CNAME |
| --- | --- | --- |
| `console-uat.onwalk.net` | `console-selfhost-uat.onwalk.net` | `console-serverless-uat.onwalk.net` |
| `accounts-uat.onwalk.net` | `accounts-selfhost-uat.onwalk.net` | `accounts-serverless-uat.onwalk.net` |

| Service | Access contract | Serverless UAT entrance |
| --- | --- | --- |
| Console | public | `console-serverless-uat.onwalk.net` |
| Accounts | authenticated | `accounts-serverless-uat.onwalk.net` |
| Billing | authenticated | `billing-serverless-uat.onwalk.net` |
| PostgreSQL | authenticated | `postgresql-serverless-uat.onwalk.net` |
| Agent-Proxy | public UUID with internal validation | `agent-proxy-serverless-uat.onwalk.net` |

The same five entries are declared for `selfhost`, `serverless`, and `hybrid`; only the mode
segment changes. The complete declaration is `spec.public_endpoints`. The Serverless workflow
actively reconciles and verifies Console, Accounts, and Billing. PostgreSQL and Agent-Proxy keep
their provider-owned authenticated/UUID validation paths until their Serverless providers expose
an equivalent public adapter.

DNS is the top-level switch for `selfhost` and `serverless`. `hybrid` adds request-level failover at
edge-gateway: selfhost is tried first for 2500 ms, then Cloud Run is retried on timeout, connection
failure, or a 5xx response. The edge-gateway failover is not a silent DNS mutation.

## Cloudflare boundary split

The Portal is deliberately built as one Frontend Router Worker, five independent OpenNext SSR
Workers, three independent edge-gateway Workers, and one Pages project. This split is required to
keep each Cloudflare Worker artifact below the 3 MiB limit; the boundaries must not be recombined
into a monolithic Worker.

| Boundary | Worker / Pages project | Routes | Deployment unit |
| --- | --- | --- | --- |
| Frontend Router | `frontend-router-uat` | `console-serverless-uat.onwalk.net/*` | Console Custom Domain owner; static/API/SSR dispatcher |
| SSR public pages | `frontend-ssr-public-uat` | Router Service Binding fallback | Independent lightweight Worker |
| SSR content pages | `frontend-ssr-content-uat` | `/blogs*`, `/docs*`, `/download*` | Independent lightweight Worker |
| SSR identity pages | `frontend-ssr-auth-uat` | `/login*`, `/register*`, etc. | Independent lightweight Worker |
| SSR console | `frontend-ssr-console-uat` | `/panel*`, `/dashboard*` | Independent lightweight Worker |
| SSR workspace | `frontend-ssr-workspace-uat` | `/ai-workspace*`, `/editor*`, etc. | Independent lightweight Worker |
| API auth | `edge-gateway-auth-uat` | `accounts-serverless-uat.onwalk.net/api/auth/*`, `/api/v1/auth/*` | Independent lightweight Worker |
| API admin | `edge-gateway-admin-uat` | `accounts-serverless-uat.onwalk.net/api/admin/*` | Independent lightweight Worker |
| Edge Gateway Router Core | `edge-gateway-core-uat` | `accounts-serverless-uat.onwalk.net` Custom Domain owner; `/api/*` fallback | Accounts entry owner and independent lightweight Worker |
| Static assets | `ai-workspace-portal-uat` | `PAGES_ORIGIN` for `/_next/*`, `/static/*`, `/assets/*` | Pages deployment |

The canonical names and complete route suffixes are declared in `spec.serverless.frontend_router`,
`spec.serverless.ssr`, and `spec.serverless.edge_gateway`; the table is a human-readable summary
of that contract. The canonical Console and Accounts DNS names remain stable traffic-switch aliases;
the five mode-qualified hosts in `spec.public_endpoints` are the service-specific public entrances.

The production naming contract follows the same shape:

| Canonical hostname | Selfhost CNAME | Serverless CNAME |
| --- | --- | --- |
| `console.svc.plus` | `console-selfhost-prod.svc.plus` | `console-serverless-prod.svc.plus` |
| `accounts.svc.plus` | `accounts-selfhost-prod.svc.plus` | `accounts-serverless-prod.svc.plus` |

Production must be introduced through its own environment-scoped declaration and PR; the UAT
file does not enable production traffic.

## Database handover and async DTS reservation

`spec.runtime.data` reserves both database targets:

- `selfhost` uses self-managed PostgreSQL;
- `serverless` uses Supabase Cloud DB;
- `primary` and `replica` identify the current writer and prepared standby by mode;
- migration execution is selected only by the delivery workflow's `operation` input; the topology
  retains strategy and safety constraints but does not contain an enable/disable action switch;
- the reserved migration is asynchronous, bidirectional, single-writer, and capped at a
  60-second lag target with a required quiesce window;
- execution is selected by the control-plane workflow `operation`; this declarative topology does
  not contain an execution-enable flag.
- connection strings, replication credentials, JWT secrets, Cloudflare tokens, and service
  account keys are never stored in GitOps.

Before a mode or DNS cutover, the operator must validate lag, freeze writes, promote exactly one
writer, apply the selected DNS/runtime mode, and run verification. Rollback reverses those steps
without overwriting or deleting migration checkpoints.

## Consumer contract

Consumers must read this GitOps declaration rather than repository-local environment constants:

- `spec.runtime` defines mode, routing, services, and data handover;
- `spec.domains` defines the canonical Console/Accounts aliases;
- `spec.public_endpoints` defines the five mode-qualified public service entrances and access
  contracts (`public`, `authenticated`, `public_uuid`);
- `spec.cloudflare` defines the Pages project, zone, and static_cdn_url (direct Pages origin for SIT/UAT, dedicated assets domain for PROD);
- `spec.serverless.frontend_router` defines the Console Worker Custom Domain, Pages/API origins,
  static prefixes, the `api_auth` Edge Gateway Service Binding, and the five SSR Service Bindings;
- `spec.serverless.frontend_router.static_sections` maps a content section
  (`blogs`, `docs`, `products`, `support`) to the origin of the prebuilt static
  site that serves it. A section that is absent or empty stays on its SSR
  boundary, so declaring an entry is the rollout and removing it is the
  rollback. Sections may point at different Pages projects, which is what lets
  one be republished without touching the others or the main site;
- `spec.serverless.ssr` defines exactly five independently deployable SSR boundaries;
- `spec.serverless.edge_gateway` defines `auth`, `admin`, and `core`; `core` owns `/api/*`.
  Its stable `id: core` has the display name **Edge Gateway Router Core** because it also owns the
  Accounts Worker Custom Domain.

All declaration changes require a GitOps PR to `main` before the platform orchestrator consumes
them. Keep the three mode documents structurally aligned when changing shared domains, service
names, database migration reservations, or Cloudflare boundary names.
