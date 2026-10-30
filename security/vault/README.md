# Vault authorization declarations

This directory is the YAML source for Vault ACL policies and JWT roles used by
the controlled Platform-Orchestrator Vault administration entrypoints.

These files contain authorization metadata only. They do not contain secret
values, and they are not Kubernetes resources: Flux and Kustomize do not apply
them. Toolkit scripts read a reviewed GitOps ref, render the Vault API payload
at runtime, and write only when an operator explicitly selects `--apply`.

## Layout

- `policies/`: one `VaultACLPolicy` YAML per policy. `spec.paths` lists Vault
  ACL paths and capabilities.
- `roles/`: one `VaultJWTAuthRole` YAML per GitHub Actions JWT role. Each
  `spec.token_policies` reference must resolve to a policy in `policies/`.
- `workload-identities/`: cluster workload JWT role contracts. These are
  consumed by the designated Playbooks identity role, not the shared GitHub
  Actions role installer.
- `templates/`: parameterized policy and role templates for account-scoped
  Akamai roles. Toolkit resolves declared placeholders before contacting Vault.

The `metadata.name` field is the Vault policy/role identifier. `metadata`
fields are not sent to Vault; only the rendered `spec` is used. For policies,
the Toolkit renderer compiles the structured YAML `spec.paths` into Vault ACL
policy text immediately before the API call. For roles, it serializes `spec` to
the Vault JWT role API request. No generated HCL or JSON is committed.

Changes to capabilities, token constraints, bound claims, or policy references
are security-sensitive. Review the effective path scope and allowed/denied
identity contract before applying them. GitOps CI checks declaration shape and
policy references without calling Vault.
