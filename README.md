# Cloud-Neutral Toolkit GitOps

This repository is the **authoritative** GitOps declaration layer for the Cloud-Neutral Toolkit.

Consumers reference it by URL and ref rather than vendoring copies — for example the
`setup-iac-env` composite action in `platform-ops-toolkit`, which takes `gitops_repo_name`
and `gitops_repo_ref` as inputs. Declarations live here; the pipelines that act on them
live in their own repositories and pin the ref they consume.

## Scope

**In scope — declarative state:**

- Kubernetes resources and Flux Kustomizations.
- Non-sensitive multi-environment values.
- **IaC topology declarations**: the desired set of hosts, their sizes, groups, and service
  domains per environment. These are inputs consumed by Terraform renderers and by CMDB /
  inventory generators.

**Out of scope:**

- Application charts and Helm templates — these belong in the dedicated chart repository.
- Imperative automation: Ansible playbooks, roles, and hand-maintained inventories.
- Secrets of any kind. Credentials are distributed at runtime through Vault, never committed
  here. Topology declarations may contain SSH **public** keys; nothing private.

### On topology declarations specifically

A topology declaration states *what should exist* — it is data, not automation. That it is
later rendered into Terraform HCL, or into an Ansible inventory, does not make it imperative
automation, and does not conflict with the exclusion above. The line is:

| | Belongs here | Belongs to the pipeline repo |
|---|---|---|
| Host list, plan, groups, service domains | ✅ declaration | |
| The renderer that turns it into HCL | | ✅ |
| The generated `cmdb.json` / `inventory.ini` | | ✅ (build artifact) |
| Playbooks and roles that configure the hosts | | ✅ |

Generated inventories remain out of scope. The *declaration they are generated from* is in
scope.

## Layout

- `environments/`: cluster-level overlays and entrypoints (`clusters/<env>/`)
- `services/`: per-service declarations shared across environments
- `resources/`: IaC topology declarations, keyed `<project>/<env>/<provider>/`
- `skills/`: repository-scoped conventions consumed by agents
- `docs/`: repository conventions and operational documentation

For a directory-level overview, see [docs/repo-structure.md](docs/repo-structure.md).

### `resources/` path convention

```
resources/<project>/<env>/<provider>/<declaration>.yaml
```

This shape accommodates the two conventions already in use:

| Consumer | Path |
|---|---|
| Multi-cloud account/resource matrices | `resources/svc.plus/uat/aws/account/bootstrap.yaml` |
| Vultr VPS topology per business domain | `resources/svc.plus/uat/vultr/web-saas.yaml` |

`<project>` is the domain base or account grouping, `<env>` is `sit` / `uat` / `prod`, and
`<provider>` is the cloud the declaration targets. Keeping the provider in the path is what
lets one environment span more than one cloud without the filenames colliding.

**Do not hardcode environment-varying values inside a declaration.** Domains, hostnames and
plans are supplied by the consuming pipeline (e.g. `TARGET_DOMAIN_BASE`, `INSTANCE_PLAN_API`).
A per-file fallback default is worse than none: divergent fallbacks render output that is
valid, plausible, and wrong in only some files.

## Consuming this repository

Pin a ref. A consumer that tracks a moving branch inherits every change here at the moment it
runs, which is rarely what a deployment wants:

```yaml
- uses: ./.github/actions/setup-iac-env
  with:
    gitops_repo_name: https://github.com/ai-workspace-infra/gitops.git
    gitops_repo_ref: ${{ inputs.gitops_repo_ref || 'main' }}
    gitops_target_path: gitops
```

**A missing declaration must fail the consuming step.** Reading a path that does not exist and
continuing — logging a warning and exiting 0 — produces a run that is green while having
configured nothing. Consumers are responsible for asserting that the declaration they expected
was actually found.
