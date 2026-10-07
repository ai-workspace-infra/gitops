# Repository Structure

This repository contains declarative GitOps assets only. Below is an overview of the key
directories.

| Directory | Purpose |
|-----------|---------|
| `environments` | Cluster-level overlays and entrypoints, under `clusters/<env>/`. |
| `services` | Per-service declarations shared across environments. |
| `resources` | IaC topology declarations, keyed `<project>/<env>/<provider>/`. Consumed by Terraform renderers and CMDB/inventory generators. |
| `skills` | Repository-scoped conventions consumed by agents. |
| `docs` | Repository conventions and operational documentation. |

## `resources/`

```
resources/<project>/<env>/<provider>/<declaration>.yaml
```

- `<project>` — domain base or account grouping, e.g. `svc.plus`
- `<env>` — `sit` / `uat` / `prod`
- `<provider>` — the cloud the declaration targets, e.g. `vultr`, `aws`

Keeping the provider in the path lets a single environment span more than one cloud without
filenames colliding.

A declaration states the desired hosts, their plans, groups and service domains. It is data.
The renderer that turns it into Terraform HCL, and the `cmdb.json` / `inventory.ini` generated
from it, belong to the consuming pipeline repository — the generated inventory is a build
artifact and is not committed here.

Values that vary per environment are supplied by the consuming pipeline rather than written
inline, and declarations carry no fallback defaults for them. See the scope notes in
[../README.md](../README.md).

## What does not live here

- Application charts and Helm templates — see the dedicated chart repository.
- Ansible playbooks, roles, and hand-maintained inventories.
- Secrets. Credentials are distributed at runtime via Vault. SSH **public** keys inside a
  topology declaration are fine; nothing private is committed.

## Declaration and cross-repository contract

GitOps is a data repository, not a script repository. New resource, topology, service, and
environment descriptions use YAML; repository and operational guidance uses Markdown.
Existing JSON declarations are converted to YAML when they are touched by a migration, and
consumers must be updated in the same PR. Do not add shell, Python, Ruby, Terraform, or
Ansible automation under the declaration directories.

The consumers are deliberately separate:

- [`iac_modules/scripts/pipeline/`](https://github.com/ai-workspace-infra/iac_modules/tree/main/scripts/pipeline)
  renders and applies Terraform resources.
- [`playbooks/scripts/pipeline/`](https://github.com/ai-workspace-infra/playbooks/tree/main/scripts/pipeline)
  runs the Ansible phase from the resulting CMDB/inventory.
- [`platform-ops-toolkit/.github/scripts/`](https://github.com/ai-workspace-infra/platform-ops-toolkit/tree/main/.github/scripts)
  orchestrates, dispatches, waits, snapshots, performs API DNS operations, and reads this data.

Cross-repository delivery merges IaC/playbooks implementation first and then the dependent
toolkit call-site change. Consumers pin a GitOps ref and must fail when the selected
declaration is missing; they must not silently fall back to another file. Branches are
changed through PRs using the existing repository prefixes, with only `main` and the
repository's established `release/*`/`stable/*` lines long-lived.
