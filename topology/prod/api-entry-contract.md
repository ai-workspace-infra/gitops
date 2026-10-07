# PROD API entry contract

- Brand homepage: `xworktech.com`; console: `console.svc.plus`. These entries keep their current ownership.
- Accounts API: `accounts.svc.plus` CNAME to `accounts-serverless-prod.svc.plus` or `accounts-selfhost-prod.svc.plus`.
- Billing API: `billing.svc.plus` CNAME to `billing-serverless-prod.svc.plus` or `billing-selfhost-prod.svc.plus`.
- A canonical CNAME must keep explicit Worker Routes on its original hostname. Edge Gateway selects Accounts and Billing origins together; no POST/PUT/PATCH/DELETE retry across databases.
- `serverless.billing_host` remains the legacy caller's public hostname. New consumers use `billing_serverless_host` for the qualified Worker domain; `api_cname_records` is authoritative for API aliases. Other canonical records and website/console domains are preserved.
- IaC owns Cloudflare DNS and Worker-domain resources; Edge Gateway owns Worker deployment; Toolkit selects fixed owner revisions and acceptance evidence.
- Keep Serverless active until complete business equality, PROD Proxy UUID equality, latest native schema and a single writer fence are verified. Identity-only copying is insufficient.
- GitOps declaration changes are not live CNAME or database cutover evidence. Existing callers must migrate to the reviewed IaC owner before production alias reconciliation.
