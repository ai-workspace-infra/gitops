# Platform MCP Gateways (dev-k3s-v5)

Declarative Kubernetes manifests for deploying the dedicated MCP gateways onto the `dev-k3s-v5` cluster node via FluxCD GitOps.

## Single Domain Architecture (`mcp-server.svc.plus`)

```text
mcp-server.svc.plus (dev-k3s-v5)
  |-- Ingress: caddy (Caddy Ingress Controller in platform-ingress)
  |-- Path: /v1/grafana -> mcp-grafana:8000
  |     |-- SSE transport (/v1/grafana/sse)
  |     |-- Read-only guardrails: --disable-write --disable-admin
  |     \-- Upstream telemetry data: https://observability.svc.plus/
  \-- Path: / -> infrastructure-mcp-server:8080
        |-- Multi-cloud CMDB inventory & 15-edge Environment Graph
        |-- Safe read-only CLI executor & QMD memory integration
        \-- Upstream MCP client aggregation (https://mcp-server.svc.plus/v1/...)
```

## Security & Resource Guardrails

1. **Pod Security**: Restricted PSA (`runAsNonRoot: true`, `runAsUser: 65532`, `readOnlyRootFilesystem: true`, `capabilities.drop: [ALL]`).
2. **Resource Budget (2C4G node)**:
   - `infrastructure-mcp-server`: requests 50m / 64Mi, limits 200m / 256Mi.
   - `observability-mcp-gateway`: requests 50m / 64Mi, limits 200m / 256Mi.
   - Total allocation: 100m CPU, 128Mi RAM requests.
3. **Read-Only Redline**:
   - `mcp-grafana` explicitly runs with `--disable-write` and `--disable-admin`.
   - Grafana upstream connection strictly uses Viewer credentials.
