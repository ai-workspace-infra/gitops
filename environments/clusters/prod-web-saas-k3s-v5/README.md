# Retained PROD cluster handoff

This declaration adopts the existing isolated cluster. It does not authorize
creating or replacing the host, deleting PVCs, or switching public DNS.

Before activation, back up and verify the old Terraform state and migrate its
ownership to the declared PROD backend key. Confirm the destination is absent
and record lineage migration and preserve resource IDs; retire old ownership without deleting cloud
resources. Do not run apply against an empty destination state.

Publish the fixed reviewed GitOps release tag only after CI/review. Suspend old
cluster reconcilers and disable their pruning, then transfer ownership without
resource deletion. Bootstrap source.yaml and root.yaml through the authorized
node administration channel. All new reconcilers consume the fixed tag.

Credential source migration is staged: the existing reference is retained until
isolated Raft restore, TLS, dedicated cluster policy and shadow ESO checks pass.
No source Vault changes or shared production credential rotation are implied.
