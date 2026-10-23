# Opt-in candidate target migration listener

This is a separate `schema_version: 1`, `kind: selfhost-migration-listener`
contract. Ordinary candidate installation does not start a migration listener or
initialize its receipt schema. Source V4 stays on the reviewed legacy path;
declaring its URL never deploys an API or changes data there. An unsupported
source API fails explicitly without fallback.

The [schema](../schemas/selfhost-migration-listener.schema.yaml),
[listener template](../examples/control-plane/selfhost-migration-listener.example.yaml),
[Compose overlay](../examples/control-plane/migration-listener.compose.example.yaml)
and [Doco-CD selection template](../examples/control-plane/doco-migration-listener.example.yaml)
are generic review inputs. They are **NOT DEPLOYABLE**: the listener template
has `example_only: true`; Compose/Doco templates have `x-example-only: true`;
pins, job identity, networks and stack paths are unpopulated placeholders. No
active resource, source V4 selection or root `.doco-cd.*` file references them.
The owning consumer must reject example markers before credentials or actions.

## Declaration and immutable selection

`control_plane_config` is a GitOps-root-relative reference to the reviewed
candidate declaration. It supplies the environment, exact CMDB target, candidate
mode, service digests, storage and installed Playbooks SHA. It must remain in
the selected checkout, including symlink resolution.

`doco_target` names a **distinct opt-in** root `.doco-cd.<target>.yml` selection.
That selection includes all reviewed candidate stack files plus the migration
overlay, at the same immutable GitOps SHA passed as `--gitops-ref`. All five core
pins and dependency pins still apply. The normal application and storage
selections stay separate; `remove_orphans: false` prevents implicit cleanup.
Do not select an overlay alone or add it to a serving/source selection.

The Doco template's target stack path is deliberately unresolved. After the
producer implementation is reviewed, populate real pins and exact candidate
files in a separate reviewed declaration, remove the example markers, and put
the opt-in manifest/overlay at the paths checked by that pinned owner. Preserve
the complete existing Caddy config/TLS mounts when combining Compose files.
No Role generates or substitutes a second Compose declaration.

`listener` declares the approved source URL, distinct source/target audiences,
approved job UUID, exact peer/client CIDR allowlists, dedicated receipt owner
and the explicit `apply_enabled` / `initialize_receipts` booleans. Both default
to false and must be supplied explicitly. A job UUID is an authorization binding,
not a generated migration plan or execution receipt.

The consumer verifies canonical CIDRs, actual resolved source addresses, distinct
endpoints and the Accounts job/audience/operator binding. Networks must be at
least IPv4 /24 or IPv6 /64; broad, unspecified, multicast or malformed networks
are rejected. Client CIDRs include the precise local loopback network needed
for the trust-verified local SNI/unauthorized probe and the approved operator
networks. Allowlists are policy, not observed cloud IP facts.

## Compose and Caddy boundary

The service key is `migration`, with `container_name: web-saas-migration-listener`.
It must use exactly `release.services.accounts`, including its verified digest,
and the list entrypoint `[/usr/local/bin/migratectl]`. Its list-form command must
equal the pinned Playbooks listener owner's `arguments(listener)` output; do
not introduce a shell, alternate executable or floating download.

The pinned CLI's default listener binds loopback port 9097. The explicit
`--allow-loopback-http` flag is only for this private local reverse-proxy hop.
The sidecar shares `network_mode: service:caddy`, publishes no ports, declares no
additional networks or inline environment, and loads only
`/run/control-plane-migration/listener.env`. It runs with a read-only root,
`user: '0:0'`, all capabilities dropped and `no-new-privileges:true`; the owner
enforces this exact envelope and file permissions.

Staging is a persistent bind from `parent(storage.data_path)/migration-stage`
to `/private/target-stage`, with `create_host_path: false`. It contains protected
encrypted resumable data and must survive a listener restart. No credential or
staging payload is committed to GitOps.

The Caddy service is `web-saas-caddy`. Its overlay explicitly binds
`/run/control-plane-migration/route.caddy` read-only at
`/etc/caddy/migration-listener.caddy`, also with `create_host_path: false`.
Playbooks renders that route and the reference-only runtime environment from
approved external inputs. The native candidate Caddyfile imports
`migration-listener*.caddy` before its ordinary read-only candidate rule, so the
narrow authenticated migration routes are evaluated deliberately. Only the
reviewed route and CIDRs may expose the loopback API; no generic proxy bypass
or source-host modification is implied.

## Runtime references, preview and apply

`CONTROL_PLANE_CMDB` and `CONTROL_PLANE_VARS_FILE` remain external inputs to the
associated control-plane contract. `CONTROL_PLANE_MIGRATION_VARS_FILE` supplies
a protected reference-only migration policy for the dedicated target DSN,
signing key and distinct staging key. These identities are independent of
business roles and `INTERNAL_SERVICE_TOKEN`; actual values resolve at runtime
under the owner and never enter GitOps, evidence or command arguments.

Preview declares `apply_enabled: false`, `initialize_receipts: false`, and no
`receipt_file`. Its Compose selection contains no backup receipt mount or
receipt-initialization/apply-enabling flag. Listener enablement does not call
`transfer-api --apply` or import business rows.

An apply-capable listener requires explicit `apply_enabled: true` and an
existing target-only `receipt_file`. `CONTROL_PLANE_MIGRATION_RECOVERY_FILE`
supplies the protected complete owner proof, backup/archive references,
checksums and exact plan binding. These generated runtime facts must not be
embedded as `listener.recovery` or copied into GitOps. The owner validates the
proof, independently verified isolated restore, target identity/baseline, plan and expiry
before enabling apply. The reviewed Compose selection adds only the existing
receipt at the same absolute host/container path, read-only with
`create_host_path: false`, and the matching backup-receipt CLI flag.

`initialize_receipts: true` additionally requires apply eligibility and an
explicit dedicated target receipt owner; it never initializes a source schema.
Even an apply-capable listener requires the separate explicit reviewed plan
ID/hash operation to mutate business data. Missing evidence fails closed.

## Ownership and acceptance

Accounts owns API/authentication, encrypted chunks, plan/transaction/idempotency
semantics and the executable. Billing owns reviewed Billing DDL. GitOps owns
these declarations and reviewed Compose/Doco selections. Playbooks owns runtime
reference resolution, target listener/Caddy setup, receipt gates and probes.
Toolkit/public dispatchers pin and invoke those owners; IaC remains the owner
of cloud/DNS/state and CMDB.

Schema/selection checks prove no live readiness. Required isolated acceptance
includes same-image listener startup, private staging and restart/resume,
unauthorized/illegal-peer refusal, trusted SNI routing, preview without business
writes or receipt DDL, backed-up target apply and exact committed retry. Fixed
source V4, DNS/writer handoff, real payments and production remain outside this
declaration change.
