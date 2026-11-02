# Accounts migration listeners: source and isolated target

These are optional Flux units, independent of ordinary application readiness.
The source and target share an explicit job UUID but distinct audience and staging
keys. The target has a separate PostgreSQL17 instance and 2Gi PVC; staging uses
separate 1Gi PVCs. No existing Accounts database or application DATABASE_URL changes.

Only `/api/migrations/v1` and `/api/migrations/v1/*` are routed to the TLS listener.
The original Accounts routes continue through their ordinary upstream. The V6
listener resolves the source origin through the WireGuard V5 address. Verify that
path from the actual target Pod before snapshot acceptance; a host probe alone is
not Pod connectivity proof. TLS SNI remains the source hostname.

Apply sequence after producer/consumer PR review:

1. Merge the Playbooks identity owner and this GitOps declaration. Flux creates
   the namespaces, PVCs and workloads; missing Secrets intentionally block startup.
2. Use the exact clean approved GitOps SHA with `accounts-migration-identity.yml`.
   Run `secrets` for each `operations/accounts-migration/{source,target}.yaml`.
   This persists random server-side materials in the declared Vault path and
   copies the existing public TLS certificate into the migration namespace.
3. Run target `init`. It waits for the independent PostgreSQL, refuses a populated
   candidate, and runs the fixed native initializer Job. No candidate writer exists.
4. Run `permissions` on both sides. The source operation requires explicit
   credential rotation approval for the existing readonly_release role. Review
   other consumers first; the existing business application uses another role.
5. Reconcile/wait for each listener. Check unauthenticated requests are 401,
   configured service tokens work, invalid credentials are 401, and the target
   Pod can access the source over the pinned WireGuard path.
6. Run transfer-api without --apply. Record source snapshot boundary, plan ID,
   hashes, table counts, conflicts, and resumable restart verification. Do not
   report a 401 or Ready Pod as a successful snapshot/preview.

The native-init Job YAML is deliberately excluded from Kustomization; only the
owner's explicit empty-candidate initialization phase creates it. There is no
backup receipt, receipt initialization or apply capability configured. The target
migration role has only scoped candidate DML/TEMP permissions, no database admin
attributes. Source RLS SELECT policies are added only for declared migrated tables.

Secrets reference Vault material; no values are present in this repository. TLS
copy is a migration-window snapshot, not a certificate-rotation controller; rerun
secrets after certificate renewal. Do not rotate staging keys while retained
snapshots/plans still need them.

Rollback removes the precise Caddy route and scales listeners down through GitOps.
PVCs and the optional Flux unit use no automatic pruning; preserve all candidate
and encrypted staging material for audit. Deletion, apply and DNS cutover are
separate operations.
