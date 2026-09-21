# IaC declaration layout

GitOps is the single declaration layer for cloud infrastructure. The Terraform module
repository contains reusable modules, templates, renderers and environment workspaces; it
must not contain provider `config/` trees or copied account/resource YAML.

## Canonical path

```text
resources/<project>/<environment>/<provider>/<declaration>.yaml
```

`project` identifies the owning domain or account boundary, `environment` is `sit`, `uat` or
`prod`, and `provider` is the cloud being changed. A declaration is non-secret desired state;
credentials, private keys, tokens and passwords stay in Vault or the CI secret store.

## Current mappings

| Project | Environment | Provider | Declarations |
|---|---|---|---|
| `xworktech.com` | `dev` | `gcp` | account bootstrap/landing-zone and shared resource declarations |
| `xworktech.com` | `uat` | `gcp` | `open-platform-uat.yaml` |
| `xworktech.com` | `prod` | `gcp` | `open-platform-prod.yaml` |
| `svc.plus` | `sit`, `uat`, `prod` | `aws` | AWS host/resource declarations and GitHub Actions OIDC metadata |
| `svc.plus` | `sit`, `uat`, `prod` | `vultr` | VPS host/resource declarations |
| `svc.plus` | `uat` | `akamai` | six isolated namespaces for web-saas, open-platform, ai-workspace and JP/US/SG Agent Proxy |
| `svc.plus` | `dev` | `supabase` | Supabase project declaration |

The environment and provider directories are intentionally separate. This prevents a UAT
renderer from accidentally consuming production values and allows the same service name to be
declared independently on AWS and Vultr.

## Consumption contract

Pipelines check out this repository at a pinned ref and pass an absolute declaration path to
the renderer (`--resources` or `RESOURCES`). Terraform modules receive declaration paths as
inputs; they do not discover files under the module repository. Rendered HCL, tfvars, state,
CMDB and Ansible inventory remain build artifacts and are ignored by Git.

For isolated Akamai UAT resources, each YAML declares exactly one host. The
`global.state_namespace`, `global.workspace` and filename stem must match. The existing consuming
workflow derives the canonical state key from its `workspace` input, so it must be invoked with
the matching namespace; declarations must not be regrouped under shared `selfhost`. CI validates this contract with
`scripts/validate-akamai-uat-six-namespaces.sh`.

When adding a provider or environment:

1. Create the canonical directory and declaration in this repository.
2. Update the consuming pipeline/workflow to pin the GitOps ref and pass that path.
3. Keep the Terraform module repository limited to code and templates.
4. Validate the declaration and rendered Terraform before applying UAT, then promote the same
   commit to PROD.
