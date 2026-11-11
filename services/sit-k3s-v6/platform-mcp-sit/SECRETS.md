# platform-mcp-dev secrets

No Secret values live in Git. The bootstrap playbook creates this Secret directly with
`kubectl apply` (generated on the node, never logged) before/after Flux syncs the unit.
All references are `optional: true`, so pods start even if keys are missing.

| Secret | Namespace | Key | Used by | Purpose |
| --- | --- | --- | --- | --- |
| `infra-mcp-auth` | `platform-mcp-dev` | `mcp-service-token` | `infrastructure-mcp-server` (env `MCP_SERVICE_TOKEN`) | Random service token for the gateway. Enforced as inbound `Authorization: Bearer` on `/mcp`, `/sse`, `/api/v1/*` by Infrastructure-MCP-Server builds that include ai-workspace-infra/Infrastructure-MCP-Server#17 (`/healthz` stays open for probes). Older images ignore it. Once enforced, every client of `mcp.svc.plus` must send the token. |
| `infra-mcp-auth` | `platform-mcp-dev` | `grafana-service-account-token` | `mcp-grafana` (env `GRAFANA_SERVICE_ACCOUNT_TOKEN`) | DEPRECATED for mcp-grafana (now reads `mcp-grafana-token`, below). Grafana **Viewer** service-account token for the in-cluster dev Grafana (`observability-dev`). Without it mcp-grafana cannot query Grafana (the gateway itself stays Ready). |
| `infra-mcp-ssh` (ExternalSecret) | `platform-mcp-sit` | `ssh-private-key` ← Vault `kv/data/CICD/infrastructure-mcp#ssh_private_key` | `ssh-mcp-server` sidecar (file `/var/run/secrets/ssh-mcp/ssh-private-key`) | Private key of the read-only `auditor` account on CMDB host targets. Never leaves the pod; other agents use SSH only via `mcp.svc.plus`. |
| `infra-mcp-ssh` (ExternalSecret) | `platform-mcp-sit` | `ssh-mcp-http-token` ← `#ssh_mcp_http_token` | sidecar `SSH_MCP_HTTP_TOKEN` + gateway backend `bearer_token_env` | Random token for the localhost-only ssh-mcp-server HTTP endpoint (defence in depth). |
| `infra-mcp-ssh-host-map` (ExternalSecret, optional) | `platform-mcp-sit` | `ssh-host-map` ← `#ssh_host_map` | `render-ssh-config` initContainer (`INFRA_SSH_HOST_MAP_FILE`) | JSON `{"<hostname>": "<address>"}` for names that do not resolve in-cluster (e.g. `sit-k3s-v6`, `prod-k3s-v6`). Addresses live only in Vault and the in-memory rendered config. |
| `mcp-grafana-token` (ExternalSecret) | `platform-mcp-sit` | `grafana-service-account-token` ← `#grafana_service_account_token` | `mcp-grafana` (env `GRAFANA_SERVICE_ACCOUNT_TOKEN`) | Grafana **Viewer** SA token. Must be a valid token for the SIT Grafana; the 2026-11 smoke test got 401. |

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

`vault-secrets.yaml` syncs the rows marked ExternalSecret from Vault KV v2
`kv/data/CICD/infrastructure-mcp` with the identity
`security/vault/workload-identities/sit-k3s-v6-platform-mcp-reader.yaml` (policy
`platform-mcp-reader`, read-only on that one path). An operator must create the Vault
fields and apply the policy/role via the Toolkit before these Secrets appear; until then
all references are `optional: true` and the gateway stays Ready (ssh/grafana backends
report errors in `infra.backends`).
