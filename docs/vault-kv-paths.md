# Vault KV v2 contract

Vault values are runtime secrets and are not committed to GitOps or IaC. The `kv` mount uses
separate roots per environment:

```text
kv/uat/platform/{oidc,jwt,cloudflare,gcp,observability,gitea}
kv/uat/services/{xconnect,ai-workspace}
kv/prod/platform/{oidc,jwt,cloudflare,gcp,observability,gitea}
kv/prod/services/{xconnect,ai-workspace}
```

UAT maps to `open-platform-uat`; PROD maps to
`open-platform-prod`. There is no `kv/shared` credential path. Shared non-secret
defaults belong in the corresponding GitOps declaration.

## AI Aggregator v1 minimal contract

For both `uat` and `prod`, the only AI Aggregator secret paths are:

```text
kv/<env>/ai-aggregator/database/new-api
kv/<env>/ai-aggregator/database/litellm
kv/<env>/ai-aggregator/database/kong
kv/<env>/ai-aggregator/gateway/new-api
kv/<env>/ai-aggregator/gateway/litellm
kv/<env>/ai-aggregator/litellm/providers/openai
kv/<env>/ai-aggregator/litellm/providers/anthropic
kv/<env>/ai-aggregator/litellm/providers/xai
```

The KV v2 API addresses these records as `kv/data/<env>/ai-aggregator/...`.
The database records contain only `dsn`; Gateway records contain New API and
LiteLLM runtime secrets; provider records contain `endpoint` and `api_key` for
OpenAI, Anthropic, and xAI. Kong v1 uses a non-secret JWT public key supplied
by the node image or CMDB, so it does not need a Gateway KV secret. CPA OAuth,
channel tokens, client tokens, and account/instance metadata are not stored
under this namespace: OAuth remains in each CPA node's encrypted local auth
directory, while client and runtime metadata belong in PostgreSQL.

The deprecated `accounts/*`, `instances/*`, `clients/*`, `cpa/*`, and
`database/backup` paths must not be created by new automation. Existing records
are retained only for an explicitly approved migration and revocation process.

| Path | Required keys |
|---|---|
| `kv/<env>/platform/oidc/<account_id>` | `gcp_workload_identity_provider`, `deploy_service_account`, `gcp_oidc_audience` |
| `kv/<env>/serverless/gcp` | `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT_EMAIL` |
| `kv/<env>/platform/jwt` | `issuer`, `audience`, `signing_key` |
| `kv/<env>/platform/cloudflare` | `api_token`, `account_id`, `zone_id` |
| `kv/<env>/platform/gcp` | `project_id`, `region`, `artifact_registry` |
| `kv/<env>/platform/observability` | `grafana_admin_password`, `remote_write_token` |
| `kv/<env>/platform/gitea` | `url`, `runner_token`, `webhook_secret` |
| `kv/<env>/services/xconnect` | `supabase_url`, `supabase_service_role`, `jwt_audience` |
| `kv/<env>/services/ai-workspace` | `api_base_url`, `oauth_client_secret`, `jwt_audience` |

The UAT and PROD GitHub Actions identities may read only their own environment roots and an
explicit service allowlist. Terraform provisions the project, identity and network; Ansible
configures Vault policies and writes runtime values after deployment. CI logs must never print
secret values or Vault responses.

`GCP_PROJECT_ID` and `GCP_REGION` are non-sensitive and are read from the checked-in GitOps GCP
manifest by the Serverless workflow. They must not be duplicated in `kv/<env>/serverless/gcp`.
