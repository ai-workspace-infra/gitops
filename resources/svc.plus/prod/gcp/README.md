# PROD GCP Selfhost Web SaaS

`web-saas.yaml` is the canonical declaration selected by Toolkit's
`selfhost-orchestrator.yml` for `prod / gcp-cloud / xworktech / web-saas`.
It targets `open-platform-prod`, independently of the existing Serverless
runtime and the shared Vault project.

- One `STANDARD` `e2-medium` VM, `web-saas-prod`, in `asia-east1-a`.
- A retained, independently managed 50 GiB data disk mounted at `/data`.
- VM deletion protection; no Spot termination or maximum lifetime.
- OS Login and HTTPS ingress; PostgreSQL has no declared public TCP listener.
- State key: `terraform/prod/svc.plus/gcp-cloud/xworktech/web-saas/terraform.tfstate`.

IaC owns the resource plan, creation, external-IP policy, OS Login and CMDB.
Playbooks owns mounting the declared disk, PostgreSQL/service deployment and
the explicitly requested empty-database initialization. New resources must
have a plan with no deletion/replacement before apply.

The requested data direction is **PROD Supabase → Selfhost PostgreSQL**.
Apply the exact immutable Accounts release's Init DB schema SQL only to the
verified empty local Selfhost database, then use Accounts `cmd/migratectl` for
logical copying of users, identities and sessions. Match users by normalized
email; preserve PROD Proxy UUIDs. Source access remains read only. Credentials
and exported identity rows must never be included in Git or public artifacts.

This declaration does not establish deployment, data convergence or PROD
primary cutover. User-domain import does not establish subscription, quota or
ledger convergence. Compare the required business data and verify the live
entry before changing the primary database under the user's conditional
authorization.

`resources/xworktech.com/prod/gcp/web-saas.yaml` is a **LEGACY** bootstrap
candidate, not this Selfhost workload declaration. Keep it until its callers
and any state are audited; do not apply both declarations to this workload.
