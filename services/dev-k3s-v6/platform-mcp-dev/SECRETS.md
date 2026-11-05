# platform-mcp-dev secrets

No Secret values live in Git. The bootstrap playbook creates this Secret directly with
`kubectl apply` (generated on the node, never logged) before/after Flux syncs the unit.
All references are `optional: true`, so pods start even if keys are missing.

| Secret | Namespace | Key | Used by | Purpose |
| --- | --- | --- | --- | --- |
| `infra-mcp-auth` | `platform-mcp-dev` | `mcp-service-token` | `infrastructure-mcp-server` (env `MCP_SERVICE_TOKEN`) | Random service token for the gateway. NOTE: the current Go server does not enforce it itself; reserved for a fronting proxy / future auth. |
| `infra-mcp-auth` | `platform-mcp-dev` | `grafana-service-account-token` | `mcp-grafana` (env `GRAFANA_SERVICE_ACCOUNT_TOKEN`) | Grafana **Viewer** service-account token for the in-cluster dev Grafana (`observability-dev`). Without it mcp-grafana cannot query Grafana (the gateway itself stays Ready). |

Example (placeholders only):

```sh
kubectl -n platform-mcp-dev create secret generic infra-mcp-auth \
  --from-literal=mcp-service-token="<random>" \
  --from-literal=grafana-service-account-token="<viewer-sa-token>"
```

The Grafana SA token can only be minted after Grafana is up; the playbook may create the
Secret with just `mcp-service-token` first and patch the second key later (restart
`observability-mcp-gateway` afterwards).
