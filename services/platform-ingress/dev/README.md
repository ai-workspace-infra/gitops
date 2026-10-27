# One Dev ingress controller

Independent platform owner; never part of a feature Namespace/TTL. No existing
Traefik declaration was found, and K3s bootstrap disables both bundled traefik and
servicelb. This standalone official Helm chart does not restart/reconfigure K3s.

Pinned official chart 42.1.3 / OCI digest 49458ccd... and image v3.7.16 /
digest 1336e85a... are immutable in the manifests. Source: [official chart values](https://github.com/traefik/traefik-helm-chart/blob/master/traefik/values.yaml),
[HTTP-01 ACME](https://doc.traefik.io/traefik/reference/install-configuration/tls/certificate-resolvers/acme/),
[Kubernetes ingress provider](https://doc.traefik.io/traefik/reference/install-configuration/providers/kubernetes/kubernetes-ingress/).
Values were checked against the actual pinned chart schema and final rendering.

A single replica, Recreate, UID/GID/fsGroup 65532, RuntimeDefault, no capabilities,
no privilege escalation, no hostNetwork or hostPath. Container 8000/8443 maps only
to hostPort 80/443 on dev-k3s-v5. The namespace uses Pod Security enforce=privileged to permit hostPort; PSA does
not restrict it to these exact ports. The fixed reviewed manifest, owner raw/rendered
hashes and runtime checks constrain the intended 80/443 mapping. The controller
process remains non-root with no privileged container.

RBAC is namespaced to platform-ingress and the two exact app namespaces; there
are no ClusterRoles/ClusterRoleBindings, Gateway/Traefik CRD providers, IngressClass
objects, dashboard or LoadBalancer Service. The explicit Ingress annotation class
is dev-web-saas, because namespaced RBAC disables cluster-scope class lookup.
The upstream controller's namespace-scoped service/endpoint/Ingress/Secret watches
are administrative controller permissions, not an audit identity.

The trusted platform owner must create platform-ingress-reconciler and the two
app namespaces before chart install. Platform SA/owner authorization is separate
from the untrusted feature path and must never borrow lane namespace privileges.

HTTP-01 storage is a dedicated local-path 1Gi PVC mounted at /data. Traefik creates
private acme.json under fsGroup; never log/export it. Feature cleanup must retain
this PVC and the controller. The authorized Dev firewall change is dependency
[GitOps #604](https://github.com/ai-workspace-infra/gitops/pull/604), not duplicated here.
Only enable the app's separate TLS path after exact DNS and HTTP-01 reachability
are proved; do not retry issuance for missing DNS. No DNS token, production DNS,
production certificate or copied private key is used by this controller.
