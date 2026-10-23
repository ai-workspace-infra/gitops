# Selfhost Control Plane deployment and Accounts migration contracts

This page defines the GitOps part of the accepted eight-stage deployment and
upgrade plan. It describes candidate intent, not permission to change a running
environment. This change does not provision resources, deploy services, migrate
data, publish a release, transfer writer ownership, or change DNS.

## Declarations and availability

| Contract | Schema | Illustrative template |
| --- | --- | --- |
| Fresh candidate deployment | [selfhost-control-plane.schema.yaml](../schemas/selfhost-control-plane.schema.yaml) | [selfhost-control-plane.example.yaml](../examples/control-plane/selfhost-control-plane.example.yaml) |
| Accounts migration peers | [accounts-migration.schema.yaml](../schemas/accounts-migration.schema.yaml) | [accounts-migration.example.yaml](../examples/control-plane/accounts-migration.example.yaml) |
| Opt-in target migration listener | [selfhost-migration-listener.schema.yaml](../schemas/selfhost-migration-listener.schema.yaml) | [selfhost-migration-listener.example.yaml](../examples/control-plane/selfhost-migration-listener.example.yaml) |

The templates are **NOT DEPLOYABLE**. They contain `example_only: true`, reserved
`.invalid` domains and visibly invalid `<...>` placeholders. No example image
digest or Playbooks SHA is represented as verified. All declaration schemas reject
`example_only: true`; consumers must also reject it explicitly before obtaining
credentials or performing any runtime action. Replacing pins alone is not enough:
an operator must create a reviewed declaration with the example flag removed.
Consumers must never discover examples by globbing runtime topology directories.

These are versioned service input contracts, not `ResourceMatrix` declarations.
Their root is `schema_version: 1` and `kind`; they do not replace the existing
resource/topology envelope or the environment's canonical resource matrix. The
examples live outside active `resources/`, `topology/`, Compose and Doco-CD paths.
No existing environment declaration is selected or changed by this PR.

The new URL migration lane is initially for isolated integration acceptance.
Documentation must not label it available until the Accounts API, pinned
Playbooks consumer and public entrypoint pass that acceptance together.

## Deployment consumer contract

`install-control-plane.sh` accepts `--config` and `--gitops-ref`; `--check` is a
preflight only. It consolidates the old `setup-selfhost.sh` entrypoint. The
caller resolves an immutable GitOps commit and checks that the supplied config
belongs to that checkout. Reading floating `main` at execution time is forbidden.

The schema requires exactly these desired-state groups:

- `environment`: `sit`, `uat`, or `prod`; a value alone grants no access.
  Fresh SIT uses the same explicit native initialization and default billing-plan
  requirements as UAT/PROD; the consumer must support it without rerouting to UAT.
- `target.host`: a logical key in the environment's external CMDB, never an IP,
  SSH login, provider fact or committed inventory path.
- `release.snapshot_tag`: the immutable coordinated snapshot identity.
- `release.services`: direct registry-qualified `@sha256:` image strings for
  exactly `accounts`, `billing-service`, `portal`, `content-service`, `postgresql`.
- `execution.playbooks_sha`: a literal 40-character lowercase hexadecimal commit.
  The caller must verify it equals the installed Playbooks owner's Git HEAD,
  reject a modified owner checkout, and pin all downloaded execution components.
- `execution.mode: candidate`: installation and candidate verification, without
  source mutation, writer transfer, or traffic cutover.

To support a complete first installation, the Playbooks consumer also requires
`target.generation`, `domain_base`, `console_domain`, `accounts_domain`;
`release.accounts` with the Accounts source SHA, native and Billing schema
checksums, migration version and sorted native business table manifest;
`release.doco_cd` with a digest-pinned controller image, canonical GitOps
repository and distinct application/storage selections; and the explicit boolean
`execution.initialize`. These extend the initial core groups above, without
adding runtime inventory or credential fields. `source.host` and
`source.generation` are optional audit metadata; source and target must not
alias the same host/resource. Migration peer URLs belong to the separate Accounts
contract, and generations never select migration endpoints.

