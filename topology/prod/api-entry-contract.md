# PROD API entry contract

- Brand homepage: `xworktech.com`; console: `console.svc.plus`. These entries keep their current ownership.
- Accounts API: `accounts.svc.plus` CNAME to `accounts-serverless-prod.svc.plus` or `accounts-k3s-v5.svc.plus` for the current K3s selfhost target.
- Billing API: `billing.svc.plus` CNAME to `billing-serverless-prod.svc.plus` or `billing-k3s-v5.svc.plus` for the current K3s selfhost target.
- Vault API: `vault.svc.plus` CNAME to `vault-k3s-v5.svc.plus` only after the source and target KV path/key/value consistency gate passes.
- Observability UI: `observability.svc.plus` CNAME to `observability-k3s-v5.svc.plus`; the former observability host is retired and is not a rollback target.
- Brand homepage `xworktech.com` remains on its current A record until the K3s Console host route and the existing domain certificate pass direct-SNI HTTPS checks.
- A canonical CNAME must keep explicit Worker Routes on its original hostname. Edge Gateway selects Accounts and Billing origins together; no POST/PUT/PATCH/DELETE retry across databases.
- `serverless.billing_host` remains the legacy caller's public hostname. New consumers use `billing_serverless_host` for the qualified Worker domain; `api_cname_records` is authoritative for API aliases. Other canonical records and website/console domains are preserved.
- IaC owns Cloudflare DNS and Worker-domain resources; Edge Gateway owns Worker deployment; Toolkit selects fixed owner revisions and acceptance evidence. Host configuration is applied to the existing K3s node through SSH + Playbook, then reconciled by Flux.
- Keep Serverless active until complete business equality, PROD Proxy UUID equality, latest native schema and a single writer fence are verified. Identity-only copying is insufficient.
- GitOps declaration changes are not live CNAME or database cutover evidence. Existing callers must migrate to the reviewed IaC owner before production alias reconciliation.

- PostgreSQL alias: `postgresql.svc.plus` targets `postgresql-k3s-v5.svc.plus`. The current K3s database is ClusterIP-only and stunnel is disabled; DNS readiness does not establish an external database tunnel.
