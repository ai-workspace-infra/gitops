# platform-mcp-dev (dev-k3s-v6)

Infrastructure MCP Server for the single-node dev cluster (namespace `platform-mcp-dev`).

```text
http://mcp-dev.onwalk.net  (Caddy ingress, ingress-dev)
  \-- /  -> infrastructure-mcp-server:8080   (CMDB, Environment Graph, safe CLI exec)
              \-- in-cluster SSE -> mcp-grafana:8000/v1/grafana/sse   (cluster-internal only)
                                     \-- http://observability-observability-stack.observability-dev.svc:3000
```

- `observability-mcp-gateway` (mcp-grafana, `--disable-write --disable-admin`) is kept because it is
  the only backend providing the observability tools; it is not exposed via ingress.
- No Vault/ESO; Secret `infra-mcp-auth` is created by the playbook (see `SECRETS.md`).
- The Go server has no PostgreSQL support (CMDB/graph are in-memory), so no DB is configured.
- Requests total 100m CPU / 128Mi. Restricted PSA, read-only root FS, NetworkPolicy
  `business-namespaces-ingress` (same dev namespace set as the other V6 units).
- Image: `infrastructure-mcp-server` is a placeholder (`:latest`), override in `kustomization.yaml` `images:`.
