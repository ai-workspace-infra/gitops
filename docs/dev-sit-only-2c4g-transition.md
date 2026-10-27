# Dev SIT-only and persistent Serverless UAT

The feature acceptance boundary is linked PRs → immutable artifacts → temporary complete SIT Namespace and feature hostname → automated acceptance → merge main. Dev K3s V5 runs temporary SIT workloads only. Existing UAT uses topology/uat/serverless/runtime-topology.yaml (Cloudflare Pages, Cloud Run and Supabase), is persistent, and consumes controlled main builds pinned to immutable artifacts. Main watching is a release trigger, not permission to deploy floating tags.

Do not connect the Serverless UAT database, sessions, OAuth callbacks or runtime credentials to a SIT namespace. Do not redirect existing UAT DNS to the Dev node. Removing a never-deployed K3s UAT candidate does not authorize cleanup of historical UAT states, DNS or cloud resources.

## Dev capacity

The sole desired Linode type is g6-standard-2 (2 vCPU / 4096 MiB / 81920 MiB disk allocation). Keep the existing Dev target, canonical Terraform key and logical hostname. Run one complete feature lane at a time initially; queue additional features until observed memory/CPU headroom supports concurrency. Configure quotas/requests from the actual rendered workload footprint; do not infer capacity from green schema validation.

## Resize gate

Changing the type alone is insufficient when current allocated disks exceed 81920 MiB. Resolve the current instance via CMDB and the declared account/label before every action. Capture disk IDs/filesystems/used bytes, CPU and memory, attached volumes, active jobs and application/PVC inventory. Require no active feature test before planned downtime.

For an ext4 disk that fits, the reviewed Linode owner must stop the exact node, wait for offline, resize the root disk to at most 81408 MiB while retaining 512 MiB swap, wait for disk ready, and apply the declared g6-standard-2 change through the existing Dev Terraform owner. If disk shrink is unsupported or used space exceeds the target, stop and prepare a replacement plan; never rebuild/delete as an implicit fallback. Preserve state identity and refresh CMDB; verify IP, host key, 2 CPUs, 4 GiB memory, filesystem and K3s/Flux readiness before accepting the resize. Application readiness remains a separate gate.

The existing generic Resize Instance workflow is Vultr-specific and is not a valid Linode executor. A normal Terraform plan cannot prove offline disk shrink completed. Do not bypass provider preflight or automatically invoke this transition from an ordinary app deployment.

Rollback: before shrinking, define a recoverable platform configuration reference. After shrinking, restoring the old plan can restore CPU/RAM headroom but does not automatically restore former disk allocation or application data. The operation must produce a receipt with actual post-resize type and disk sizes; this declaration is not such a receipt.
