# platform-mcp-dev secrets

No Secret values live in Git. The bootstrap playbook creates this Secret directly with
`kubectl apply` (generated on the node, never logged) before/after Flux syncs the unit.
All references are `optional: true`, so pods start even if keys are missing.

| Secret | Namespace | Key | Used by | Purpose |
| --- | --- | --- | --- | --- |
| `infra-mcp-auth` | `platform-mcp-dev` | `mcp-service-token` | `infrastructure-mcp-server` (env `MCP_SERVICE_TOKEN`) | Random service token for the gateway. Enforced as inbound `Authorization: Bearer` on `/mcp`, `/sse`, `/api/v1/*` by Infrastructure-MCP-Server builds that include ai-workspace-infra/Infrastructure-MCP-Server#17 (`/healthz` stays open for probes). Older images ignore it. Once enforced, every client of `mcp.svc.plus` must send the token. |
| `infra-mcp-service-token` (ExternalSecret) | `platform-mcp-sit` | `mcp-service-token` ← `kv/sit/platform/mcp#mcp_service_token` | `infrastructure-mcp-server` (env `MCP_SERVICE_TOKEN`) | Gateway inbound Bearer token; replaces the bootstrap `infra-mcp-auth/mcp-service-token`. |
| `mcp-grafana-auth` (ExternalSecret) | `platform-mcp-sit` | `password` ← `kv/sit/platform/observability#grafana_admin_password` | `mcp-grafana` (env `GRAFANA_PASSWORD`; `GRAFANA_USERNAME=admin` in Git) | Shared observability credential, referenced not copied. Admin-level (no viewer SA in SIT yet); read-only enforced by `--disable-write --disable-admin` + gateway `disabled_tools`. Replace with a viewer SA token (`grafana_mcp_sa_token`) when available. |
| `infra-mcp-ssh` (ExternalSecret) | `platform-mcp-sit` | `ssh-private-key` ← Vault `kv/sit/platform/mcp#ssh_private_key_b64` (single-line base64; ESO `decodingStrategy: Base64` → raw key) | `ssh-mcp-server` sidecar (file `/var/run/secrets/ssh-mcp/ssh-private-key`) | Private key of the read-only `auditor` account on CMDB host targets. Never leaves the pod; other agents use SSH only via `mcp.svc.plus`. |
| `infra-mcp-ssh` (ExternalSecret) | `platform-mcp-sit` | `ssh-mcp-http-token` ← `kv/sit/platform/mcp#ssh_mcp_http_token` | sidecar `SSH_MCP_HTTP_TOKEN` + gateway backend `bearer_token_env` | Random token for the localhost-only ssh-mcp-server HTTP endpoint (defence in depth). |

Example (placeholders only):

```sh
kubectl -n platform-mcp-dev create secret generic infra-mcp-auth \
  --from-literal=mcp-service-token="<random>" \
  --from-literal=grafana-service-account-token="<viewer-sa-token>"
```

The Grafana SA token can only be minted after Grafana is up; the playbook may create the
Secret with just `mcp-service-token` first and patch the second key later (restart
`observability-mcp-gateway` afterwards).

## Vault-synced secrets (External Secrets)

Vault holds secrets only; usernames, URLs, hostnames and the `auditor` user are in Git/CMDB.
`vault-secrets.yaml` syncs from:

| Vault path (API `kv/data/...`) | Fields | Owner |
| --- | --- | --- |
| `kv/sit/platform/mcp` | `mcp_service_token`, `ssh_private_key_b64`, `ssh_mcp_http_token` | MCP stack only |
| `kv/sit/platform/observability` | `vmauth_password`, `grafana_admin_password` | Observability stack (MCP only reads `grafana_admin_password`) |

Identity: `security/vault/workload-identities/sit-k3s-v6-platform-mcp-reader.yaml`, policy
`platform-mcp-reader` (read on those two paths). Until the fields, policy and role exist the
references stay `optional: true`; the gateway remains Ready and reports backend errors in
`infra.backends`. The bootstrap `infra-mcp-auth` Secret is no longer referenced (cleanup later).
