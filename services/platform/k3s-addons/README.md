# K3s addon Flux templates

Each directory is an independently selectable Kustomize base containing one
Flux HelmRepository and HelmRelease. Nothing here is referenced by a cluster
root by default. A reviewed environment overlay can select only the required
components and own its namespace, release identity, values, credentials, image
versions/digests, resource limits and dependency order. These are templates,
not evidence of a deployment or acceptance.

| Directory | Chart version | Scope and selection considerations |
| --- | --- | --- |
| `cert-manager` | v1.20.0 | CRDs and controller; existing ClusterIssuer resources must depend on it |
| `reloader` | 1.3.0 | Optional controller; review watched namespaces and RBAC |
| `apisix` | 2.13.0 | Optional ingress/gateway; review topology, storage and routes in the environment overlay |
| `external-dns` | 1.20.0 | Defaults to `--dry-run`; provider identity, allowed zones and record policy require explicit reviewed configuration |
| `nginx-ingress` | 2.2.2 | Optional NGINX Ingress Controller; review class, exposure and TLS in the environment overlay |

The selected versions were checked for chart availability. Version selection is
not an image digest, capacity review or upgrade acceptance. cert-manager CRD
changes and any stateful addon upgrade follow the new-cluster policy. These
bases do not set IP addresses, credentials, domains or provider credentials.
ExternalDNS is never included in an environment by this change; removal of
`--dry-run` or authorization to write DNS is a separate reviewed operation.

Example Flux Kustomization selecting the reloader base (replace the source name
with the source declared for that environment):

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: addon-reloader
  namespace: flux-system
spec:
  interval: 5m
  sourceRef:
    kind: GitRepository
    name: platform-config
  path: ./services/platform/k3s-addons/reloader
  prune: true
  wait: true
```

The environment's Flux Kustomization must point to that overlay, specify its
source and required dependencies, and wait for the HelmRelease when another
unit needs it. Do not import a base alongside an existing controller release of
the same function without reviewing Helm release name, namespace, existing
resources, ownership and adoption/rollback. Do not delete legacy controllers
or resources simply because these templates render. Kustomize path restrictions
may require an environment-local overlay or a reviewed Flux source layout.

Existing cluster declarations remain authoritative: the current V6 ESO and
Caddy HelmReleases already have owners and must not be duplicated by these
bases. ESO/TLS, ingress and service acceptance remain separate runtime checks.
