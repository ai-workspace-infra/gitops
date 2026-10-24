# Isolated PROD Raft recovery

This declaration adds a separate Raft Vault and retained PVC without replacing
the existing instance. NetworkPolicy quarantines all pod ingress and egress;
no public ingress, production Raft join, or automatic ESO switch is declared.
The API listener uses HTTP only inside this quarantine; pod traffic must remain
blocked until an authenticated TLS access path is reviewed for consumers.

An authorized operator uses the node administration channel to initialize this
empty target, restore the verified snapshot, and unseal with controlled recovery
material. Never place tokens or unseal shares in Git or command-line arguments.
Readiness intentionally fails until recovery and unseal are complete. A restart
requires unseal again; this is not an auto-unseal deployment.

Before enabling consumers, revoke copied token identities on this target, disable
copied external authentication methods, configure independent PROD policy and
short-lived workload identity, and verify allowed and denied requests. Validate
mount/object completeness and pod-recreation persistence. Local-path is not a
host-loss backup. Existing Vault/ESO resources remain the rollback point until
explicitly verified consumer handoff. Never delete either PVC as part of rollback.
