# GitOps declaration and documentation standard

本文件定义 GitOps 仓库中资源描述和文档的唯一编辑格式。资源、拓扑和非敏感运行配置使用 YAML；规范、说明、迁移记录和操作手册使用 Markdown。Terraform、Ansible、Cloudflare、CMDB 和编排流水线只能消费这些声明，不能在运行时重新发明资源事实。

## 1. Source of truth

| Content | Canonical format | Canonical location |
| --- | --- | --- |
| Cloud/IaC resource declaration | YAML | `resources/<project>/<environment>/<provider>/*.yaml` |
| Cross-service or XConnect topology | YAML | `topology/<environment>/<mode>/*.yaml` or `vpn-overlay/<environment>/*.yaml` |
| Shared service declaration | YAML | `resources/<project>/shared/<provider>/*.yaml` |
| Service configuration that is part of GitOps intent | YAML | `services/<service>/<environment>/**/*.yaml` |
| Human documentation, runbooks, decisions | Markdown | `README.md`, `docs/**/*.md`, directory `README.md` |

The path is part of the contract. `environment` is one of `sit`, `uat`, `prod`, or `shared`; `provider` is an explicit registry value such as `aws`, `gcp`, `akamai`, `vultr`, `ucloud`, or `ulighthost`. A provider switch changes the declaration and its review; it must not be hidden in a renderer fallback.

## 2. YAML resource contract

Every resource or topology document must be one YAML document with these top-level fields:

```yaml
apiVersion: gitops.svc.plus/v1alpha1
kind: ResourceMatrix
metadata:
  name: example
  project: svc.plus
  environment: uat
spec: {}
```

Rules:

1. Use two spaces for indentation and UTF-8 text. Keep one declaration per file.
2. `apiVersion`, `kind`, `metadata.name`, `metadata.project`, `metadata.environment`, and `spec` are required for resource/topology declarations.
3. Put desired state in `spec`; keep execution steps in the consuming workflow or playbook.
4. Use explicit `provider`, account/project identifiers, region, workspace/state namespace, lifecycle, and management mode. `account_ref` may identify a runtime profile; `account` or `project_id` must be used when the concrete account/project is part of the intended state.
5. `management_mode: existing` must also declare `lifecycle: external`. Existing resources are inventory inputs only: no Terraform create, replace, apply, or destroy may be inferred from them.
6. Keep secrets out of GitOps. Vault paths and non-secret field names may be declared; tokens, passwords, private keys, unseal material, and database credentials must not be committed.
7. Environment-specific domains, plans, IDs, and network names are desired state only when the environment declaration owns them. Do not add hidden per-file defaults that diverge from the selected GitOps matrix.
8. Use quoted YAML strings for values that may be parsed as numbers, booleans, dates, account IDs, CIDRs, or expressions (for example, AWS account IDs and `0.0.0.0/0`).

## 3. State, lifecycle, and safety

Terraform state keys are derived from the declaration's environment, project, provider/account, and namespace. A resource declaration must not silently share a state with another namespace. Permanent services and protected production nodes require an explicit lifecycle guard such as `prevent_destroy` in the IaC consumer; the GitOps declaration must identify the scope and exception.

Use these fields when applicable:

```yaml
management_mode: terraform
lifecycle: permanent
provider: gcp-cloud
account_ref: gcp_account
project_id: open-platform-uat
workspace: open-platform
state_namespace: open-platform
```

For external nodes:

```yaml
management_mode: existing
lifecycle: external
provider: ulighthost
resource_manifest: resources/svc.plus/uat/ulighthost/xconnect.yaml
```

The renderer must fail closed when a declaration is missing, ambiguous, or has a provider/account mismatch. A successful render or `plan` is not proof of deployment; apply, playbook, DNS, monitoring, and acceptance evidence remain separate stages.

## 4. JSON migration policy

Resource descriptions, topology declarations, and GitOps service configuration are YAML. Existing files in those categories are migrated from `.json` to `.yaml` in the same change, and every consumer/reference is updated atomically. The YAML conversion must preserve keys, scalar types, arrays, and values; it must not introduce secrets or change lifecycle intent.

JSON remains allowed only for an intentional machine/API boundary, for example a GitHub API ruleset request/fixture under `skills/**/references/`. Such a file must be documented as a payload or fixture and must not be treated as the authoritative resource declaration. Generated `cmdb.json` and `inventory.ini` are pipeline artifacts, not GitOps source files.

## 5. Markdown documentation contract

Every new convention or non-obvious topology must have a Markdown page close to the declaration or linked from `docs/README.md`. A page should state:

- scope and owner repository;
- authoritative declaration path and the Git ref consumed by pipelines;
- provider/account/environment boundaries;
- Vault paths by name only, never secret values;
- apply, migration, rollback, destroy, and existing-resource boundaries;
- validation commands and what each command does not prove.

Use relative links to repository files. Do not paste generated logs, credentials, or mutable cloud-console screenshots as the source of truth.

## 6. Review and validation checklist

Before merging a GitOps change:

1. Run a YAML parser over changed declarations and `git diff --check`.
2. Run the repository topology/resource contract scripts.
3. Search for stale `.json` paths and verify every remaining JSON file is an intentional machine payload.
4. Confirm provider, concrete account/project, region, namespace/state key, and lifecycle against the requested matrix.
5. Confirm `existing` rows cannot reach Terraform create/destroy code paths.
6. Review the generated plan and inventory separately; do not infer real cloud changes from static validation.

The merge order is `GitOps declaration → IaC renderer/module → playbook/inventory → platform workflow`. The GitOps repository supplies intent and facts; it does not contain imperative deployment logic.
