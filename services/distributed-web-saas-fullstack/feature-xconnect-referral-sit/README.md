# feature-xconnect-referral-sit

Temporary SIT lane for the XConnect referral feature on `dev-k3s-v5`
(deployment re-verification of the already-merged fixed candidate).

- Accounts `8d1b09a6f2022af221b2a817d516952af41ced0e` → `ghcr.io/ai-workspace-services/accounts@sha256:6edd156c…737d`
- Portal `2a272f295235efdd39f469245ad74177d1a5ff5d` → `ghcr.io/ai-workspace-services/console@sha256:03ffaf01…28f9`
- Frontend Router `ab3f9e81…` is a Cloudflare Worker artifact and is not deployed in-lane.
- Chart `distributed-web-saas-fullstack@sha256:63362354…20f27` (0.2.5)

Secrets `lane-db-admin`, `lane-accounts-runtime`, `lane-console-runtime` are
referenced by name only and generated in-namespace by the lane operator.
Egress is restricted to in-namespace peers and cluster DNS.

Lifecycle: this directory is removed (GitOps target revoked) at SIT cleanup.

## Candidate evidence

`candidate.yaml` records unresolved evidence explicitly. Declaration hashing and
runtime receipts belong to the Toolkit control plane, not this declarative
repository. Data baseline and runtime image reconciliation remain unknown, so the
candidate is `BLOCKED`. The namespace and values both identify SIT. This delta
grants no deployment or UAT promotion authority.

The declared egress policy currently permits only namespace peers and DNS. Real
Stripe Sandbox validation remains blocked until the existing owner supplies a
reviewed egress path and authorized Sandbox identity; mock results do not satisfy it.
