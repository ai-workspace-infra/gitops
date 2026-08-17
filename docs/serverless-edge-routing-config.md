# Serverless edge routing configuration

The UAT serverless delivery chain consumes one declarative configuration file:

```text
resources/svc.plus/uat/cloudflare/edge-routing.yaml
```

It is the configuration backend for:

```text
Supabase → Cloud Run → SSR Workers ×5 → edge-gateway Workers ×3 → Pages → Verify
```

The YAML declaration contains only non-sensitive values:

- Cloudflare zone, Pages project, and environment domains;
- SSR Worker names and route suffixes;
- edge-gateway Worker names and API routes;
- VPS and Cloud Run origin URLs;
- primary/fallback routing policy.

Cloudflare tokens, Vault tokens, JWT secrets, database credentials, and service-account
credentials remain runtime inputs from Vault/OIDC. A deployment must fail when the selected
GitOps ref does not contain the expected declaration.

## Definition contract

The file is a single `EdgeRoutingConfig` document with these required fields:

| Path | Type | Requirement |
|---|---|---|
| `apiVersion` | string | `gitops.svc.plus/v1alpha1` |
| `kind` | string | `EdgeRoutingConfig` |
| `metadata.environment` | string | Matches the selected environment directory |
| `spec.cloudflare.zone_name` | string | Cloudflare zone name |
| `spec.cloudflare.pages_project` | string | Pages project name |
| `spec.hosts.console_cloudflare` | string | Console Cloudflare hostname |
| `spec.hosts.accounts_cloudflare` | string | Accounts Cloudflare hostname |
| `spec.hosts.console_vps` | string | VPS console fallback hostname |
| `spec.hosts.accounts_vps` | string | VPS Accounts primary/fallback hostname |
| `spec.ssr` | list | Exactly five independently deployable boundaries |
| `spec.edge_gateway.boundaries` | list | `auth`, `admin`, and `core`; `core` must use `/api/*` |
| `spec.edge_gateway.defaults` | map | Public upstream and timeout policy; no secrets |

Every Worker name and route is declared once here. Consumers must not override these values
with repository-local environment-specific constants. Add SIT or production only by creating
the corresponding environment-scoped YAML file and validating it before enabling that
environment.

To test a branch of this repository from the orchestrator, set `gitops_ref` to that branch in
the manual dispatch. Production and SIT declarations should be added under their own
`resources/svc.plus/<env>/cloudflare/` path before those environments are enabled.
