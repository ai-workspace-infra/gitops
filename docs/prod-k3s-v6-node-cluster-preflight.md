# PROD-K3S-V6 独立节点与集群创建准备

状态：规划与声明阶段，尚未执行云端 preflight、Terraform plan/apply、挂载或部署。
升级分类遵循已合并的[技能 PR #63](https://github.com/ai-workspace-lab/xworkspace-core-skills/pull/63)。
V6 是全新节点、全新 K3s 集群、全新数据卷；V5 保持当前服务、SQL schema 和写入权。

V6 GitOps 结构以[专属层级规划](prod-k3s-v6-gitops-hierarchy.md)为准：一个引导源和根
Kustomization 管理五个单元的独立 GitRepository/子 Kustomization，各自维护 HelmRelease。
共用仓库，配置 tag、chart 版本和调谐范围独立；根不会连带升级其他四个单元。

## 节点与资源边界

| 项目 | 本轮方案 | 创建前核实 |
| --- | --- | --- |
| 云及地域 | 沿用 V6 GitOps 资源声明中的 Akamai 账户和 Tokyo 3 地域 | 实际账户身份、地区容量、计算/卷配额、费用 |
| 计算 | 用户已选定 1 台 `g6-standard-2`，2 个共享 vCPU / 4 GB RAM，Debian 13 候选 | 实际 plan/image 可用性及各镜像 amd64 兼容性；创建节点不等于完整业务栈容量验收 |
| 系统盘 | 实例方案自带 SSD；OS、容器镜像/运行时及 K3s 控制面 | 实际容量、空闲空间、inode、控制面写入延迟 |
| 独立数据盘 | 同地域新建 1 块 `prod-k3s-v6-data`，100 GB，ext4 | 单位为 provider GB；格式化后可用容量、I/O、保护及恢复能力 |
| 集群 | 单节点 K3s server，同时运行工作负载；独立集群身份与 CA | hostname、machine ID、SSH 指纹、集群 UID/CA 均不得沿用 V5 |
| 状态 | 使用现有 V6 独立 workspace/backend key；一个 V6 节点和一个 V6 卷 | 不导入、不移动、不删除 V5 state；不共用 V5 卷或快照恢复原盘 |
| 可用性 | 单节点冷启动和迁移验收候选 | 节点故障会影响所有 V6 单元；Raft 单副本及独立盘都不构成 HA |

此方案保留后续 UI/API 兼容小修复和独立监控服务按各自发布单元原地更新的能力。
业务 DB、SQL schema 和其他业务持久状态转换继续使用下一代新集群。
单节点 Caddy 使用 hostPort 80/443 时也会存在重启窗口，不能承诺零停机滚动。

本轮将尚未执行创建的 V6 声明标识收敛为 `prod-k3s-v6`，未执行 Terraform state 移动。
创建前仍需核对旧 V6 声明标识是否已有云实例/后端 state；若存在，停止新增并先审查准确的
资源身份与 state 处理方案，不能靠改名重复创建或接管旧资源。

## V6 GitOps 层级与独立更新

| 层级 | V6 对象 | 数量 | 声明位置与职责 |
| --- | --- | --- | --- |
| 引导 GitRepository | `flux-system/config-prod` | 1 | `source.yaml`；固定 V6 根管理图版本 |
| 根 Flux Kustomization | `flux-system/prod-k3s-v6` | 1 | `root.yaml` 也进入根 `kustomization.yaml`；管理 namespace、五个单元源和五个子 Kustomization |
| 单元 GitRepository | `<unit>-config`，均在 `flux-system` | 5 | `unit-sources.yaml`；同一 Git 仓库、每单元独立 tag/commit |
| 子 Flux Kustomization | `<unit>`，均在 `flux-system` | 5 | 每个单元独立 sourceRef、`services/prod-k3s-v6/<unit>` 路径及暂停/健康等待状态 |
| Chart 源 | 服务 namespace 中 HelmRepository / OCIRepository | 2 / 5 | Vault/DataKit 用 HelmRepository；数据库/入口/业务三个 release 使用同一个 fullstack chart 包，各自保留本 namespace 的 OCI source |
| HelmRelease | 下表列出的发布对象 | 7 | 每个 release 独立 chart/values/版本与暂停状态；服务资源由 Helm controller 管理 |

总计为 **6 个 GitRepository、1 个根和 5 个子 Flux Kustomization、7 个 HelmRelease**。
五个发布单元继续共用一个 GitOps 仓库，不要求拆仓库；监控使用三个已有 chart，因此有三个 HelmRelease。

### 环境、集群及 GitOps 对象关联表

集群展示名统一为 **`PROD-K3S-V6`**；hostname、Kubernetes 对象、目录和 state 技术标识使用
小写 `prod-k3s-v6`。下表 `namespace` 指工作负载所在
namespace，HelmRelease 也在该 namespace。**所有 Flux Kustomization 和 GitRepository
均位于 `flux-system`**，下表省略其相同 namespace 前缀。GitRepository 列指配置 Git 源，
不是 OCIRepository/HelmRepository chart 源；source path 为 Kustomization 的 `spec.path`。

| 环境 | 集群 | namespace | Kustomization（flux-system） | HelmRelease | GitRepository（flux-system） | source path |
| --- | --- | --- | --- | --- | --- | --- |
| PROD | **PROD-K3S-V6** | `flux-system`（控制层） | `prod-k3s-v6` | —（根不直接发布 chart） | `config-prod` | `./environments/clusters/prod-k3s-v6` |
| PROD | **PROD-K3S-V6** | `vault-prod` | `vault-prod` | `vault` | `vault-prod-config` | `./services/prod-k3s-v6/vault-prod` |
| PROD | **PROD-K3S-V6** | `postgresql-prod` | `postgresql-prod` | `postgresql` | `postgresql-prod-config` | `./services/prod-k3s-v6/postgresql-prod` |
| PROD | **PROD-K3S-V6** | `ingress-prod` | `ingress-prod` | `caddy-ingress` | `ingress-prod-config` | `./services/prod-k3s-v6/ingress-prod` |
| PROD | **PROD-K3S-V6** | `observability-prod` | `observability-prod` | `observability` | `observability-prod-config` | `./services/prod-k3s-v6/observability-prod` |
| PROD | **PROD-K3S-V6** | `observability-prod` | `observability-prod` | `observability-agent` | `observability-prod-config` | `./services/prod-k3s-v6/observability-prod` |
| PROD | **PROD-K3S-V6** | `observability-prod` | `observability-prod` | `datakit` | `observability-prod-config` | `./services/prod-k3s-v6/observability-prod` |
| PROD | **PROD-K3S-V6** | `web-saas-prod` | `web-saas-prod` | `web-saas-prod` | `web-saas-prod-config` | `./services/prod-k3s-v6/web-saas-prod` |

根图使用同一个仓库 URL；每个 GitRepository 的 tag/commit 独立固定。source path 是该源
版本下的仓库相对目录，不能将其视为节点文件路径。根 source 的 tag 与被选根版本中
`source.yaml` 的自身 pin 保持一致；单元配置源的 pin 则可独立推进，防止根 reconcile 把
现场临时选定的版本覆盖回旧值。

六个 GitRepository 的 `spec.url` 均为 **`https://github.com/ai-workspace-infra/gitops.git`**。
它们是同仓库的六个独立 source 对象，不是六个仓库；各单元保留独立配置 ref。

### PostgreSQL、Caddy、Web SaaS 共用一个 chart 包

三个 release 的 chart URL 均为 `oci://ghcr.io/ai-workspace-infra/distributed-web-saas-fullstack`。
它们只有 HelmRelease、namespace、values 和版本引用不同；无需为拆分发布再维护三个 chart 包。
各 namespace 的 `web-saas-fullstack-chart` OCIRepository 初始固定同一个已验证 digest，
以后可分别保留版本；DB/业务状态转换仍受新集群规则限制。

| HelmRelease | namespace | 启用的 chart 组件 | 必须关闭 | 连接约定 |
| --- | --- | --- | --- | --- |
| `postgresql` | `postgresql-prod` | `postgresql.enabled: true` | Caddy、UI/API、edgeGateway、stunnel | releaseName `postgresql`；Service `postgresql-postgresql`，空目标库 `account` |
| `caddy-ingress` | `ingress-prod` | `caddy.enabled: true`，`externalBackends.enabled: true` | PostgreSQL、Console、Accounts、Billing、Content、edgeGateway、stunnel | 独立 Caddy 反向代理，经显式 FQDN 连接业务 namespace；不是另装 Ingress API controller |
| `web-saas-prod` | `web-saas-prod` | Console、Accounts、Billing、Content | PostgreSQL、Caddy、edgeGateway、stunnel | releaseName `web-saas`，应用连接 `postgresql-postgresql.postgresql-prod.svc.cluster.local` |

现有公开 chart 的校验要求 Caddy 与本地 Console/Accounts 同时启用。Artifacts owner 分支已补充
独立 Caddy `externalBackends` 契约：显式上游、禁止重复部署业务/数据库、保留旧 combined 模式。
该源版本为 0.2.10 候选；需经 PR、发布工作流和新 OCI digest 验证后，统一更新 V6 三个初始
chart pin。当前旧 digest 保持暂停占位，不得作为独立 Caddy 已可部署的证据。
跨 namespace DB NetworkPolicy、TLS Secret、Vault/观测入口路由和实际资源预算仍需相应验收。

| 发布单元 | 最小单元依赖 | 独立发布说明 |
| --- | --- | --- |
| Vault | 无 | TLS/初始化/unseal 为外部引导前置 |
| PostgreSQL | Vault | 不依赖 Ingress 或监控 |
| Ingress | Vault | 不依赖 PostgreSQL |
| Observability | Vault | 不依赖 Ingress 或业务 |
| Web SaaS | Vault、PostgreSQL | 不依赖独立监控/Ingress 的发布健康；业务对外验收仍检查入口和观测链路 |

| 更新类型 | 修改与生效路径 | 其他单元影响及限制 |
| --- | --- | --- |
| 根管理图 | 更新根配置 release tag，根 Kustomization 收敛单元引用/放行状态 | 不自动推进五个单元的配置 tag 或 chart 版本 |
| 单元配置 | 发布选中单元路径的新配置 tag，再在根管理图只推进该单元 GitRepository 的 ref | 其他四个配置 pin 保留；同仓库不等于同版本 |
| 单个 HelmRelease | 在所属单元配置 tag 中更新该 release 的 chart version/OCI digest/values/镜像引用 | 不连带修改同单元其他 release；当前 fullstack chart 内 UI/API 仍共用其一个 HelmRelease |
| UI/API 小修复 | 无 schema/持久格式变化且向后兼容时，只更新 `web-saas-prod` 的相应制品 | 可原地发布，需业务回归；代码回退不回滚数据 |
| 独立监控 | 只更新监控单元中选中的 release | 非业务、非账单范围内可原地更新；维护不阻断业务发布，仍需采集/查询及备份恢复证据 |
| DB/schema/业务状态转换 | 下一代新集群、空目标库/独立存储，按审查后的路径迁移和验收 | 禁止靠在 V6 修改有状态 release pin 原地升级；保留 V6 源与写入权 |

| 阶段 | Source / Kustomization / HelmRelease 状态 | 执行约束 |
| --- | --- | --- |
| 首次加载 | 六 GitRepository、六 Flux Kustomization、七 HelmRelease 全部 `suspend: true` | Playbooks 从固定 checkout 校验并加载完整声明，不另外生成 `platform-root`，不主动 reconcile |
| 管理图放行 | 先启用引导 GitRepository 和根 Kustomization | 单元配置源、子 Kustomization、HelmRelease 仍保持暂停 |
| 单元冷启动 | 按选中单元依次放行其 GitRepository、子 Kustomization、相应 HelmRelease | 冷启动顺序为 Vault → PostgreSQL → Ingress → Observability → Web SaaS；该人工顺序不等于全部写成 dependsOn |
| 单元独立维护 | 保持正常运行单元状态，仅修改被选中单元的声明与 pin | 所有暂停状态在权威 GitOps 声明中维护；不靠现场 resume 对抗父级旧声明 |
| 健康验收 | source/子 Kustomization/HelmRelease 与目标 revision 一致，再检查实际链路 | 暂停 HR 不会因解除子 Kustomization 暂停而自动运行；`wait: true` 须与 HR 放行配套，Ready 不等于数据或业务验收 |

根、Vault/PostgreSQL/监控子 Kustomization 已设置 `prune: false`，保留数据相关对象；
仍须验证 Helm 自身删除行为、PVC `Retain`、云卷保护和备份，不能把 prune 关闭当作完整数据保护。
首次六个 Git source pin 必须共同指向包含 V6 目录的正式候选，后续才各自推进。
现有暂停占位 tag 不含 V6 路径，创建/部署放行前需替换并核验。

## 部署所需 Vault KV 路径

以下仅记录路径、字段名和消费者，未读取或写入任何密钥值。“已有引用”表示代码中已声明，
不代表已验证远端记录存在或实际身份可读；“V6 规划”仍需 owner 创建、精确授权和拒绝路径验证。
现有运维 Vault 用于 IaC/SSH 和 V6 Vault 的初始信任引导，不能依赖尚未初始化的 V6 Vault 自举。
V6 服务运行凭据在新 Vault 就绪后通过其内部 SecretStore/ESO 同步，端点与信任链必须明确区分。

| 阶段 / 用途 | Vault KV v2 API path | 字段名（不含值） | 消费方 / Kubernetes Secret | 状态 |
| --- | --- | --- | --- | --- |
| IaC 云账户 | `kv/data/CICD/prod/akamai-cloud/manbuzhe2026` | `LINODE_TOKEN` | IaC `auth.record` / `prod-akamai-iac` 对应受控身份 | 已有 V6 声明引用，未远端验证 |
| Terraform backend | `kv/data/CICD/prod/iac_state` | `TF_STATE_ENDPOINT`、`TF_STATE_BUCKET`、`TF_STATE_REGION`、`TF_STATE_ACCESS_KEY`、`TF_STATE_SECRET_KEY` | IaC backend，仍使用 V6 独立 state key | IaC 代码默认路径，未远端验证 |
| 主机引导 SSH | `kv/data/prod/platform/prod-k3s-v6/ssh` | `SSH_PRIVATE_KEY`，并配套受信任主机指纹来源 | Playbooks 的专用操作身份；不授予业务 Pod | V6 规划，需 caller 接线 |
| Vault server 初始 TLS | `kv/data/prod/services/vault-prod/tls/prod-k3s-v6-server` | `tls_fullchain_pem`、`tls_key_pem`、`issuer`、`expire_at` | `vault-prod/vault-server-tls`；首次来自外部可信引导面 | V6 规划，需避免 ESO/Vault 自举循环 |
| PostgreSQL 管理/初始化 | `kv/data/prod/services/postgresql-prod/prod-k3s-v6/admin` | `POSTGRES_PASSWORD` | `postgresql-prod/postgresql-superuser`；仅管理初始化/迁移身份 | V6 规划，业务身份不得读取 |
| Accounts DB | `kv/data/prod/services/web-saas-prod/prod-k3s-v6/accounts-db` | `POSTGRES_PASSWORD` / `DATABASE_URL`，按实际应用契约映射 | `web-saas-prod/accounts-db-runtime` | V6 规划，独立运行角色 |
| Billing DB | `kv/data/prod/services/web-saas-prod/prod-k3s-v6/billing-db` | `POSTGRES_PASSWORD` / `DATABASE_URL`，按实际应用契约映射 | `web-saas-prod/billing-db-runtime` | V6 规划，不共享 Accounts 写角色 |
| Accounts 认证 | `kv/data/prod/services/web-saas-prod/prod-k3s-v6/accounts-runtime` | JWT/内部服务认证所需字段，由 Accounts owner 定义 | `web-saas-prod/accounts-runtime` | V6 规划，禁止将 JWT 私密字段授予无关服务 |
| Billing 运行配置 | `kv/data/prod/services/web-saas-prod/prod-k3s-v6/billing-runtime` | 支付/回调/内部服务认证所需字段，由 Billing owner 定义 | `web-saas-prod/billing-runtime` | V6 规划；候选禁真实扣退款副作用 |
| Content 运行配置 | `kv/data/prod/services/web-saas-prod/prod-k3s-v6/content-runtime` | `INTERNAL_SERVICE_TOKEN` 等 Content 必需字段 | `web-saas-prod/content-runtime` | V6 规划，按业务最小权限接线 |
| Grafana | `kv/data/prod/services/observability-prod/prod-k3s-v6/grafana` | `admin_password` → Secret `password` | `observability-prod/grafana-admin` | V6 规划 |
| DataKit | `kv/data/prod/services/observability-prod/prod-k3s-v6/datakit` | DataWay 认证字段，按固定 chart 契约映射 | 规划 `observability-prod/datakit-runtime` | V6 规划，chart Secret 引用尚需核实 |
| Console 公网 TLS | `kv/data/prod/services/ingress-prod/tls/prod-k3s-v6-console` | `tls_fullchain_pem`、`tls_key_pem`、`issuer`、`expire_at` | `ingress-prod/console-tls` | V6 规划 |
| Accounts 公网 TLS | `kv/data/prod/services/ingress-prod/tls/prod-k3s-v6-accounts` | 同上 | `ingress-prod/accounts-tls` | V6 规划 |
| Billing 公网 TLS | `kv/data/prod/services/ingress-prod/tls/prod-k3s-v6-billing` | 同上 | `ingress-prod/billing-tls` | V6 规划 |
| Vault 公网 TLS | `kv/data/prod/services/ingress-prod/tls/prod-k3s-v6-vault` | 同上 | `ingress-prod/vault-tls` | V6 规划，与 Vault server 内部 TLS 分开 |
| Observability 公网 TLS | `kv/data/prod/services/ingress-prod/tls/prod-k3s-v6-observability` | 同上 | `ingress-prod/observability-tls` | V6 规划 |
| 迁移源读取 | `kv/data/prod/platform/prod-k3s-v6/migration-source` | `SOURCE_DSN`，仅实际只读源身份 | 迁移 owner 运行时环境；不提供给应用 Pod | V6 规划，迁移另按授权执行 |
| 迁移目标写入 | `kv/data/prod/platform/prod-k3s-v6/migration-target` | `TARGET_DSN`，受控目标迁移身份 | `migratectl`/迁移执行器；与业务运行身份分开 | V6 规划，迁移另按授权执行 |

| 表示方式 / 身份边界 | V6 规则 |
| --- | --- |
| Vault CLI path | 例如 `kv/prod/services/ingress-prod/tls/prod-k3s-v6-console`；CLI 自动处理 KV v2 的 `/data/` |
| API / policy path | 对应 `kv/data/prod/services/ingress-prod/tls/prod-k3s-v6-console`；按具体记录授予读取权限，不给跨环境/跨单元通配权限 |
| ESO remoteRef.key | `SecretStore.path: kv`、`version: v2` 时填 `prod/services/ingress-prod/tls/prod-k3s-v6-console`，不重复加 `kv/` 或 `data/` |
| TLS 字段映射 | ESO 将 `tls_fullchain_pem` / `tls_key_pem` 映射为标准 `kubernetes.io/tls` Secret 的 `tls.crt` / `tls.key`，Secret 位于消费 Pod 的 namespace |
| V6 workload auth | Kubernetes auth mount 规划为 `kubernetes-prod-k3s-v6`；各 namespace/服务独立 SA、Vault role 和 audience，禁止业务身份读取 IaC/SSH/数据库管理记录 |
| Vault 恢复材料 | unseal/recovery/root 初始化材料由安全 owner 保存在集群外独立受保护恢复存储；不放入依赖该 V6 Vault 自身解锁的业务 KV，不提交 Git/artifact |
| 现有 V5 路径 | 不将 V5 的 `web-saas-k3s-v5` 记录当作 V6 缺值兜底；必要的认证/会话连续性由 owner 逐字段审查，而非自动轮换或批量复制 |

新规划路径必须形成 GitOps SecretStore/ExternalSecret 声明与 owner 的 Vault policy/auth 变更，
验证准确映射到 chart 的 Secret 名称/字段后才可解除相应 HelmRelease 暂停。以上规划表不是授权
执行 KV 写入、凭据轮换或数据迁移，也不代表这些 ExternalSecret 已创建或同步成功。

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
| IaC `3cfc12d95578885ecd267d7d09e049919ff10464` | Akamai renderer 支持 `hosts[].volume`，并生成 `module.volume_prod_k3s_v6`；compute_protected 保护节点 | storage 模块尚无 `prevent_destroy`；`cmdb_runtime`/inventory 尚不携带卷身份与设备信息。需 owner PR 补齐卷保护、权威输出及重跑验证，不能以 global 的节点保护代替卷保护 |
| Playbooks `e18f112536ce293532dee7b6f7ce0df21b1d7b8f` | 已有 `web_saas_data_volume` 空盘检查与 UUID 挂载角色 | 角色当前只接受特定 Web SaaS/恢复主机，不接受当前 V6 inventory 身份；需基于 CMDB 的最小 V6 接入、挂载前置、持久卷供给路径及重启验证，不能靠伪造旧主机别名绕过 |
| 同一 Playbooks bootstrap | K3s/Flux 安装及固定 Git commit 输入 | 本轮 owner 分支新增 `declarative_paused`：从固定 checkout 加载完整声明图、验证初始全部暂停并跳过 reconcile；需完成 PR/固定 owner SHA 后使用。V6 声明已显式选 0600 和专属 root/source 名 |
| Platform-Orchestrator `33fe2bbfcb73283fa4092498f18b37e5b5a8811a` | `iac-orchestrator.yml` 可选 prod、目标 manifest 和 resources stage | 精确固定 V6 target 与资源路径、IaC SHA、GitOps release ref、受保护 PROD 入口和 OIDC 身份；本次未验证实际权限和云 API 可达性 |
| 同一控制面 `web-saas-k3s-orchestrator.yml` | 现有 K3s UAT/V5 调度链 | 文件强制 V5 namespace，使用 UAT 环境/凭据且默认开启测试 DNS；不能仅修改 target 输入用于 PROD V6。需独立审查 V6 调度契约或采用已授权的固定 Playbooks 路径 |
| Artifacts 的 fullstack chart | 单包内 PostgreSQL、Caddy 和业务组件均有启用开关 | 三 HelmRelease 使用同包；独立 Caddy 跨 namespace 契约需合并、发布 0.2.10 候选并固定新 digest，旧 pin 不具备该契约 |

已修正 V6 设计：root.yaml 进入根资源列表，五个子单元改用各自独立 GitRepository。
与之配套的 Playbooks owner 分支通过 `declarative_paused` 模式加载 source、root、
子 Kustomization、chart source 和 HelmRelease，不生成或 reconcile `platform-root`。
首次 source/root/子 Kustomization/HelmRelease 全部暂停；后续按根声明与单元配置声明
逐层放行。旧 generated 模式只保留既有调用兼容，V6 不选择它。
只解除子 Kustomization 暂停不会自动解除 HelmRelease 暂停；具体步骤和最小依赖见层级文档。

本地其他 owner checkout 存在无关修改，已保留；Playbooks 改动在独立 worktree 中完成。
K3s、Flux、Helm 及所有 chart/image 候选还需核实官方发布、校验和、chart values 和依赖兼容性；
仓库默认值不能替代该项验证。业务目标库名、PostgreSQL 17 及 Accounts/Billing schema
checkpoint 按实际 `migratectl` 固定版本的要求由迁移 owner 创建与验证。

## 进入创建阶段的顺序与放行结果

| 阶段 | 完成条件 | 当前状态 |
| --- | --- | --- |
| 0 声明与候选固定 | 六 GitRepository、唯一根/五子 Kustomization、七 HelmRelease、独立节点/卷及目标/state 审查通过；发布标签包含 V6 路径 | 本地声明已准备，正式 release ref 未选择 |
| 1 创建前检查 | 账户、region、plan、image、卷容量/费用、源数据量、预算、受控入口通过；上述 owner 缺口关闭 | BLOCKED，尚未做云端 preflight |
| 2 云资源 plan | 只新增 V6 节点、独立卷及 firewall；无 V5、DNS、共享 SSH key 变更，无修改/删除/替换既有资源 | NOT_RUN |
| 3 IaC 创建 | 依已审查的同一 plan 执行，输出并核验 CMDB、节点和卷身份 | NOT_RUN；创建另按任务授权执行 |
| 4 主机/存储/集群 | 安全身份、空盘核验、UUID 挂载、供给路径、固定版本 K3s/Flux 和暂停声明验证 | NOT_RUN |
| 5 五单元冷启动 | Vault → PostgreSQL → Ingress → Observability → Web SaaS，逐单元准备依赖并验收；业务独立写者暂停 | NOT_RUN |
| 6 核心数据与恢复验收 | 备份/恢复、`migratectl` 预览及审查后的复制、差异/回归、含业务数据的隔离恢复和观察 | NOT_RUN；数据写入另按任务授权执行 |
| 7 待切换报告 | 列出未完成项、最终追齐及写入权/流量交接方案 | NOT_RUN；V5 不切换、不退役 |

按用户选定的 4 GB 节点核算容量：先测 OS/K3s/Flux/ESO 基线和实际 allocatable，再分配
五单元 requests/limits 与余量。此前 V5 历史 memory requests 约 3,340 MiB，不能直接当成
V6 容量验收结果。按当前规格创建节点与后续放行全部业务分别记录；没有足够容量时停在
对应单元验收，不自动变更用户选定的云规格，也不以创建成功宣称整个业务栈通过。

云费用按节点、独立卷、备份/对象存储、恢复演练容量和双代并行窗口分别核算。
按已选择的 Shared 4 GB / 2 vCPU 重新核实实际 Tokyo 账户报价、税费及 Block Storage 单价；
旧 8 GB 方案的参考价不适用于本轮。本轮不声称已完成 provider preflight。

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
