# Feature delivery records

These records connect requirements, cross-repository PRs, immutable candidates,
acceptance and release receipts. They are evidence indexes, not a new deployment
controller, a second topology source or permission to operate. Unknown values
stay null; a missing required receipt blocks its stage. Read current repository
and Actions state before execution: an observed PR state is a dated fact.

The first record is [XConnect referral](feature-xconnect-referral.yaml). The
requirement owner remains the linked Accounts task. Existing SIT `release.yaml`
and OCIRepository own the candidate images and chart; the existing Serverless
runtime topology owns UAT targets. Do not duplicate these in this index.

## Current capability and next increments

| Boundary | Accessible evidence | Gap / next implementation owner |
| --- | --- | --- |
| Feature ID and cross-repository work | Business baseline PRs are merged; preview and declaration are linked in the record | Keep new companion PRs and merge dependencies attached to the same requirement; a single PR closing cannot complete the feature |
| Fixed SIT artifacts | Existing complete six-component digest overlay and chart digest | Trusted deployment must compare actual image IDs, config and data baseline; a file hash alone is not candidate acceptance |
| Isolated SIT and combined tests | Existing protected owner workflows and failing rebuild evidence | Playbooks owns bounded repairs and test execution; preserve failures and bind the next result to exact candidate/namespace incarnation |
| Main to UAT | Separate Serverless runtime declaration already exists | Toolkit owns trusted main-build selection, immutable release receipt, trigger, serialization and independent verification; this record does not claim automation is operational |
| Metrics, logs and traces | Existing observability architecture is the shared owner | Attach revision-bound queries, observation windows and sanitized test/deploy receipts; keep unbounded IDs in events/indexes rather than metric labels |
| Archive and automatic reclamation of SIT resources | No successful final archive or cleanup receipt is established here | Lifecycle owner must implement/verify approved automatic cleanup, exact ownership and retry receipts; documentation is not execution evidence |
| PROD | Separate release stage | Manual controlled promotion of the accepted immutable UAT release, with health/observation/rollback gates; no automatic PROD trigger is introduced |

Prioritize the existing failing SIT path, combined business tests, Main provenance
and automated UAT before rootless deepening or a new orchestration platform.
Reuse the existing release matrix, runtime topology and owner receipts instead
of adding parallel controllers, hand-maintained artifact matrices or redundant
monitoring collectors. Keep PR candidate evidence separate from new Main
artifacts after merge; revalidation scope follows actual differences.

Current main documents a platform Traefik entry and includes Traefik ingress
annotations, whereas the requested direction is Caddy-only. This is a runtime
contract discrepancy, not just prose. Its owner must verify the active path and
make the smallest non-production change; this record does not migrate ingress
or change production. A working endpoint and applicable boundary tests are the
acceptance requirement, not a broad platform rebuild.

## Archive and cleanup contract

Archive receipts outside the temporary lane before reclaiming it. Retain the
requirement, PR/source mappings, full candidate and Main release identity,
configuration/data baselines, test cases/results, deployment/observation windows,
approvals, failures and cleanup result. Publish only sanitized metadata; raw
credentials, access-bearing URLs and personal data never belong here.

Record delivery and resource state separately. SIT verified, merged, UAT
verified and archived are distinct outcomes; a reclaimed lane neither proves
UAT nor erases the feature's release record. The non-production loop closes
without waiting for a later manual production release. A production record can
subsequently reference the accepted UAT release.

An approved automatic policy may reclaim SIT after its declared gate and
retention conditions, without repeated interactive approval. Before mutation,
the owner must authenticate the exact current namespace UID and candidate,
check leases/investigation holds, and enumerate bound test PVCs/PVs with reclaim
policy and ownership. Stop/remove only the corresponding GitOps reconciliation
source through its owner before deletion, then verify it cannot recreate the
lane. A same-name namespace with a different UID invalidates old authorization
and receipts. Missing evidence or unknown ownership means retain and report.

Deletion scope excludes persistent UAT, shared ingress/dependencies, host K3s
storage, unrelated disks and credentials. Namespace deletion is not proof that
external resources were reclaimed. Do not force finalizers to hide failure;
record remaining resources, partial failure and a bounded retry owner. Keep
archive retention independent from temporary resource retention.
