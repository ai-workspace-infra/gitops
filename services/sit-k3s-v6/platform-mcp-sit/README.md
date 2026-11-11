# platform-mcp-dev (dev-k3s-v6)

Infrastructure MCP Server for the single-node dev cluster (namespace `platform-mcp-dev`).

```text
https://mcp-sit.onwalk.net  (Caddy ingress, ingress-sit)
  \-- /  -> infrastructure-mcp-server:8080   (CMDB, Environment Graph, safe CLI exec)
              \-- in-cluster SSE -> grafana-mcp-server.observability-sit:8000/v1/grafana/sse
                     (mcp-grafana, deployed by the grafana chart with mcp.enabled=true; cluster-internal only)
```

- mcp-grafana (`--disable-write --disable-admin`) is no longer in this unit: it runs next to Grafana as
  `grafana-mcp-server` (HelmRelease `observability-grafana` in `observability-sit`, `mcp.enabled: true`)
  and reuses the Grafana admin Secret there, so this unit holds no Grafana credential.
- No Vault/ESO; Secret `infra-mcp-auth` is created by the playbook (see `SECRETS.md`).
- The Go server has no PostgreSQL support (CMDB/graph are in-memory), so no DB is configured.
- Requests total 100m CPU / 128Mi. Restricted PSA, read-only root FS, NetworkPolicy
  `business-namespaces-ingress` (same dev namespace set as the other V6 units).
- Image: `infrastructure-mcp-server` is a placeholder (`:latest`), override in `kustomization.yaml` `images:`.
