# gitops Agent 约束：声明式目标状态

## 仓库格式限定（强制）

- 所有受 Git 跟踪的 JSON 文件必须转换为 YAML；禁止新增或保留 `.json` 文件，包括资源矩阵、拓扑、配置、schema 和规则模板。
- `topology/uat/hybrid/resource-matrix.yaml` 是 UAT 资源矩阵唯一声明源；禁止使用 `.json` 作为第二份资源描述。
- 转换保留键、值、标量类型、数组顺序和当前 main 的最新资源事实；同步更新消费者路径和解析器。
- 外部 API 所需 JSON 只能由 YAML 在运行时生成，不得回写或提交到 GitOps。CMDB 和执行回执由 IaC/控制面保存为运行产物。
- PR 的格式检查必须拒绝任何受跟踪的 `.json` 文件；不得通过改名后继续使用 JSON 专用读取器绕过 YAML 消费契约。

五仓职责完整判定见
[`execution-ownership-migration`](https://github.com/ai-workspace-lab/xworkspace-core-skills/blob/main/skills/engineering-standards/execution-ownership-migration/SKILL.md)。

## 允许内容

只保存可审计的声明式目标状态：资源拓扑、provider/environment 选择、实例规格、服务版本/tag/digest、
域名、网络引用、非敏感配置引用和 Vault key/path 引用。GitOps 是声明源，不是 CMDB；运行时 IP、instance ID、
Terraform 输出和执行回执必须由 IaC/控制面产生。

`security/vault/` 保存不含秘密值的 Vault ACL policy、JWT role 和模板声明；它不是 Flux/Kustomize 资源。受控 Vault 管理写入由 Playbooks owner 执行，Platform-Orchestrator 负责身份授权、派发和回执。现有控制面写入实现属于待迁移代码，不能作为新增执行逻辑的许可；先验证 owner 与 caller，再移除旧实现。不得在该目录添加执行脚本。

## 硬禁令

- 不新增 shell/Python/Ruby 执行脚本、Ansible role/playbook、Docker/systemd/service 操作；
- 不调用 provider、DNS、Registry、Vault 写入或数据库/主机 API；CI 只能做无副作用 schema/声明校验；
- 不保存密码、私钥、DSN、token、运行时 CMDB、临时地址或人工复制的 provider 事实；
- 不把“安装器”“bootstrap”或“validator”命名当作执行归属例外。

每类声明必须有明确消费者和 schema：云资源由 IaC renderer 消费，Flux 资源图由 Flux 消费，主机/身份配置由 Playbooks 消费。涉及执行能力变更时提交对应 owner PR。

## 声明完整性与执行交接

- 本仓声明真实环境、批次、节点、provider/account/region、资源引用、Flux 图、RBAC 和非敏感凭据引用；这些具体身份是期望状态，不能因带版本字符串就删除。运行代码按该名字分支才属于硬编码问题。
- 根 Kustomization、集群名、节点 hostname、批次目录、namespace 和 source path 分别声明；不得隐式要求同名。CRD/ESO/TLS/服务依赖和独立单元版本引用在资源图内表达。
- 基础仓库由 dispatch 选 ref，默认 `main`，一次运行记录 commit；声明格式需支持消费该运行候选，避免调谐时覆盖控制面按契约交付的 source pin。单元独立更新范围应明确，不能意外扩大到其他单元。
- 身份声明明确 OS/Kubernetes/数据库职责映射、RBAC、Vault 角色和字段引用，不预置运行时 cluster UID、CA 私钥或身份 token。相应 owner 负责生成、验证和秘密交付。
- 声明更新同步对应 schema/消费者，缺失或不支持字段应明确报错；不得让 Playbooks 以代码常量或本地 YAML 副本补齐。运行时 API JSON/HCL 允许由 YAML 派生，不能回写第二份声明。
- 资源配置、RBAC 与 Vault 策略的应用归 IaC/Playbooks/Flux 各自执行入口；GitOps 只做声明校验，不调用管理 API。迁移调用方后清理旧引用，旧持久资源及历史证据保留实际身份。

详细交接与硬编码判定见：[declaration-and-handoff](https://github.com/ai-workspace-lab/xworkspace-core-skills/blob/main/skills/engineering-standards/execution-ownership-migration/references/declaration-and-handoff.md)。
