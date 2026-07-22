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
