# Platform Ingress Controller (Caddy on dev-k3s-v5)

## Architecture & Policy

1. **Default Ingress / Gateway**:
   - In accordance with cluster governance policy, **Caddy** is deployed in the independent `platform-ingress` namespace as the standard cluster Ingress Controller / Gateway entrypoint.
   - **Traefik Ingress is strictly prohibited** (`默认禁止使用 Traefik Ingress 服务`).
2. **GitOps + FluxCD Delivery**:
   - Deployed via FluxCD `HelmRelease` (`helm.toolkit.fluxcd.io/v2`) consuming the official chart `caddyserver/caddy-ingress-controller` (version `1.3.0`) from `https://caddyserver.github.io/ingress/`.
   - Ingress class: `caddy` (`spec.ingressClassName: caddy`).
3. **Port & Node Binding**:
   - Container ports 80 and 443 bind to `hostPort: 80` and `hostPort: 443` on the single `dev-k3s-v5` node.
   - Resource requests: 50m CPU, 64Mi RAM; limits: 300m CPU, 256Mi RAM.
4. **ACME TLS Challenge**:
   - Automatically handles Let's Encrypt HTTP-01 challenges for ingresses with `ingressClassName: caddy`.