`initialize: true` only permits first initialization after empty/absent database
and no-writer checks; it never allows reset or deletion. Existing initialized
targets require matching owner receipts, cluster identity and schema checkpoints.
Accounts and Console domains are explicit declaration values. Do not construct
or restrict them using generation labels or a fixed alias template. Verify that
Doco-CD's local manifests exist in the pinned checkout. The service
snapshot tag is independent of the selected GitOps commit: the current snapshot
workflow tags service repositories, so do not require a same-named GitOps tag or
compare its resolution to `--gitops-ref`. Verify service provenance against the
coordinated release manifest and GitOps provenance against its own pinned SHA.
Storage is PostgreSQL-only, all application/dependency images must be pinned,
persistent data must match the verified root/dedicated storage profile, and
candidate background writers and external payment/notification effects stay
disabled. No disk formatting or anonymous database storage is authorized.

`execution.storage` supplies optional nonsecret intent when the external CMDB
lacks storage metadata. It requires `profile: root` or `profile: dedicated` and
an absolute `data_path` matching the PostgreSQL bind in both pinned Doco-CD
selections. A root profile uses the host's bundled root filesystem; a separate
disk is not required. A dedicated profile also requires `mount_path` and
`device_path`; `filesystem_uuid` may add an identity guard. The owner verifies
the selected filesystem/device without formatting or clearing it.

The consumer resolves storage from CMDB `storage`, then
`host_vars.control_plane_storage`, then `execution.storage`; legacy CMDB
`data_disk` is accepted as a dedicated profile when none of those is present.
The fallback declares storage intent, not provider facts or permission to create
a disk. An absent CMDB storage profile must not silently select a default disk.

The external runtime inputs are supplied through environment variables:

| Variable | Meaning | Source and validation |
| --- | --- | --- |
| `GITOPS_CHECKOUT` | Local verified checkout containing the declaration | Caller verifies selected GitOps SHA and config containment |
| `CONTROL_PLANE_CMDB` | Operator-provided CMDB artifact path | Playbooks resolves the target and validates environment, host, SSH identity and provenance |
| `CONTROL_PLANE_VARS_FILE` | Operator-provided protected runtime vars path | Playbooks validates required settings and resolves scoped secret references before writing configuration |
| `BILLING_CHECKOUT` | Canonical clean Billing source checkout, required for execution | Owner verifies `release.billing.source_sha`, canonical origin and exact schema bytes |

These local files/checkouts and their machine-specific paths are not fields in the declaration
and must not be committed. The caller bridges `CONTROL_PLANE_CMDB` to the existing
inventory adapter (`AI_WORKSPACE_CMDB_JSON` / `CMDB_FILE`) explicitly; it must not
fall back to an unrelated provider inventory. The existing `cmdb.v1` host records
already provide logical names, addresses, environment, resource identity,
groups and SSH users. No IaC schema or deployed resource change is required for
this contract. A missing, mismatched or ambiguous target fails before SSH.
`target.cmdb_file` and `vars_files` are rejected by the GitOps and owning consumer
contracts. Both operator paths must come through the environment; a repository
file fallback must not be used for CMDB or protected runtime policy. The selected
storage profile is verified against the CMDB-selected host. Dedicated storage
must identify its already prepared device and mount; root storage must reside
on the actual root filesystem. The deployment Role must not invent a disk.

Domain settings, dependency configuration and environment-scoped Vault references
are resolved from the selected GitOps declarations and protected runtime vars.
Tokens, DSNs, keys, addresses and generated CMDB/receipts do not belong here.
Additional runtime dependencies must be explicitly declared and pinned by their
owner; the five mandatory service pins are not permission to install hidden ones.
OCI repository names remain lowercase; an optional tag may contain uppercase
letters and must still be followed by its immutable `@sha256:` digest. The owner
and schema must accept the same image reference grammar.

The release verifier checks the five source commits, successful builds,
registry digests, schema and migration checksums against the same snapshot.
It also checks workflow availability before build dispatch. A tag can exist
while its build is incomplete; neither a tag nor a successful subset of builds
is a deployable snapshot. Never move a published tag; changed source requires
a new immutable revision. Schema validation proves only syntax.

