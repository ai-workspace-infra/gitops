# Versioned Selfhost public-domain cutover

This contract lets `web-saas-prod-v2`, `web-saas-prod-v3`, and later control
planes evolve behind the original Selfhost Console, Accounts, and Billing
names. The legacy `web-saas-prod` host remains outside the V2/V3 target set.

## Stable identities

Each release has two kinds of names:

| Identity | Example V2 | Purpose |
| --- | --- | --- |
| private revision names | `console-selfhost-prod-v2.svc.plus`, `accounts-selfhost-prod-v2.svc.plus` | host and operator checks before cutover |
| stable public aliases | `console-selfhost-prod.svc.plus`, `accounts-selfhost-prod.svc.plus`, `billing-selfhost-prod.svc.plus` | user-facing URL and OAuth/CORS identity |

`compose/web-saas/.env.prod-v2` is the release-owned source for the stable
`PUBLIC_*_DOMAIN` values. The Playbooks `web-saas-prod-v2` host vars render the
same values into Caddy and Accounts. A release is invalid if those sources
disagree.

## V2 → V3 promotion

1. Provision V3 on a new host and keep V2 serving the stable aliases.
2. Pin all images and the GitOps release to immutable SHA/digests. Set V3's
   private names while keeping the same `PUBLIC_*_DOMAIN` aliases.
3. Reconcile Playbooks first (certificates, Caddy host matchers, Accounts
   `frontendUrl`, OAuth callbacks, `publicUrl`, and `allowedOrigins`), then let
   Doco-CD converge the Compose stack.
4. Verify the V3 private names directly: `/`, Accounts readiness and ping,
   registration/login, OAuth redirect construction, Billing health, and one
   real proxy subscription. Do not call this a cutover yet.
5. Change the three existing Selfhost DNS records in one reviewed DNS
   transaction. DNS is an alias switch only; the public Host header is
   preserved and Caddy serves both private and public names. Record the prior
   address and release ID as the rollback checkpoint.
6. Repeat the authenticated registration and proxy smoke tests through the
   public names. Keep V2 running until the observation window closes.

## Rollback and database rules

- Roll back DNS to the recorded previous address; do not rebuild the prior
  host during an incident.
- Database migrations must be additive and backward compatible with the
  previous release. Destructive changes require a separate migration window,
  backup/checkpoint, and an explicit rollback plan.
- Never change `web-saas-prod` host vars or its public records as part of a V2+
  promotion. The only mutable routing state is the original Selfhost alias
  record set owned by the versioned release procedure.

## Acceptance evidence

Keep the release tag, GitOps commit, Playbooks commit, rendered Caddy host
matchers, DNS transaction receipt, application image digests, and public
registration result together. A Doco-CD reconciliation or HTTP 200 alone is
not acceptance; public registration and proxy-path checks must pass.
