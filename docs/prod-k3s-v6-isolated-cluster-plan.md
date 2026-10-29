# PROD K3S V6 cold-start and release validation plan

**Default rule:** stateful workloads and SQL schema/data migrations use a fresh target
cluster; never upgrade the business database, Vault Raft, or other business state in
place. Apply a reviewed SQL schema to a fresh target database, then move data only
through an owner-approved migration or verified backup/restore. Data changes can be
difficult or impossible to reverse, so an image/chart rollback or a guessed reverse
migration is not a data rollback.

**Allowed in-place exceptions:** small frontend/API code fixes with no SQL schema,
data-format, or persistent-state migration; and the independently released monitoring
service, provided it remains outside business and billing paths. These exceptions are
scoped to their own release units. Keep pre-change evidence and a recoverable artifact
pin; monitoring data changes still require their own backup/recovery evidence.

Status: reviewable V6 plan. The V6 root, GitRepository, Flux Kustomizations, and
HelmReleases are suspended. No V6 node, DNS record, certificate, service release,
or data migration has been created by this change.

This follows [GitOps PR #648](https://github.com/ai-workspace-infra/gitops/pull/648).
That PR is merged and declared only the isolated Akamai target/state; this follow-up
defines the V6 release units and validation order.

The [V6-specific GitOps hierarchy](prod-k3s-v6-gitops-hierarchy.md) is authoritative
for the root, six Git sources, five unit Kustomizations and seven HelmReleases.

The [node, data-volume and cluster preflight](prod-k3s-v6-node-cluster-preflight.md)
records the current provisioning proposal and source-verified execution gaps. It is
the preparation checklist before any resource creation or cluster bootstrap.

## Current V5 evidence and V6 boundary

The approved read-only check of PROD V5 on 2026-10-29 confirmed the supplied diagram:

- Its single Flux `GitRepository` is `config-prod`, polling every minute,
  pinned to tag `v2026.10.28.5` at commit `ede6e0ebd91df03c24eec55967ea94d1b1aa7b18`.
- The V5 root Kustomization and its Vault, observability, DataKit, and Web SaaS child
  Kustomizations report Ready. They all use that same source and tag. Keep them and
  the V5 source pin unchanged during V6 validation.
- V5 is still `localhost`; the SSH session was UID 0 and its machine ID matched the
  historical V5 value. These are V5 observations, not V6 identity evidence.
- V5 has 2 vCPU and 4,015,960 Ki allocatable memory. At the read time, node memory
  use was 3,239 MiB (82%) and declared Pod memory requests were about 3,340 MiB.
  These historical figures are a capacity observation, not acceptance for V6.

V6 is a separate cluster and state namespace (`prod-k3s-v6`). One cluster-local
bootstrap GitRepository `config-prod` manages its root, and five additional
unit GitRepositories independently pin configuration versions from the same GitOps
repository. All six initially pin reviewed tag `v2026.10.29.4` at merged commit
`c74a1a5a7d3a633d4020897fbb765b3e23fb279a` and remain suspended. They cannot change
V5's objects. Never point production Flux at this feature branch.

The user selected Akamai account `manbuzhe2026`, region `jp-tyo-3`, and
`g6-standard-2` (2 shared vCPU / 4 GB). Confirm current region capacity, account quota,
price, disk requirements, and the rendered V6 request/limit budget in provider preflight
before creating a node. Those provider facts have not been checked in this planning
change. Set hostname `prod-k3s-v6`; verify a newly generated, unique machine ID
after creation. Retain `prevent_destroy: true` and the independent state key
`terraform/prod/svc.plus/akamai-cloud/manbuzhe2026/prod-k3s-v6/terraform.tfstate`.

The user approved temporary IPv4 SSH ingress from `0.0.0.0/0` for bootstrap. IPv6
SSH remains closed, as does public K3s API ingress. Use key-based operations access
and replace the temporary IPv4 rule with the operator allowlist after bootstrap.

PROD requires a separate data disk. The V6 declaration now includes one new 100 GB
ext4 Block Storage volume in the same region, owned by the V6 state. This is distinct
from the instance system disk. Before service deployment, verify the volume identity,
mount it at `/data`, and route V6 persistent volumes under `/data/k3s/storage`;
never fall back to the system disk if the data mount is missing. The current IaC
volume-protection/CMDB and Playbooks V6 mount integration gaps remain blockers, as
described in the linked preflight. No volume has been created or mounted.

## Five release units

The V6 root uses its bootstrap GitRepository and manages five independently pinned
unit GitRepositories plus the five child Kustomizations below. Each unit has its own reconciliation path and
one or more HelmReleases whose chart version or artifact digest can be selected
independently. The observability unit has separate
HelmReleases for its stack, reusable agent, and DataKit because these are separately
published charts. Stateful business HelmRelease pins must not be changed on a cluster
that already owns their persistent data. The standalone monitoring service and small
frontend/API fixes follow the explicit in-place exceptions above.

| Order | Flux Kustomization / namespace | Managed release and V6 pin | V5 comparison / validation purpose |
|---:|---|---|---|
| 1 | `vault-prod` | HashiCorp Vault Helm chart `0.32.0`; server image `1.21.4` | Fresh V6 Raft store; same Vault server version as V5 while validating chart ownership. Do not copy V5 Raft data or recovery keys. |
| 2 | `postgresql-prod` | Shared `distributed-web-saas-fullstack` OCI package; independent `postgresql` HelmRelease | Fresh empty database/PVC and reviewed target SQL schema. Deploy does not import data; core data is copied later with the approved `migratectl` workflow. |
| 3 | `ingress-prod` | Shared `distributed-web-saas-fullstack` OCI package; independent `caddy-ingress` HelmRelease | Caddy-only reverse proxy with explicit cross-namespace upstreams; new producer contract/digest required before activation. |
| 4 | `observability-prod` | Stack OCI digest `sha256:61e414722d21bbf4ace63d54c7236de30af5ff54d3878dcb5c8da8999894c706`; agent OCI digest `sha256:4095ed924194c7a91aaa2ad00dd21cec3ccfdcd4c342951ac95aec56fe041f12`; DataKit chart `2.16.1` | The stack digest is the newer main-branch pin; compare with V5's live digest `sha256:6cf607b36fa0c92fd14f06d4db5186242dba85b7171757257242c0c6f90162a0`. Agent and DataKit remain on their current pins until newer artifacts are selected. |
| 5 | `web-saas-prod` | Full-stack OCI digest `sha256:6336235445e389958660cc344eead488ad3a50cf67afb1301fd35f6793720f27` | Current V5 chart baseline; embedded PostgreSQL and app-bundled Caddy are disabled in favor of the separate units. This validates V6 compatibility, not a Web SaaS artifact upgrade; advance only after a newer producer digest is published and reviewed. |

The unit boundaries follow the requested ownership: Vault and its identity/storage;
collectors, monitoring storage, dashboards and probes; Caddy/TLS references/routing;
PostgreSQL and its Service/PVC/configuration; then business Deployments/Services/app
configuration. All five live in the same GitOps repository. The selected chart pins
above are explicit candidates. A root configuration tag selects the management graph;
each unit configuration source retains its own tag until explicitly advanced.
Independent configuration and artifact pins allow a release unit to be updated without
changing the other units. Use the in-place exceptions only for the frontend/API
code-only patch or the independent monitoring service; business state, billing state,
SQL schema transitions, and persistent workloads outside those exceptions require a
fresh target.

## Upgrade rules by change class

| Change class | In-place rollout | Required boundary |
|---|---|---|
| Frontend UI | Allowed for UI-only, stateless changes such as layout, styles, and browser assets. Roll out the immutable frontend artifact and verify page load, key flows, and error rates. | No API contract, SQL schema, business data, or persistent-volume format change. If UI ships in the combined Web SaaS artifact, update only `web-saas-prod` and retain its prior immutable pin. |
| API | Allowed for small, backward-compatible code fixes that work with the current API contract and database schema. Roll out only the affected release unit, then verify health, representative requests, regressions, and error rates. | No SQL schema/data migration, incompatible contract change, or mutation of persistent state formats. Keep an artifact pin for application rollback; this does not undo data writes. |
| DB | No in-place version upgrade, SQL schema version transition, or data migration on the existing generation. Create a fresh cluster and empty target database, apply the reviewed SQL schema, validate backup/restore, then migrate required core data with the approved `migratectl` flow. | Keep the source database and writer unchanged through acceptance. Do not use a guessed reverse migration or image rollback as data rollback. Final writer/traffic cutover requires a separate reviewed operation. |

The independent monitoring service is an additional explicit exception: it may be
upgraded in place when it remains outside business and billing paths. Pin and update
its own release unit, retain pre/post health and regression evidence, and capture a
recoverable backup for any monitoring data it owns. This exception does not permit
in-place business/database schema changes.

## Cold start, data migration, then next-generation validation

1. Keep the V6 root and all five child Kustomizations suspended. Select an immutable
   production tag that contains these paths for V6's cluster-local
   `config-prod`; V5 remains pinned at its own tag. Complete provider/state,
   firewall, hostname, machine ID, storage, and rendered capacity preflight.
2. After the separate IaC provisioning approval, cold-start V6. Establish the three
   identity classes, initialize fresh Vault Raft storage and an empty PostgreSQL
   database, then deploy all five release units in dependency order. Turn on one child
   Kustomization at a time and wait for Flux readiness, HelmRelease readiness, health
   probes, TLS and cross-namespace routes before enabling the next unit. Keep business
   write/background workers disabled during validation. Recreate required V6 Vault
   secrets through their owning secret workflow; do not copy V5 Raft state or
   recovery keys. Start observability storage fresh; moving historical telemetry
   requires its own reviewed backup/restore plan.
3. Before migrating data, pin the exact Accounts `migratectl` binary/source, image
   digest, Accounts schema checksum, Billing schema checksum, source checkpoint and
   target baseline. Create an encrypted target backup and prove it restores into an
   isolated database. Obtain a source read-only credential through the owning secret
   path; never place DSNs or credential values in Git, argv, or receipts.
4. Keep all V6 business writers and background workers paused before any full-business
   compare, dry run, or apply. Run `migratectl compare-full-business` (read-only)
   against V5 and the empty V6 target; review its privacy-safe diff and schema/version
   preconditions. Then invoke `migratectl copy-full-business` in dry-run mode and
   review the exact candidate scope. The current Accounts CLI describes this as a
   guarded 53-table business scope; record the actual tool version and confirm its
   table list covers every required core owner before applying. Accounts
   `migratectl diff` alone compares core user identity fields and is not a
   full-business migration.
5. Apply the reviewed migration only through its execution-owning Playbooks/Toolkit
   path, with target writers independently confirmed paused and the tool's required
   write gate present. The source connection remains read-only. Do not treat the
   initial snapshot as zero-lag synchronization while V5 continues to write. Record
   the exact source snapshot boundary and candidate receipt.
6. Validate counts and checksums/identity-level diffs, schema checkpoints, permissions,
   application reads, and incident regressions. Take a populated V6 backup, restore it
   into an isolated target, and verify the restored data and app connection. The
   full-business apply requires an empty target and is not a repeatable import into a
   populated target. After success, use `compare-full-business` to verify equality.
   If execution is interrupted or its outcome is uncertain, compare first; retry the
   copy only after proving the atomic transaction rolled back and all scoped target
   tables remain empty. Missing table owners, conflicts, restore failures,
   source/target drift, or unexplained writes are blockers; do not reset the target or
   overwrite source-only facts.
7. The five V6 units are deployed one at a time as part of the cold start. This staged
   order is the V6 release rollout; it does not upgrade V5 in place. Once V6 cold
   deployment and migration acceptance are complete, freeze its accepted pins and
   evidence as the source-generation baseline. After that, a small frontend/API
   code-only fix or the independent non-business/non-billing monitoring service may
   update its own HelmRelease pin in place, with pre/post health and regression
   evidence and a known artifact rollback pin. Do not combine those updates with SQL
   schema changes or business/billing data-format migrations.
8. Validate the next application/platform version on a separate fresh target cluster
   (for example, a future V7), with its own IaC state, cluster-local Flux source pin,
   five independently pinned release units, and unique identity. Deploy that target
   from cold state one unit at a time, then run the approved `migratectl` data-copy
   workflow and the same backup/restore, reconciliation, regression, and recovery
   gates. Do not change V6 business/stateful HelmRelease pins to simulate a
   new-generation upgrade. The two explicitly allowed in-place exceptions remain
   limited to the frontend/API code-only patch and the independent monitoring service.
   For each stateful component, document whether its data is migrated, restored, or
   intentionally reinitialized, and prove the chosen path before the new generation
   can accept writes. Apply the reviewed SQL schema to the new empty PostgreSQL target
   before `migratectl`; do not mutate the prior generation's schema to perform the
   upgrade. Each generation needs a fixed immutable source tag and artifact digests
   before deployment; a shared Git repository is still acceptable.
9. The current Web SaaS chart digest matches V5, so its V6 cold deployment is a
   compatibility baseline, not a Web SaaS artifact upgrade. Do not report an app
   version upgrade as passed until a newer immutable producer digest is available and
   validated on a fresh target generation. Keep V5 serving and keep canonical
   DNS/writer handoff outside this plan; any final catch-up, source-writer fence, or
   traffic cutover needs a separate reviewed operation.

This plan specifies the migration stage but does not run it. An actual data apply
requires a separate execution request after the target backup/restore evidence and
the complete core-data owner list are reviewable.

## Identity and security gates

- **System administration:** a dedicated, audited operations identity manages the
  host/K3s control plane, storage recovery, Vault initialization, and PostgreSQL
  DDL/restore. Root is setup/break-glass only and never runs applications, collectors,
  or scheduled business jobs.
- **Business runtime:** each service gets a distinct Kubernetes service account and
  Vault-backed credential. PostgreSQL grants only required per-service DML; no
  application role receives `SUPERUSER`, `CREATEROLE`, `CREATEDB`, `REPLICATION`,
  `BYPASSRLS`, ownership, or server-file/program privileges. Enforce non-root UIDs,
  no privilege escalation, dropped capabilities, read-only root filesystems, and
  explicit writable paths after each image is compatibility-checked.
- **Audit:** a separate revocable Kubernetes identity reads only approved status,
  events, and metrics; it cannot read Secrets, exec/attach/proxy, mint tokens,
  impersonate, escalate, or write. A separate database role reads only approved
  masked views and has no write or role-membership path. Allowed and denied actions
  must be checked using the actual identities before claiming enforcement.
- GitOps stores references only. Playbooks/Toolkit own account creation, RBAC,
  PostgreSQL grants, Vault policies and actual runtime checks. This plan does not
  create those identities or claim their controls have passed.

## V6 routing and TLS

Reserve only V6-specific test names: `console-k3s-v6.svc.plus`,
`accounts-k3s-v6.svc.plus`, `billing-k3s-v6.svc.plus`, `content-k3s-v6.svc.plus`,
`vault-k3s-v6.svc.plus`, and `observability-k3s-v6.svc.plus`. Do not declare
canonical aliases (`console.svc.plus`, `accounts.svc.plus`, `billing.svc.plus`,
`vault.svc.plus`, `observability.svc.plus`) for V6.

Caddy in `ingress-prod` is the public HTTP(S) reverse proxy, deployed through the
same `distributed-web-saas-fullstack` chart package as PostgreSQL and Web SaaS.
Its independent `caddy-ingress` HelmRelease enables only Caddy, with explicit
cross-namespace upstream FQDNs in `caddy.externalBackends`; it does not install
an Ingress API controller or route by `ingressClassName`. TLS Secrets remain in
`ingress-prod` and are synchronized by ESO from the reviewed V6 Vault paths.
Vault and observability routes use the chart's explicit additional-host upstream
contract, with verified backend ports and CA trust before activation. Do not copy
V5 certificates. The standalone-Caddy producer change must be released and pinned
before this release is enabled.

PostgreSQL has no public hostname, LoadBalancer, or Ingress. Applications connect
over TLS to `postgresql-postgresql.postgresql-prod.svc.cluster.local:5432` using their
own roles. Future remote administration requires an approved private XConnect/stunnel
route and a separate operations identity. IaC owns any later V6 DNS records and
firewall exposure. This plan declares no DNS records and does not switch canonical
routing.

## Recovery and out-of-scope work

Do not roll back a stateful business release by changing its chart/image pin on the
same cluster or reversing SQL schema changes in place. Before any data migration or
target write, retain a protected backup and prove restore into an isolated target. If
validation fails, pause the affected target writers and preserve the target, logs,
receipts, and source snapshot boundary for review; do not reset, truncate, or overwrite
data to make a retry pass. Recover by restoring a verified backup into a separate
fresh target or by a separately reviewed owner-run recovery plan. The allowed
frontend/API and monitoring updates may return to a known artifact pin, but this does
not reverse any data or storage-format change.

Keep V6 credentials, state, and data separate; do not silently fall back to V5 admin
or business identities. V5 remains the serving source and writer during this plan.
Once a target accepts writes, those changes do not flow back automatically to V5.
Any writer transfer, final catch-up, reverse/reconciliation strategy, or traffic
cutover needs its own reviewed data recovery and change plan.

Production writer transfer, canonical DNS changes, V5 service retirement, and the V5
monitoring publication handled by the original task are outside this validation. A
later cutover requires its own approval and evidence record.

## Automatic post-IaC host preparation

The reviewed V6 caller runs Playbooks `vhosts/common` after verified IaC output for both `infra` and `deploy`. `infra` requests common-only without initializing storage or installing K3s; `deploy` must pass the same node identity and audit checks before storage and paused-cluster bootstrap. `plan` does not connect to the host. Existing K3s identity, PV hostname affinity or active Flux conflicts stop the operation; no automatic node rename or PV rebinding is allowed. Canonical CMDB/inventory, OS and K3s identity is `prod-k3s-v6`; service FQDNs are aliases. Fixed owners and actual execution results are recorded in the [preparation evidence](prod-k3s-v6-node-cluster-preflight.md).
