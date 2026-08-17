# Serverless edge routing configuration

The UAT serverless delivery chain consumes one declarative configuration file:

```text
resources/svc.plus/uat/cloudflare/edge-routing.json
```

It is the configuration backend for:

```text
Supabase → Cloud Run → SSR Workers ×5 → edge-gateway Workers ×3 → Pages → Verify
```

The declaration contains only non-sensitive values:

- Cloudflare zone, Pages project, and environment domains;
- SSR Worker names and route suffixes;
- edge-gateway Worker names and API routes;
- VPS and Cloud Run origin URLs;
- primary/fallback routing policy.

Cloudflare tokens, Vault tokens, JWT secrets, database credentials, and service-account
credentials remain runtime inputs from Vault/OIDC. A deployment must fail when the selected
GitOps ref does not contain the expected declaration.

To test a branch of this repository from the orchestrator, set `gitops_ref` to that branch in
the manual dispatch. Production and SIT declarations should be added under their own
`resources/svc.plus/<env>/cloudflare/` path before those environments are enabled.