`release.billing` may be omitted for declaration-only preflight, but execution
requires its `source_sha` and `schema_file: sql/billing-service-schema.sql`.
`BILLING_CHECKOUT` supplies a separate canonical clean Billing repository at that
exact commit. The owner verifies SQL bytes against the existing
`release.accounts.billing_schema_sha256`; a path or checksum alone does not prove
that Billing DDL ran. This is first-empty-target DDL only. It must not replay
against an initialized database or invent a default billing catalog/seed.

Ordinary installation does not enable the migration API. A separate
[listener declaration and opt-in Doco-CD selection](selfhost-migration-listener-contract.md)
are needed for the target-side listener; they reuse the same pinned candidate
stack and Accounts image without deploying anything onto the source.

## Accounts peer and authentication contract

`source.url` maps to `--source-url`, and `target.url` maps to `--target-url`.
These are canonical HTTPS Accounts origins, not database connection strings.
`source.allowed_target_urls` must contain the selected target origin, and
`target.allowed_source_urls` must contain the selected source origin. Compare
exact normalized origins, forbid redirects, and verify the resolved endpoint and
actual database identities before export/plan/apply. Reject same-database
migration even if the URLs differ. Do not derive endpoints from generation names.
Network and DNS resolution checks must reject unapproved destinations.

Each endpoint has its own `auth` object:

| Field | Source | Target |
| --- | --- | --- |
| `kv_ref` OR `token_env` | `--source-auth-kv` OR `--source-token-env` | `--target-auth-kv` OR `--target-token-env` |
| `scopes` | Exactly `[source.read]` | `[target.plan]`, optionally also `target.apply` |
| `expires_at` | Issued credential's UTC expiration | Issued credential's UTC expiration |

The two authentication methods are mutually exclusive per endpoint. `token_env`
is only the **name** of a runtime environment variable. There is no plaintext
token argument or shared token field. `INTERNAL_SERVICE_TOKEN` is rejected by
the schema and must never be reused indirectly through another variable or KV
reference. Credentials must be distinct per endpoint, bound to the specific
source/target pair and purpose, and limited in lifetime. `expires_at` is a
declaration of the issued credential's expiry, not a way to extend it.
The resolver verifies the actual scope, peer binding, environment and expiry;
a valid timestamp string or Vault path alone is insufficient. Never log values.
The optional `generation.source` / `generation.target` are audit labels only.

The URL consumer appends the `/api/migrations/v1` routes. Preview is the default;
`target.apply` capability alone never causes an apply. Applying requires explicit
`--apply --plan-id <id> --plan-sha256 <hash>` against the existing task and its
idempotency record. Plans bind source snapshot boundary, target baseline, tool
version, data scope and schema. Conflict, expired plan or changed baseline
requires a fresh preview. Resume by querying the existing result; never blindly
replay an interrupted import. Plan IDs, hashes, payloads and receipts remain
protected runtime artifacts outside GitOps.

Accounts owns a machine-readable table/field contract covering stable identities,
email/password hashes, protected MFA/recovery state, OAuth, Proxy UUIDs, teams,
subscriptions, quotas, usage, invoices, payments, refunds and audit dependencies.
Preserve and verify protected TOTP data in its supported format. Exclude old login
sessions, temporary verification codes and migration credentials. Compare content
and business fingerprints, not just row counts. Identity or same-key financial
conflicts and unsafe target-only business activity stop the migration without
overwriting target facts. No real payment, refund or notification is triggered.

### First compatibility window: current V4

The current V4 → V5 upgrade keeps the reviewed **target-only SSH/database**
migration lane: run the approved migration Role on the verified target, using
protected source read access and target migration access. No new V4 API or source
host mutation is required. The URL peer declaration documents the new API lane;
it is not silently translated into a legacy database operation. An old endpoint
without the migration API returns an explicit unsupported result, with no
automatic fallback, credential widening or alternate URL discovery.

## Eight ordered evidence gates

