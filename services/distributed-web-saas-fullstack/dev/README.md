# Complete non-production web-saas

Original task: [XConnect referral](https://github.com/ai-workspace-services/accounts/blob/8d1b09a6f2022af221b2a817d516952af41ced0e/docs/tasks/xconnect-referral-completion-20261025.md).
This is a new candidate revision after #599/#602. Those branches are not changed.

Both namespaces run the complete existing six-component single-container-console
profile: Caddy, Console (Next SSR **and** static Nginx), Accounts, Billing, Content
and PostgreSQL. The chart's optional edgeGateway/stunnel profiles remain disabled,
as in the established complete deployment profile. Router #35 is historical
external-Worker baseline, not a container quietly substituted into this profile.

| Stage | Namespace | Console / Accounts / Billing hosts |
|---|---|---|
| temporary SIT | feature-xconnect-referral-sit | xconnect-referral-sit.onwalk.net / accounts-xconnect-referral-sit.onwalk.net / billing-xconnect-referral-sit.onwalk.net |
| persistent UAT | web-saas-uat | web-saas-uat.onwalk.net / accounts-web-saas-uat.onwalk.net / billing-web-saas-uat.onwalk.net |

All public URL, OAuth callback, APP_BASE_URL and NEXT_PUBLIC_APP_BASE_URL values
use onwalk.net. Production svc.plus hosts are not configured or changed. Internal
service/DB names are namespace-qualified. Content's knowledge revision is pinned;
its cache and each namespace's PostgreSQL volume are independent. Accounts uses
in-process session storage and its own signing keys; Portal receives an onwalk.net
request host and both explicit onwalk base URLs, so its legacy svc.plus-wide cookie
branch does not apply. Real login/logout/MFA responses still need runtime tests.

## Immutable published inputs

Chart 0.2.5 is pinned by OCI digest in each OCIRepository. `release.yaml` is a Helm
values overlay consumed as the last HelmRelease valuesFrom entry, not an inert
release ledger. Every component has an immutable image and actual PodTemplate
annotations `release.svc.plus/source_repository`, `source_sha`, `image_digest`,
`build_run_id`. The reviewed release writer updates these and the image atomically:

- `caddy.image`, `postgresql.image`, `console.singleContainer.image`
- `{accounts,billing,content}.workload.image` and matching `.workload.env.IMAGE`

The six source/digest bindings were checked against the exact retained publishing
run logs: Caddy 30419099530, Console 40256113380, Accounts 40222728214, Billing
40222731605, Content 40222734705 and PostgreSQL 40222746656. Chart publishing run
40212878369 uses source 1d3812d386924105498afefbe3c1ad3e418fd90a. PostgreSQL is a new
candidate c6ee94d4... from source 5920028c..., not the unproven old 56f4179b digest.
SIT Accounts now uses the actual unmerged [Accounts #279](https://github.com/ai-workspace-services/accounts/pull/279)
preview at source `450ab9940071883139d4a73e6cfd2f4b77d193ba`, publisher run
`40378515318`, digest `sha256:97a58ebe7fab56432777591604491c2dea7fc7cc57cd35820fedef78fa328572`.
Its authenticated publisher job and OCI source/revision/platform labels were checked.
UAT retains the main Accounts baseline above until a merged-main release exists;
the other five components are unchanged. Accounts #277 remains historical business
baseline and cannot be retrospectively claimed as a pre-merge SIT test. The native
schema source/hash remains reviewed 8d/e223; #279 changes the publishing proof.
A changed image/config/data baseline requires new candidate evidence.

## Trusted owner and persistent main

The application paths contain **no** Namespace, RBAC or Secret-value objects.
The reviewed deployment owner creates the fixed namespace/labels and restricted
`lane-reconciler` identities. HelmRelease explicitly uses that identity.

SIT consumes a fixed full PR commit at
`./services/distributed-web-saas-fullstack/dev/sit-xconnect-referral`; it must not
merge first, redirect the platform root to an arbitrary PR or execute PR scripts.
UAT uses its own unique persistent GitRepository with **ref.branch: main** and
`./services/distributed-web-saas-fullstack/dev/uat`. Its initial observed source
and applied revision must equal a freshly sampled current main SHA; subsequent
main changes reconcile automatically and invalidate earlier PASS. There is no
second root/UAT watcher here and no persistent feature-branch UAT. A main source
must not start against this path until the reviewed UAT declaration exists on
main. The application-main publishing → verified digest → reviewed GitOps main
writer is a separate required control-plane dependency, not claimed complete by
a `branch: main` string.

## HTTP first, DNS-gated TLS

One platform-owned Traefik controller serves both namespace Caddy ClusterIP
services; neither stack reserves host ports. Base paths include HTTP ingress
only. The corresponding `tls/` path contains HTTPS ingress using the fixed
`dev-http01` ACME resolver. It must be enabled only after the DNS owner confirms
all exact A records match the current Dev resource and HTTP-01 is reachable.
Missing DNS or HTTP reachability means TLS NOT_RUN, not repeated issuance.
Traefik owns persistent private `/data/acme.json`; no Cloudflare token or copied
TLS key is placed in a business namespace. Feature cleanup excludes the platform
controller, its ACME PVC and persistent UAT.

## Required owner materialization

These are names/fields, not stored secret values:

- `web-saas-registry`: dockerconfigjson generated by the authorized owner from
  Dev `kv/CICD/dev/ghcr` fields GHCR_USERNAME/GHCR_TOKEN. Five service packages are
  private; Caddy/chart are public. Each namespace receives its own Secret object.
- `web-saas-db-admin`: `password`, for the PostgreSQL initializer/admin only.
- `web-saas-accounts-runtime`: DATABASE_URL for the namespace-qualified PostgreSQL
  service, account database and xc_accounts_rw role (password remains runtime-only),
  plus POSTGRES_PASSWORD for the template and signing fields
  AUTH_TOKEN_PUBLIC_TOKEN/AUTH_TOKEN_ACCESS_SECRET/AUTH_TOKEN_REFRESH_SECRET,
  AGENT_API_TOKEN, a namespace-random ROOT_BOOTSTRAP_PASSWORD for the mandatory
  application bootstrap (not a seeded review user), and DATABASE_IDENTITY_SHA256
  matching the managed DATABASE_URL.
  DATABASE_RUNTIME_ROLE=primary requires DATABASE_URL explicitly; the template
  store.dsn is not the managed runtime override. ConnectionIdentity hashes JSON
  Host/Port/Database/Role (not the password); it is a routing fingerprint, not
  physical database identity or business acceptance. Verify the actual DB separately. Optional
  Sandbox STRIPE_SECRET_KEY/STRIPE_WEBHOOK_SECRET must derive only from authorized
  SANDBOX_* Dev fields. No live payment/payout key is permitted.
- `web-saas-console-runtime`, `web-saas-billing-runtime` and
  `web-saas-content-runtime`: namespace-specific INTERNAL_SERVICE_TOKEN; Billing
  additionally needs DATABASE_URL for the same namespace account DB, using its
  separate xc_billing_rw role. The real Billing schema references Accounts users;
  no cross-database users mirror or FDW is created.
- The trusted DB owner must create/migrate each namespace account database, separate
  DDL owners from business DML roles and prove DDL refusal before business PASS.
  The PostgreSQL chart alone only initializes lane_admin/account. A SecretRef is
  not proof that a role, schema, identity or permission exists. No known default
  review password or production bootstrap account is enabled. SMTP is deliberately
  non-delivering until a separately authorized non-production mail source exists.

## Isolation and rendered fixes

All six rendered processes satisfy restricted Pod Security. Exact postRenderers
add PostgreSQL capability dropping and Caddy seccomp, restrict the chart's otherwise
wide Caddy ingress policy, and bind the final Caddyfile checksum to the actual
replacement content. Console keeps the complete image entrypoint with non-root
Nginx writable paths; its Next PORT is 3000 and Nginx remains on 8080. Console-host
API requests reach the Portal BFF instead of bypassing session handling to Accounts.
Account-template/Nginx checksums trigger rollout when their contents change.

NetworkPolicy allows namespace peers/DNS only, with explicit Accounts TCP443 to
Stripe's published API ranges and Content TCP443 to GitHub's published Git ranges.
These are vendor-published configuration ranges, not copied Dev instance addresses.
Sources: [Stripe IP ranges](https://docs.stripe.com/ips), [GitHub meta API](https://api.github.com/meta).
This does not claim external SMTP/OAuth, real Stripe tests or cross-service business
acceptance have run.
