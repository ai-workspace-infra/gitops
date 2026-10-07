# gitops Agent 约束：声明式目标状态

## 仓库格式限定（强制）

- 所有受 Git 跟踪的 JSON 文件必须转换为 YAML；禁止新增或保留 `.json` 文件，包括资源矩阵、拓扑、配置、schema 和规则模板。
- `topology/uat/hybrid/resource-matrix.yaml` 是 UAT 资源矩阵唯一声明源；禁止使用 `.json` 作为第二份资源描述。
- 转换保留键、值、标量类型、数组顺序和当前 main 的最新资源事实；同步更新消费者路径和解析器。
- 外部 API 所需 JSON 只能由 YAML 在运行时生成，不得回写或提交到 GitOps。CMDB 和执行回执由 IaC/控制面保存为运行产物。
- PR 的格式检查必须拒绝任何受跟踪的 `.json` 文件；不得通过改名后继续使用 JSON 专用读取器绕过 YAML 消费契约。

四边界完整判定见
[`execution-ownership-migration`](https://github.com/ai-workspace-lab/xworkspace-core-skills/blob/main/skills/engineering-standards/execution-ownership-migration/SKILL.md)。

## 允许内容

只保存可审计的声明式目标状态：资源拓扑、provider/environment 选择、实例规格、服务版本/tag/digest、
域名、网络引用、非敏感配置引用和 Vault key/path 引用。GitOps 是声明源，不是 CMDB；运行时 IP、instance ID、
Terraform 输出和执行回执必须由 IaC/控制面产生。

## 硬禁令

- 不新增 shell/Python/Ruby 执行脚本、Ansible role/playbook、Docker/systemd/service 操作；
- 不调用 provider、DNS、Registry、Vault 写入或数据库/主机 API；CI 只能做无副作用 schema/声明校验；
- 不保存密码、私钥、DSN、token、运行时 CMDB、临时地址或人工复制的 provider 事实；
- 不把“安装器”“bootstrap”或“validator”命名当作执行归属例外。

每个声明必须能被 IaC renderer 消费；涉及云资源动作时切到 IaC PR，涉及主机/服务动作时切到 Playbooks PR。
