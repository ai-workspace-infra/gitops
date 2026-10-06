# gitops Agent 约束：声明式目标状态

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
