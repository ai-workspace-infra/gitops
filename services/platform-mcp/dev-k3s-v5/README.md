# Platform MCP Gateways (dev-k3s-v5)

Declarative Kubernetes manifests for deploying the dedicated MCP gateways onto the `dev-k3s-v5` cluster node via FluxCD GitOps.

## Dual-Domain Architecture

```text
mcp-server.svc.plus (dev-k3s-v5)
  |-- Ingress: dev-web-saas (hostPort 80/443 -> 8080)
  |-- TLS: dev-http01 (ACME HTTP-01)
  \-- Backend: infrastructure-mcp-server
        |-- Multi-cloud CMDB inventory & 15-edge Environment Graph
        |-- Safe read-only CLI executor & QMD memory integration
        \-- Upstream MCP client aggregation

mcp.svc.plus (dev-k3s-v5)
  |-- Ingress: dev-web-saas (hostPort 80/443 -> 8000)
  |-- TLS: dev-http01 (ACME HTTP-01)
  \-- Backend: observability-mcp-gateway
        |-- mcp-grafana: SSE (/v1/grafana/sse)
        |-- Read-only guardrails: --disable-write --disable-admin
        \-- Upstream telemetry data: https://observability.svc.plus/
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
