# SIT K3s V6 replacement candidate

This is a separate Flux root for a fresh single-node SIT environment. The root
and source can be handed over together; the cluster identity RBAC stage is
active for bootstrap acceptance and all workload stages are suspended by default. The source is pinned to the reviewed commit by the Playbooks handover,
and its SSA policy preserves that pin during reconciliation. Stage promotion
requires review of the changed suspend state and a new pinned candidate.
ExternalDNS, shared public routes, QMD, the AI gateway and remote desktop are
outside this graph.

## Execution inputs

Use bootstrap-vars.yaml with the existing Playbooks owner entrypoint. Before
running it, bind an attested single-target inventory, an unused Pod/Service CIDR
pair and DNS address, the exact GitOps checkout and commit, and a receipt path.
Reconcile the existing Fedora OS identity collision and prepare the candidate
hostname and directory in the explicit common profile. The node's local-path
provisioner must report /data/k3s/storage as its actual path. Check that the
storage class can allocate and mount a fresh PVC on the expected filesystem.
Retain the existing remote desktop listener. Supply the reviewed
40-character GitOps commit as k3s_identity_rbac_revision and a distinct
identity Vault writer credential; do not begin until the candidate writer
authorization and real-identity allow/deny checks are ready. The identity
stage reuses the pinned SIT RBAC definitions and must reconcile before
identity credentials are issued.

Populate flux-system/sit-replacement-runtime with REPLACEMENT_OVERLAY_IP from
the attested XConnect One assignment. The ingress stage requires the ConfigMap.
Validate the required key, address syntax and target interface ownership before
resuming it. Its ClusterIP Service uses externalIPs with ServiceLB disabled.
Verify packet handling from the overlay and rejection from out-of-scope
interfaces before approving the route.

## Stage order

1. Bring up the candidate control plane and hand off the fixed Flux root.
2. Install ESO and check its CRDs, webhook and controller. Establish the
   dedicated JWT mount from the candidate Kubernetes
   issuer and live signing keys. Apply only candidate roles and policies after
   node/cluster attestation. Provision the candidate KV records with the
   corresponding service and TLS owners. Check each projected ServiceAccount's
   allowed read, wrong audience, wrong subject and adjacent-path denials.
3. Resume storage, VPA and Traefik. Resume PostgreSQL and observability after
   their prerequisites are ready. Verify fresh PVCs and see candidate-labelled
   samples through Grafana. Observability writes to the candidate vmauth service
   over the cluster network. DataKit and inherited public probes are deferred.
4. Resume MCP and Web SaaS. Validate fresh account/billing schemas, separate
   runtime DB roles and sandbox payment configuration before Web SaaS startup.
   OAuth sandbox remains pending. MCP candidate covers observability tools.
5. Resume HTTPS routes after the upstreams and ESO TLS Secrets are ready.
   Compare stored and presented certificate chains and SANs, then run host and
   business probes through the overlay. Public DNS handoff requires an approved
   reachability path and independent external acceptance.

Workload Vault roles and ACLs are in security/vault. They require live issuer
and signing-key binding, approved Vault execution credentials and secure
provisioning of the referenced values. Kubernetes human identities use a
separate credential path and require their own signed allow/deny receipts.
A successful static render does not establish cluster or application readiness.
