# platform-mcp-dev secrets

No Secret values live in Git. The bootstrap playbook creates this Secret directly with
`kubectl apply` (generated on the node, never logged) before/after Flux syncs the unit.
All references are `optional: true`, so pods start even if keys are missing.

| Secret | Namespace | Key | Used by | Purpose |
| --- | --- | --- | --- | --- |
| `infra-mcp-auth` | `platform-mcp-dev` | `mcp-service-token` | `infrastructure-mcp-server` (env `MCP_SERVICE_TOKEN`) | Random service token for the gateway. Enforced as inbound `Authorization: Bearer` on `/mcp`, `/sse`, `/api/v1/*` by Infrastructure-MCP-Server builds that include ai-workspace-infra/Infrastructure-MCP-Server#17 (`/healthz` stays open for probes). Older images ignore it. Once enforced, every client of `mcp.svc.plus` must send the token. |

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
| `kv/sit/platform/mcp` | `mcp_service_token`, `ssh_private_key_b64` (single-line base64) | MCP stack only |

Both land in one ExternalSecret/Secret, `platform-mcp` (each Vault field referenced once):

| Secret key | ← Vault field | Used by |
| --- | --- | --- |
| `mcp-service-token` | `kv/sit/platform/mcp#mcp_service_token` | gateway inbound Bearer (`MCP_SERVICE_TOKEN`, enforced from Infrastructure-MCP-Server#17) **and** ssh-mcp-server sidecar `SSH_MCP_HTTP_TOKEN`; the gateway's ssh backend sends it via `bearer_token_env: MCP_SERVICE_TOKEN` |
| `ssh-private-key` | `kv/sit/platform/mcp#ssh_private_key_b64` (ESO `decodingStrategy: Base64` → raw key) | sidecar file `/var/run/secrets/ssh-mcp/ssh-private-key` (0600; kubelet adds group-read for fsGroup). Shared root/auditor/operator key; the sidecar logs in as `auditor`, so access is bounded by the OS account. Never leaves the pod. |

Identity: `security/vault/workload-identities/sit-k3s-v6-platform-mcp-reader.yaml`, policy
`platform-mcp-reader` (read on `kv/sit/platform/mcp`; the observability path is no longer referenced here). References to `platform-mcp` are required:
until the fields, policy and role exist, new gateway pods wait (CreateContainerConfigError /
ContainerCreating) and the RollingUpdate (`maxUnavailable: 0`) keeps the previous pods serving. The bootstrap `infra-mcp-auth` Secret is no longer referenced (cleanup later).
