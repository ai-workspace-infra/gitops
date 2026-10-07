# Unified IaC declarations

`IaCPipelineTargets` is the reviewed input to Toolkit's eight-job pipeline. The
owner checkout alone cannot select an environment or create a target. The action
validates this file and every referenced resource manifest at the same GitOps SHA.

The six provider IDs in `capabilities.yaml` are coverage declarations, not live
readiness claims. Existing Akamai UAT namespace declarations retain their
`terraform/uat/svc.plus/akamai-cloud/manbuzhe2026/<namespace>/terraform.tfstate`
keys and **default** CLI workspace. Existing state is mandatory; a missing state
stops the run for investigation rather than creating a parallel stack. Destruction
is disabled in these declarations pending target-specific cleanup review.

Bootstrap verifies the actual Linode username. Account is explicitly
`not_applicable`: public keys are passed to workload instances, without recreating
shared account keys. Resources own exactly their compute module and workload
firewall; separate volumes are protected. No approval or runtime acceptance is
implied by adding the declaration.

AWS/Vultr declarations currently contain legacy templates and workspace behavior;
GCP combines network/IAM/workload state; UCloud needs a concrete project binding and
verified security-group/key-pair owner; Azure has no production renderer. Those
targets must gain reviewed identity, address/state mapping and live prerequisite
checks before execution is enabled. Do not invent accounts or mark stages
`not_applicable` to bypass this gate. Existing state moves/imports require an
explicit maintenance operation, reviewed backup and zero unintended changes.

Every stage declares `mode: verify | terraform | not_applicable | unsupported`.
Terraform stages require `manifest`, exact `state.key`, `cli_workspace: default`,
`owners`, `protected`, `ownership_reviewed`, and explicit `destroy_allowed`.
External/shared prerequisites use live checks, not resource IDs copied into a
receipt. Persistent volumes, shared identities, network and backend cannot be
retired by the ordinary deployment chain.