| Stage | Action and owner | Required passing evidence |
| --- | --- | --- |
| 1 | Prepare GitOps intent | Environment, resource/domain references, source/target identities, immutable pin requirements and scoped secret references reviewed; no secret values |
| 2 | IaC creates resources, or verifies existing CMDB target | Reviewed plan and isolated state for new resources; generated CMDB, environment/resource identity and verified SSH host/user; existing targets must not imply Terraform mutation |
| 3 | Create unified snapshot | All five core repositories built successfully; tag, source commits, image digests, schema and migration checksums fixed; published tags never moved |
| 4 | Playbooks deploys candidate | SSH → pinned Playbook → pinned GitOps → Doco-CD; actual running artifacts match pins; missing credentials fail before writes; same version/config rerun causes no unnecessary restart |
| 5 | Accounts/Playbooks migrates data one way | Target backup independently restored; consistent source snapshot boundary; conflict-free preview; transactional import, target-only data preservation and business fingerprints verified |
| 6 | Complete isolated acceptance | Restore containing business data, full applicable regression, repeat deployment, concurrency, interruption/resume and observation pass; PostgreSQL 17 and CLI/API parity covered |
| 7 | Prepare cutover report | Concrete source writer fencing, final catch-up, writer handoff, DNS/TTL, observation and recovery plan; wait for explicit human confirmation |
| 8 | Execute confirmed cutover and live acceptance | Fence source writes, final catch-up, verify consistency, transfer writer ownership, switch traffic, observe real business and retain recovery evidence |

Fresh deployment runs stages 1–4 and 6; record stage 5 as deliberately skipped
with a reason. It does not silently claim migration or traffic cutover acceptance.
Generation upgrades run all stages. While the source continues serving, record
snapshot boundaries; final catch-up occurs only in stage 8 after source fencing.

Stage 6 includes expired/scoped auth, source write prohibition, illegal peers,
tampered streams, replay, rate limits, rollback, locks, plan expiry, repeat apply,
resume and schema fingerprints. Historical regressions include TLS/public SNI,
shared-token prevention, formal entry rules, Agent registration, VLESS,
OAuth/Webhook, Content, and Exporter → Vector → Billing → PostgreSQL → Accounts.
Observe at least two complete relevant collection cycles and record start/end
times and data freshness. Any mandatory `FAIL`, `BLOCKED` or `NOT_RUN` prevents
cutover; an unperformed check is not a pass.

Receipts link execution ID, GitOps and owner SHAs, fixed artifacts, target identity,
backup/restore evidence, source snapshot, target baseline, migration plan and
regression results. Store production endpoint bindings and receipts in controlled
records, not public documentation. A forward migration does not authorize an
unreviewed reverse migration; recovery must preserve business facts written since
handoff and has its own owner and reviewed plan.

## Scripts, ownership and review order

| Owner | Responsibility |
| --- | --- |
| Services `.github` | Thin `install-control-plane.sh`, `migrate-core-data.sh`, unchanged `setup-proxy.sh` interface (edge node onboarding); argument parsing and pinned owner dispatch only |
| GitOps | Non-secret desired state, schemas, peer policy and documentation; no executable scripts or runtime inventories |
| IaC Modules | Provider resources, DNS, isolated state and generated CMDB |
| Playbooks | Reusable host/service Roles, Vault resolution, deployment, backup/restore, migration execution and runtime verification |
| Accounts | Shared CLI/API data contract, conflicts, transactions, fingerprints, idempotency and migration API |
| Toolkit | Workflow ordering, immutable checkout, identity/approval boundaries, snapshot orchestration and final evidence gates |

Implementation PRs follow Accounts → Playbooks → GitOps → public `.github`
entrypoints. Link companion PRs and test the exact pinned combination. Contracts
can be reviewed as drafts before producers merge; consumers must not be advertised
as usable until the reviewed owner commits exist and isolated acceptance passes.
Keep historical V2/V3/V4 documents in their original time context and link them
to this process. This document does not deprecate a working lane by itself.

## Static validation and its limits

Use a YAML parser and a Draft 2020-12 JSON Schema engine with URI/date-time format
checking enabled. YAML is the only committed serialization, including schemas.
Check the declaration schemas themselves; require reviewed declarations to pass
and all `example_only: true` templates to fail. Also test rejection of missing service
pins, mutable images/owner refs, additional fields, IP hosts, secret fields,
auth-method ambiguity, wrong scopes and invalid origins/expiry syntax.

No executable validator is added here: owning consumers implement these checks
and must fail closed before credentials or mutation. Cross-field peer matching,
same-database detection, environment-bound credentials, future expiry, owner SHA
equality and real artifact provenance require consumer validation. Local schema
checks do not establish API availability, deployment, restore, migration or UAT.
