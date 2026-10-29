# PROD-K3S-V6 独立节点与集群创建准备

状态：规划与声明阶段，尚未执行云端 preflight、Terraform plan/apply、挂载或部署。
升级分类遵循已合并的[技能 PR #63](https://github.com/ai-workspace-lab/xworkspace-core-skills/pull/63)。
V6 是全新节点、全新 K3s 集群、全新数据卷；V5 保持当前服务、SQL schema 和写入权。

## 节点与资源边界

| 项目 | 本轮方案 | 创建前核实 |
| --- | --- | --- |
| 云及地域 | 沿用 V6 GitOps 资源声明中的 Akamai 账户和 Tokyo 3 地域 | 实际账户身份、地区容量、计算/卷配额、费用 |
| 计算 | 1 台 `g6-standard-4`，4 个共享 vCPU / 8 GB RAM，Debian 13 候选 | 实际 plan/image 可用性及各镜像 amd64 兼容性；不是独占 CPU 方案 |
| 系统盘 | 实例方案自带 SSD；OS、容器镜像/运行时及 K3s 控制面 | 实际容量、空闲空间、inode、控制面写入延迟 |
| 独立数据盘 | 同地域新建 1 块 `web-saas-k3s-v6-data`，100 GB，ext4 | 单位为 provider GB；格式化后可用容量、I/O、保护及恢复能力 |
| 集群 | 单节点 K3s server，同时运行工作负载；独立集群身份与 CA | hostname、machine ID、SSH 指纹、集群 UID/CA 均不得沿用 V5 |
| 状态 | 使用现有 V6 独立 workspace/backend key；一个 V6 节点和一个 V6 卷 | 不导入、不移动、不删除 V5 state；不共用 V5 卷或快照恢复原盘 |
| 可用性 | 单节点冷启动和迁移验收候选 | 节点故障会影响所有 V6 单元；Raft 单副本及独立盘都不构成 HA |

此方案保留后续 UI/API 兼容小修复和独立监控服务按各自发布单元原地更新的能力。
业务 DB、SQL schema 和其他业务持久状态转换继续使用下一代新集群。
单节点 Caddy 使用 hostPort 80/443 时也会存在重启窗口，不能承诺零停机滚动。

## 独立数据盘与 Kubernetes 持久化

1. IaC 创建并附加声明中的新卷；权威 CMDB 必须传递卷 ID、实际容量、地域、附加实例 ID
   和稳定设备路径。设备路径、IP、实例/卷 ID 只属于运行产物，不手填回 GitOps。
2. Playbooks 将权威卷身份与目标实例、块设备核对后，才允许初始化空盘；已有文件系统、
   数据、分区或非空挂载目录均不得自动格式化。文件系统 UUID 用于持久挂载到 `/data`。
3. 将 K3s 持久卷供给路径配置为 `/data/k3s/storage`，并在创建首个业务 PVC 前验证生效。
   每个服务/PVC 使用独立目录、UID/GID 和权限；磁盘物理共享不等于共享数据库身份。
   使用明确的持久化 StorageClass 和 `Retain` 回收策略，核对有状态 namespace/PVC 的
   Flux prune 保护；数据卷的云端删除保护不能替代 Kubernetes 层的保留策略。
4. K3s 启动和供给服务必须检查 `/data` 已挂载在预期卷上；挂载丢失时停止放行业务，
   不能在系统盘同名空目录继续创建 PVC。重启后重新验证 UUID、挂载与 PV 实际路径。
5. PostgreSQL 当前声明 20 GiB、Vault 10 GiB、监控 persistence 20 GiB，合计至少 50 GiB；
   100 GB 不等于 100 GiB。渲染全部 chart 后核对所有 PVC、实际源数据量、索引/WAL、
   监控保留周期、增长及临时空间。local-path 的 PVC 容量声明不能视为已强制实现的磁盘配额。
6. 候选卷告警先按使用率 70% 预警、85% 阻断新的大规模导入评审，再依据测量调整。
   隔离恢复目标和受保护备份放在该节点/数据盘之外，不依赖这块盘上的本地副本恢复自身。
   不默认云节点快照覆盖独立 Block Storage。

不采用旧盘重新附加来完成代际升级，也不通过同集群另建库或复用 PVC 规避新集群要求。
100 GB 是本轮容量候选；源数据、增长或恢复空间核算不通过时先修改声明，再创建资源。

## 网络、身份与冷启动前提

- 临时 SSH IPv4 来源按用户指示声明为 `0.0.0.0/0`；IPv6 SSH 不放行。使用已声明公钥，
  检查实际 SSH 密码登录配置，并在完成引导后通过同一 IaC 声明收紧为操作来源 CIDR。
- HTTP/HTTPS 80/443 用于 V6 入口。6443、5432、Vault 内部端口及节点指标端口不新增公网规则。
  初次管理经 SSH 到目标节点本机完成；后续 XConnect/私网管理路径需单独核对路由和授权。
- 单节点不为 Flannel 跨节点通信开放额外公网端口。创建前盘点现有私网、XConnect 和 V5 网段，
  确定 Pod/Service CIDR；多节点扩展另行规划。`private_ip: true` 不等于已建立隔离 VPC。
- 系统管理、各业务服务、只读审计身份分开。管理员 kubeconfig 强制 0600，审计不读取该凭据。
  Bootstrap 的 root 仅管理节点；应用实际 UID、Kubernetes RBAC 和 DB 角色分别验证。
- 独立 Vault TLS、初始化和 unseal 由外部可信引导路径完成，恢复材料放在集群外受保护位置；
  不依赖尚未初始化的 V6 Vault 为自身引导提供密钥。不复制 V5 Raft 或 recovery key。
- ESO/其他必要控制器由 Playbooks 的受审查 bootstrap 路径先安装并固定版本，不把它们隐藏
  在业务 chart 升级中。V6 SecretStore/身份绑定必须指向已准备好的可信 Vault 路径。

## 执行入口与已核实缺口

以下是 2026-10-29 对各仓库 `origin/main` 的静态检查，不是云端或运行验收结果。

| Owner / 固定检查点 | 已有能力 | V6 放行前需补齐 |
| --- | --- | --- |
| IaC `3cfc12d95578885ecd267d7d09e049919ff10464` | Akamai renderer 支持 `hosts[].volume`，并生成 `module.volume_web_saas_k3s_v6`；compute_protected 保护节点 | storage 模块尚无 `prevent_destroy`；`cmdb_runtime`/inventory 尚不携带卷身份与设备信息。需 owner PR 补齐卷保护、权威输出及重跑验证，不能以 global 的节点保护代替卷保护 |
| Playbooks `e18f112536ce293532dee7b6f7ce0df21b1d7b8f` | 已有 `web_saas_data_volume` 空盘检查与 UUID 挂载角色 | 角色当前只接受特定 Web SaaS/恢复主机，不接受当前 V6 inventory 身份；需基于 CMDB 的最小 V6 接入、挂载前置、持久卷供给路径及重启验证，不能靠伪造旧主机别名绕过 |
| 同一 Playbooks bootstrap | K3s/Flux 安装及固定 Git commit 输入 | 默认 kubeconfig 0644、Git 分支 main 和通用 root 都不可直接套用；显式 0600、经 release tag 核实的 SHA、V6 root/source 名与暂停状态，审查是否自动 reconcile |
| Platform-Orchestrator `33fe2bbfcb73283fa4092498f18b37e5b5a8811a` | `iac-orchestrator.yml` 可选 prod、目标 manifest 和 resources stage | 精确固定 V6 target 与资源路径、IaC SHA、GitOps release ref、受保护 PROD 入口和 OIDC 身份；本次未验证实际权限和云 API 可达性 |
| 同一控制面 `web-saas-k3s-orchestrator.yml` | 现有 K3s UAT/V5 调度链 | 文件强制 V5 namespace，使用 UAT 环境/凭据且默认开启测试 DNS；不能仅修改 target 输入用于 PROD V6。需独立审查 V6 调度契约或采用已授权的固定 Playbooks 路径 |

现有 K3s bootstrap 还会直接创建并 reconcile `platform-root`，与 V6 草案的根对象命名和
逐单元暂停策略不一致。V6 的 source、root、子 Kustomization 和 HelmRelease 需统一声明，
验证 bootstrap 不会提前放行服务。只解除子 Kustomization 暂停不会自动解除 HelmRelease 暂停；
每一步明确解除哪一层，GitOps 保持目标状态，避免父级再次覆盖现场临时更改。

本地其他 owner checkout 存在无关修改，本轮只读远端 main，没有改动这些工作树。
K3s、Flux、Helm 及所有 chart/image 候选还需核实官方发布、校验和、chart values 和依赖兼容性；
仓库默认值不能替代该项验证。业务目标库名、PostgreSQL 17 及 Accounts/Billing schema
checkpoint 按实际 `migratectl` 固定版本的要求由迁移 owner 创建与验证。

## 进入创建阶段的顺序与放行结果

| 阶段 | 完成条件 | 当前状态 |
| --- | --- | --- |
| 0 声明与候选固定 | 五单元、独立节点/卷、目标/state 和 source ref 审查通过；发布标签包含 V6 路径 | 本地声明已准备，正式 release ref 未选择 |
| 1 创建前检查 | 账户、region、plan、image、卷容量/费用、源数据量、预算、受控入口通过；上述 owner 缺口关闭 | BLOCKED，尚未做云端 preflight |
| 2 云资源 plan | 只新增 V6 节点、独立卷及 firewall；无 V5、DNS、共享 SSH key 变更，无修改/删除/替换既有资源 | NOT_RUN |
| 3 IaC 创建 | 依已审查的同一 plan 执行，输出并核验 CMDB、节点和卷身份 | NOT_RUN；创建另按任务授权执行 |
| 4 主机/存储/集群 | 安全身份、空盘核验、UUID 挂载、供给路径、固定版本 K3s/Flux 和暂停声明验证 | NOT_RUN |
| 5 五单元冷启动 | Vault → PostgreSQL → Ingress → Observability → Web SaaS，逐单元准备依赖并验收；业务独立写者暂停 | NOT_RUN |
| 6 核心数据与恢复验收 | 备份/恢复、`migratectl` 预览及审查后的复制、差异/回归、含业务数据的隔离恢复和观察 | NOT_RUN；数据写入另按任务授权执行 |
| 7 待切换报告 | 列出未完成项、最终追齐及写入权/流量交接方案 | NOT_RUN；V5 不切换、不退役 |

内存预算建议先按 8 GiB 中约 2 GiB 留给 OS/控制面/Flux、工作负载 requests 总量不超过
5 GiB、约 1 GiB 余量核算，再以实际 allocatable、全量 chart 渲染和压力/恢复数据修正。
这不是已通过的容量结果；持续 CPU/I/O 争用或内存不足时，应在创建前评审更大方案或拆分节点。

云费用按节点、独立卷、备份/对象存储、恢复演练容量和双代并行窗口分别核算。
当前公开价目列出 Shared 8 GB / 4 vCPU / 160 GB SSD 为 $48/月参考，实际 Tokyo 账户报价、
税费及 Block Storage 单价待核实；本轮不设已批准费用，也不声称已完成 provider preflight。

来源：[Akamai 亚太价格](https://www.akamai.com/cloud/pricing/asia-pacific)、
[Block Storage](https://techdocs.akamai.com/cloud-computing/docs/block-storage)、
[卷挂载说明](https://techdocs.akamai.com/cloud-computing/docs/configure-and-mount-a-volume)、
[K3s 要求](https://docs.k3s.io/installation/requirements)。

## 本轮离线检查

- 从上述 IaC main SHA 导出到临时目录，使用正式 Akamai `generate.py render` 消费 V6
  声明：通过，生成独立节点、firewall 和 100 GB 数据卷模块，包含 Terraform fmt。
- 五个服务目录及 V6 集群目录分别执行 `kubectl kustomize`：6 项通过。该检查不渲染远端
  Helm chart，不能证明 chart values、镜像、Ingress/TLS、数据库连接或实际部署有效。
- 未执行 Terraform init/plan/apply、云 API 调用、SSH、格式化/挂载、数据库操作或 workflow dispatch。
  临时生成的 HCL、运行配置和构建输出均在仓库外，不作为运行 CMDB 或执行回执提交。
