# SIT feature domain contract

This declarative contract complements the current referral lane record. It does not trigger DNS or Kubernetes operations.

Feature IDs use `feature-<lowercase-slug>`. A lane namespace is `feature-<slug>-sit`. The console host preserves the established `<slug>-sit.onwalk.net` shape; Accounts and Billing use `accounts-<slug>-sit.onwalk.net` and `billing-<slug>-sit.onwalk.net`.

DNS records are owned by IaC and target the current Dev ingress IP from fresh CMDB. An unowned conflicting record blocks publication. The shared ingress is owned by Playbooks and only serves explicitly registered namespaces. HTTP and TLS/application health must be observed before a lane is reported accessible. Per-feature cleanup is limited to exact owner-tagged records and the authenticated namespace incarnation after evidence is archived.

This contract is not consumed by the current static Toolkit and Playbooks caller yet. Dynamic feature-directory rendering, trusted namespace registration, ingress watch/RBAC lifecycle, and caller wiring remain prerequisites.
