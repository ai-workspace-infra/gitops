# PROD-K3S-V6 独立节点与集群创建准备

状态：正式支持已合入；独立云节点、100 GB 数据盘与 firewall 已创建并验证。
IaC 后自动 common、独立盘挂载和 K3s/Flux 暂停式集群引导均已通过；业务发布和数据验收尚未执行。
新建执行状态与证据见下文阶段表；不将暂停式引导计为业务部署或数据验收。
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

创建前已将 V6 声明标识收敛为 `prod-k3s-v6`；本轮在该独立 state 新建，未执行 V5 state 移动。
旧 V6 声明的 backend key 作为只读历史来源保留在 catalog，未导入、移动或接管；不将
声明改名当成旧状态已清空的证据。新目标使用自己的云资源与 state 归属校验。

## V6 GitOps 层级与独立更新

| 层级 | V6 对象 | 数量 | 声明位置与职责 |
| --- | --- | --- | --- |
| 引导 GitRepository | `flux-system/config-prod` | 1 | `source.yaml`；固定 V6 根管理图版本 |
| 根 Flux Kustomization | `flux-system/prod-k3s-v6` | 1 | `root.yaml` 也进入根 `kustomization.yaml`；仅应用管理图，`wait: false` 使暂停子对象独立报告状态 |
| 单元 GitRepository | `<unit>-config`，均在 `flux-system` | 5 | `unit-sources.yaml`；同一 Git 仓库、每单元独立 tag/commit |
| 业务子 Flux Kustomization | `<unit>`，均在 `flux-system` | 5 | 每个单元独立 sourceRef、`services/prod-k3s-v6/<unit>` 路径及暂停/健康等待状态 |
| 集群前置 Flux Kustomization | `external-secrets`、`vault-tls-identity`、`vault-tls-bootstrap` | 3 | ESO controller/CRD、身份预置与 Vault server TLS Secret 引导；不增加业务发布单元 |
| Chart 源 | 服务 namespace 中 HelmRepository / OCIRepository | 3 / 5 | ESO/Vault/DataKit 用 HelmRepository；数据库/入口/业务三个 release 使用同一个 fullstack chart 包，各自保留本 namespace 的 OCI source |
| HelmRelease | 下表列出的发布对象 | 8 | 七个业务 release 加一个 ESO controller release；每个 release 独立 chart/values/版本与暂停状态 |

总计为 **6 个 GitRepository、1 个根 + 5 个业务 + 3 个前置 Flux Kustomization、8 个 HelmRelease**。
八个 HelmRelease 包含五单元的七个业务 release 和独立的 ESO controller release。五个发布单元继续
共用一个 GitOps 仓库，不要求拆仓库；监控使用三个已有 chart，因此有三个业务 HelmRelease。

### 环境、集群及 GitOps 对象关联表

集群展示名统一为 **`PROD-K3S-V6`**；hostname、Kubernetes 对象、目录和 state 技术标识使用
小写 `prod-k3s-v6`。下表 `namespace` 指工作负载所在
namespace，HelmRelease 也在该 namespace。**所有 Flux Kustomization 和 GitRepository
均位于 `flux-system`**，下表省略其相同 namespace 前缀。GitRepository 列指配置 Git 源，
不是 OCIRepository/HelmRepository chart 源；source path 为 Kustomization 的 `spec.path`。

| 环境 | 集群 | namespace | Kustomization（flux-system） | HelmRelease | GitRepository（flux-system） | source path |
| --- | --- | --- | --- | --- | --- | --- |
| PROD | **PROD-K3S-V6** | `flux-system`（控制层） | `prod-k3s-v6` | —（根不直接发布 chart） | `config-prod` | `./environments/clusters/prod-k3s-v6` |
| PROD | **PROD-K3S-V6** | `external-secrets` | `external-secrets` | `external-secrets` | `config-prod` | `./services/prod-k3s-v6/cluster-prerequisites/external-secrets` |
| PROD | **PROD-K3S-V6** | `vault-prod`（身份前置） | `vault-tls-identity` | —（ServiceAccount / RBAC） | `vault-prod-config` | `./services/prod-k3s-v6/vault-prod/tls-identity` |
| PROD | **PROD-K3S-V6** | `vault-prod`（TLS 前置） | `vault-tls-bootstrap` | —（ESO ExternalSecret） | `vault-prod-config` | `./services/prod-k3s-v6/vault-prod/tls-bootstrap` |
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

Artifacts [PR #246](https://github.com/ai-workspace-infra/artifacts/pull/246) 已合入，
[发布运行 40833566718](https://github.com/ai-workspace-infra/artifacts/actions/runs/40833566718)
已发布 chart **0.2.10**。V6 三个独立 release 均固定初始 OCI digest
`sha256:45c2f15ab10499d7a44dc59a844246283db7bd26ff748a4b21e2207f2e749ffe`。
Caddy `externalBackends` 显式引用跨 namespace 上游，禁止重复部署业务/数据库。
跨 namespace DB NetworkPolicy、TLS Secret、Vault/观测入口路由和实际资源预算仍需相应验收。

| 发布单元 | 最小单元依赖 | 独立发布说明 |
| --- | --- | --- |
| ESO + Vault TLS 引导 | Flux 已就绪 | 仅读取公共 Vault 的单一域名证书 KV；Role/Policy 需独立就绪 |
| Vault | ESO 与 `vault-tls-bootstrap` | 只在 TLS Secret Ready 后安装；初始化/unseal 仍由 Vault owner 执行 |
| PostgreSQL | Vault | 不依赖 Ingress 或监控 |
| Observability | Vault | 不依赖 Ingress 或业务 |
| Web SaaS | Vault、PostgreSQL | 不依赖独立监控/Ingress 的发布健康；业务对外验收仍检查入口和观测链路 |
| Ingress | Vault、Observability、Web SaaS | 最后放行以便 V6-only 路由/TLS 验收；公共 DNS 不在本阶段切换 |

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
| 首次加载 | 六 GitRepository、八 Flux Kustomization、八 HelmRelease 全部 `suspend: true` | Playbooks 从固定 checkout 校验并加载完整声明，不另外生成 `platform-root`，不主动 reconcile |
| 管理图放行 | 先启用引导 GitRepository 和根 Kustomization | 五个业务单元及三个前置 Kustomization/HelmRelease 仍保持暂停 |
| ESO 与 Vault TLS 前置 | 先放行 ESO controller/CRD；准备公共 Vault JWT auth 只读角色；再同步 `vault-server-tls` | Secret Ready、证书/私钥匹配、SAN 和有效期验收通过后，才放行 Vault HelmRelease |
| 单元冷启动 | Vault → PostgreSQL → Observability → Web SaaS → Ingress | Vault 完成初始化与内部 SecretStore 后逐单元放行；Ingress 最后，公共 DNS 保持不变 |
| 单元独立维护 | 保持正常运行单元状态，仅修改被选中单元的声明与 pin | 所有暂停状态在权威 GitOps 声明中维护；不靠现场 resume 对抗父级旧声明 |
| 健康验收 | source/子 Kustomization/HelmRelease 与目标 revision 一致，再检查实际链路 | 暂停 HR 不会因解除子 Kustomization 暂停而自动运行；`wait: true` 须与 HR 放行配套，Ready 不等于数据或业务验收 |

根、Vault/PostgreSQL/监控子 Kustomization 已设置 `prune: false`，保留数据相关对象；
仍须验证 Helm 自身删除行为、PVC `Retain`、云卷保护和备份，不能把 prune 关闭当作完整数据保护。
首次六个 Git source pin 必须共同指向包含 V6 目录的正式候选，后续才各自推进。
TLS identity 分门禁已合并到 GitOps 主干。当前 V6 源需要一份新的固定发布：六个 GitRepository
首发均指向 `v2026.10.29.8`，保持暂停；发布 tag 后再用 Playbooks 的暂停图校验器验证六个源
都解析到同一个已审查提交。后续允许逐个更新单元源 pin 和对应 Kustomization/HelmRelease，
其他单元继续固定原版本。公共 DNS 在本次 V6 冷启动与验收期间保持不启用、不修改。

## 部署所需 Vault KV 路径

以下仅记录路径、字段名和消费者，不保存密钥值。IaC provider/state 路径已由正式短期身份
在实际计划与创建中读取；V6 SSH 绑定由受审查的一次性初始化创建，运行时读取已通过。
其余“V6 规划”路径仍需 owner 创建、精确授权和拒绝路径验证，不代表凭据已就绪。
现有运维 Vault 用于 IaC/SSH 和 V6 Vault 的初始信任引导，不能依赖尚未初始化的 V6 Vault 自举。
V6 服务运行凭据在新 Vault 就绪后通过其内部 SecretStore/ESO 同步，端点与信任链必须明确区分。

| 阶段 / 用途 | Vault KV v2 API path | 字段名（不含值） | 消费方 / Kubernetes Secret | 状态 |
| --- | --- | --- | --- | --- |
| IaC 云账户 | `kv/data/CICD/prod/akamai-cloud/manbuzhe2026` | `LINODE_TOKEN` | IaC `auth.record` / `github-actions-platform-ops-toolkit-prod-k3s-v6-iac` | 实际短期身份读取及云账户校验通过 |
| Terraform backend | `kv/data/CICD/prod/iac_state` | `TF_STATE_ENDPOINT`、`TF_STATE_BUCKET`、`TF_STATE_REGION`、`TF_STATE_ACCESS_KEY`、`TF_STATE_SECRET_KEY` | IaC backend，仍使用 V6 独立 state key | 实际短期身份读取、独立 backend plan/apply 通过 |
| 主机引导 SSH | `kv/data/prod/platform/prod-k3s-v6/ssh` | `SSH_PRIVATE_KEY`，并配套受信任主机指纹来源 | Playbooks 的专用操作身份；不授予业务 Pod | 已初始化，专用 OIDC caller 读取通过；主机指纹核验仍是连接前门禁 |
| V6 Vault server 初始 TLS | `kv/data/CICD/domains/svc.plus` | `tls_fullchain_pem_b64`、`tls_key_pem_b64`；只读 | 公共 `https://vault.svc.plus` → ESO → `vault-prod/vault-server-tls`（`kubernetes.io/tls`） | GitOps/ESO 声明已补；共享 Vault JWT auth mount/role 和精确只读 policy 仍须 owner 配置并验证 |
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
| ESO remoteRef.key | 此公共证书记录使用 `SecretStore.path: kv`、`version: v2` 与 `remoteRef.key: CICD/domains/svc.plus`；不写 `kv/` 或 `data/` 前缀 |
| TLS 字段映射 | ESO 对 `tls_fullchain_pem_b64` / `tls_key_pem_b64` 使用 `decodingStrategy: Base64`，映射成 `tls.crt` / `tls.key` 并生成 `kubernetes.io/tls` Secret |
| V6 workload auth | Kubernetes auth mount 规划为 `kubernetes-prod-k3s-v6`；各 namespace/服务独立 SA、Vault role 和 audience，禁止业务身份读取 IaC/SSH/数据库管理记录 |
| Vault 恢复材料 | unseal/recovery/root 初始化材料由安全 owner 保存在集群外独立受保护恢复存储；不放入依赖该 V6 Vault 自身解锁的业务 KV，不提交 Git/artifact |
| 现有 V5 路径 | 不将 V5 的 `web-saas-k3s-v5` 记录当作 V6 缺值兜底；必要的认证/会话连续性由 owner 逐字段审查，而非自动轮换或批量复制 |

公共证书同步使用独立 JWT auth mount `jwt-prod-k3s-v6`、role `prod-k3s-v6-vault-tls-reader`，
专用受众 `vault-prod-k3s-v6-eso`，绑定 `vault-prod/vault-tls-reader`；只授予读取单一 KV v2
data path `kv/data/CICD/domains/svc.plus` 的权限。Vault JWT verifier 必须信任 V6 K3s service-account
签名公钥和 issuer；ESO chart 关闭默认全局 TokenRequest 权限，仅 RoleBinding 授予它对该 SA 的
`serviceaccounts/token` 创建权限。选择 JWT auth 是为了避免公共 Vault 反向访问 V6 K3s API；不得为
此用途开放公网 6443，也不得在集群中保存静态 Vault token。

先单独放行 `vault-tls-identity` 创建 ServiceAccount，验证实际身份的允许/拒绝访问；
`vault-tls-bootstrap` 必须等验收通过后才放行。Flux 依赖不自动验证 Vault 授权。

ExternalSecret 每 5 分钟刷新，删除策略 `Retain`。放行 Vault HelmRelease 前必须确认
ExternalSecret `Ready=True`、Secret 存在且类型/键名符合 chart contract，证书与私钥匹配、有效期
与 SAN 覆盖 V6 专属 `vault-k3s-v6.svc.plus`。需要集群内消费者用该主机名访问 Vault 时，后续
配置只作用于 V6 的内部 DNS 映射至 Vault ClusterIP；不创建或修改公网 DNS。证书/私钥值不进入 Git、日志、工单或执行回执。
共享 Vault JWT mount/role/policy 尚未证明可用前，保持相关 Kustomization 和 HelmRelease 暂停；
本次文档/声明变更不执行共享 Vault 写入、凭据轮换、业务迁移或 DNS 修改。

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
100 GB 是本轮独立卷创建值；源数据、增长、恢复及导入空间须在放行业务前核算。
不通过时停止数据导入，另行评审容量变更，不自动扩容。

## 网络、身份与冷启动前提

- 临时 SSH IPv4 来源按用户指示声明为 `0.0.0.0/0`；IPv6 SSH 不放行。使用已声明公钥，
  检查实际 SSH 密码登录配置，并在完成引导后通过同一 IaC 声明收紧为操作来源 CIDR。
- HTTP/HTTPS 80/443 用于 V6 入口。6443、5432、Vault 内部端口及节点指标端口不新增公网规则。
  初次管理经 SSH 到目标节点本机完成；后续 XConnect/私网管理路径需单独核对路由和授权。
- 单节点不为 Flannel 跨节点通信开放额外公网端口。创建前盘点现有私网、XConnect 和 V5 网段，
  确定 Pod/Service CIDR；多节点扩展另行规划。`private_ip: true` 不等于已建立隔离 VPC。
- 系统管理、各业务服务、只读审计身份分开。管理员 kubeconfig 强制 0600，审计不读取该凭据。
  Bootstrap 的 root 仅管理节点；应用实际 UID、Kubernetes RBAC 和 DB 角色分别验证。
- 独立 Vault TLS 由 GitOps 管理的 ESO 从既有公共 Vault KV 读取并同步，不在节点签发证书；
  Vault 初始化/unseal 由外部受控路径完成，恢复材料放在集群外受保护位置。不复制 V5 Raft 或 recovery key。
- Playbooks 已安装 K3s `v1.37.1+k3s1` 和 Flux core；ESO 作为 cluster prerequisite 由 GitOps HelmRelease
  固定在 2.14.0。先完成公共 Vault JWT auth 只读身份，再启用 TLS ExternalSecret 和 Vault HelmRelease。

## 执行入口与已核实缺口

以下为已合入的正式执行版本。调用方固定各 owner SHA；后续修复经新 PR 和版本发布，
不修改已发布 tag，也不临时改工作流绕过门禁。

| Owner / 固定版本 | 已合入能力 | 验证与边界 |
| --- | --- | --- |
| IaC `adf9c140cd2c120361012917cddcde1e58876c6c`，[PR #493](https://github.com/ai-workspace-infra/iac_modules/pull/493) | 节点及独立卷 prevent_destroy；create_only 计划校验；卷 ID、挂载设备及节点归属进入 CMDB；provider console 主机密钥证明；[PR #494](https://github.com/ai-workspace-infra/iac_modules/pull/494) 补充二进制帧解码；[PR #495](https://github.com/ai-workspace-infra/iac_modules/pull/495)、[PR #496](https://github.com/ai-workspace-infra/iac_modules/pull/496)、[PR #497](https://github.com/ai-workspace-infra/iac_modules/pull/497) 补充只读控制台回看、终端渲染、完整管道输出与 V6 规范节点 inventory key | IaC 测试、provider validate 和 CI 通过；实际 plan 只新增节点、卷、firewall，无修改/删除 |
| Playbooks `5c0948ce9f6e451a179952d156705034ce1c5a6b`，[PR #854](https://github.com/ai-workspace-infra/playbooks/pull/854) | 精确 CMDB 动态 inventory；空盘 ext4、UUID 挂载、K3s mount 依赖；固定 K3s/Flux；全图暂停加载；独立审计身份；[PR #862](https://github.com/ai-workspace-infra/playbooks/pull/862)、[PR #863](https://github.com/ai-workspace-infra/playbooks/pull/863) 增加先行 common 与 common-only 阶段 | 角色测试、Linux 空盘测试和 CI 通过；真实节点/挂载/暂停图及实际审计允许/拒绝检查通过 |
| 身份初始化 `f6474939b1156b2eac48292f6a48bc9d03bab935`，[PR #857](https://github.com/ai-workspace-infra/playbooks/pull/857) | 管理员一次性初始化精确 V6 Vault role/policy 与 SSH KV 绑定；同环境原 Key 公钥校验，CAS=0 新建，密钥仅内存传递 | 真实临时密钥与禁止错误 Key 写入测试通过；初始化已完成。不是 CI 管理员 token 兜底 |
| Orchestrator `1b73eb3d07791d38e1af9d6d50964ff72181fac6` / `v6.0.0-bootstrap.4`，[PR #1536](https://github.com/ai-workspace-infra/Platform-Orchestrator/pull/1536) | 指定 Selfhost 入口的独立 V6 四阶段；固定 owner；关联 IaC 回执/校验和；受保护 tag 与 PROD OIDC；终态证据门禁；[PR #1547](https://github.com/ai-workspace-infra/Platform-Orchestrator/pull/1547) 保证 infra/deploy 都运行 common | CI 通过；旧 UAT/V5 路径不用于 V6；拒绝迁移、初始化业务库、destroy、DNS 切换及外部节点 |
| GitOps 已部署 `c74a1a5a7d3a633d4020897fbb765b3e23fb279a` / `v2026.10.29.4`，[PR #658](https://github.com/ai-workspace-infra/gitops/pull/658) | 六独立配置源、唯一根/五业务子 Kustomization、七业务 HelmRelease，初始全部暂停 | 完整固定 tag 构建验证通过；ESO/TLS 前置由本次新增声明引入，需新的稳定 tag |
| Artifacts `a7b791e2d80b203e31b9671885c9f07152f0a2fd`，[PR #246](https://github.com/ai-workspace-infra/artifacts/pull/246) | fullstack chart 0.2.10 的三个独立发布 profile，Caddy 显式跨 namespace 上游 | 发布成功，实际 OCI digest 与三处 V6 pin 一致；不能据此声称业务已部署 |

已修正 V6 设计：root.yaml 进入根资源列表，五个子单元改用各自独立 GitRepository。
已合入的 Playbooks owner 通过 `declarative_paused` 模式加载 source、root、
子 Kustomization、chart source 和 HelmRelease，不生成或 reconcile `platform-root`。
首次 source/root/子 Kustomization/HelmRelease 全部暂停；后续按根声明与单元配置声明
逐层放行。旧 generated 模式只保留既有调用兼容，V6 不选择它。
只解除子 Kustomization 暂停不会自动解除 HelmRelease 暂停；具体步骤和最小依赖见层级文档。

本地其他 owner checkout 存在无关修改，已保留；Playbooks 改动在独立 worktree 中完成。
K3s、Flux、Helm 的固定官方版本已核实存在，fullstack chart 已拉取核对 digest 和独立 values；
各业务 chart/image 的运行、资源预算、网络、Secret 与兼容性仍须逐单元验证。业务目标库名、PostgreSQL 17 及 Accounts/Billing schema
checkpoint 按实际 `migratectl` 固定版本的要求由迁移 owner 创建与验证。

## 进入创建阶段的顺序与放行结果

| 阶段 | 完成条件 | 当前状态 |
| --- | --- | --- |
| 0 声明与候选固定 | 六 GitRepository、唯一根/五子 Kustomization、七 HelmRelease、独立节点/卷及目标/state 审查通过；发布标签包含 V6 路径 | PASS；正式 GitOps tag 与独立 owner SHA 已固定 |
| 1 创建前检查 | 账户、region、plan、image、卷容量/费用、源数据量、预算、受控入口通过；上述 owner 缺口关闭 | 创建所需身份与正式入口已验证；全业务容量、源数据及恢复空间另在放行前验收 |
| 2 云资源 plan | 只新增 V6 节点、独立卷及 firewall；无 V5、DNS、共享 SSH key 变更，无修改/删除/替换既有资源 | PASS；3 create、0 update、0 delete，运行 [40838341949](https://github.com/ai-workspace-infra/Platform-Orchestrator/actions/runs/40838341949)，IaC 子运行 [40838376523](https://github.com/ai-workspace-infra/Platform-Orchestrator/actions/runs/40838376523) |
| 3 IaC 创建 | 使用同一固定声明重新生成、核验并 apply 保存计划，输出 CMDB 与卷身份 | PASS；3 create、0 update、0 delete；IaC 子运行 [40838673674](https://github.com/ai-workspace-infra/Platform-Orchestrator/actions/runs/40838673674)，provider 收敛、节点/卷归属与 CMDB 验证通过 |
| 4 主机/存储/集群 | 先核对完整受信主机指纹，再做空盘、UUID、固定版本与暂停声明验收 | 首次运行 [40838640119](https://github.com/ai-workspace-infra/Platform-Orchestrator/actions/runs/40838640119) 在 SSH 前停止；第二、三次运行仍停在指纹核验；PASS；[40851530314](https://github.com/ai-workspace-infra/Platform-Orchestrator/actions/runs/40851530314) 自动 common、独立盘、K3s/Flux 与审计检查全部通过，最终回执 `PAUSED_BOOTSTRAP_VERIFIED` |
| 5 五单元冷启动 | Vault → PostgreSQL → Observability → Web SaaS → Ingress，逐单元准备依赖并验收；业务独立写者暂停 | NOT_RUN |
| 6 核心数据与恢复验收 | 备份/恢复、`migratectl` 预览及审查后的复制、差异/回归、含业务数据的隔离恢复和观察 | NOT_RUN；数据写入另按任务授权执行 |
| 7 待切换报告 | 列出未完成项、最终追齐及写入权/流量交接方案 | NOT_RUN；V5 不切换、不退役 |

按用户选定的 4 GB 节点核算容量：先测 OS/K3s/Flux/ESO 基线和实际 allocatable，再分配
五单元 requests/limits 与余量。此前 V5 历史 memory requests 约 3,340 MiB，不能直接当成
V6 容量验收结果。按当前规格创建节点与后续放行全部业务分别记录；没有足够容量时停在
对应单元验收，不自动变更用户选定的云规格，也不以创建成功宣称整个业务栈通过。

云费用按节点、独立卷、备份/对象存储、恢复演练容量和双代并行窗口分别核算。
按已选择的 Shared 4 GB / 2 vCPU 重新核实实际 Tokyo 账户报价、税费及 Block Storage 单价；
旧 8 GB 方案的参考价不适用于本轮。只读 plan 已验证账户身份与创建计划；尚不代表全部业务的性能容量或恢复空间验收。

来源：[Akamai 亚太价格](https://www.akamai.com/cloud/pricing/asia-pacific)、
[Block Storage](https://techdocs.akamai.com/cloud-computing/docs/block-storage)、
[卷挂载说明](https://techdocs.akamai.com/cloud-computing/docs/configure-and-mount-a-volume)、
[K3s 要求](https://docs.k3s.io/installation/requirements)。

## 初始离线检查（创建前）

- 从上述 IaC main SHA 导出到临时目录，使用正式 Akamai `generate.py render` 消费 V6
  声明：通过，生成独立节点、firewall 和 100 GB 数据卷模块，包含 Terraform fmt。
- 五个服务目录及 V6 集群目录分别执行 `kubectl kustomize`：6 项通过。该检查不渲染远端
  Helm chart，不能证明 chart values、镜像、Ingress/TLS、数据库连接或实际部署有效。
- 此离线检查阶段未执行 Terraform init/plan/apply、云 API 调用、SSH、格式化/挂载、数据库操作或 workflow dispatch；后续实际执行见阶段表。
  临时生成的 HCL、运行配置和构建输出均在仓库外，不作为运行 CMDB 或执行回执提交。

## 正式冷启动执行边界

Selfhost Orchestrator 的 `prod-v6` 专用路径消费此声明，支持 `plan`、`infra`、
`deploy`。`infra` 在 IaC 完成后自动执行 `vhosts/common`，仅检查主机、不初始化数据盘或安装 K3s；
`deploy` 在同一 common 门禁通过后才进入独立盘和 K3s/Flux 暂停式引导；全部 6 个配置源、
6 个 Flux Kustomization、7 个 HelmRelease 仍为 suspend=true。它不执行 migratectl、
SQL schema 变更、业务恢复、DNS、源写者停用或写入权交接。

初始配置 tag 为 `v2026.10.29.8`，必须发布于包含本声明及 Vault TLS identity 门禁的合入提交，才可调度。
固定安装版本：K3s `v1.37.1+k3s1`、Flux `2.9.6`、Helm `v3.22.1`。
独立卷目标挂载 `/data`，local-path provisioner 目标使用 `/data/k3s/storage`；K3s systemd
依赖该挂载，不允许在丢失挂载时向系统盘的同名目录写入。

IaC 角色 `github-actions-platform-ops-toolkit-prod-k3s-v6-iac` 仅能读取 provider 与 state 凭据，Bootstrap 角色
`github-actions-platform-ops-toolkit-prod-k3s-v6-bootstrap` 仅读取本集群 SSH 绑定与 provider 主机密钥核验凭据。
两者仅接受受保护 `v6.*` tag 下相应固定 workflow 的 PROD OIDC 身份。系统管理员首次
配置专用角色和 SSH KV 绑定；不把管理员 Vault token 放入 CI 或业务。
实际云端 plan/apply 已有回执；集群身份、挂载 UUID 和暂停声明回执已在引导运行及独立实机读取中验证；运行事实只保存在受控回执，不回填为部署输入。

## 保留节点后的修复验证

首次失败未执行 SSH、格式化、K3s 安装、业务发布或数据迁移。节点和独立卷按保护策略
保留。IaC 控制台解码修复经 PR 合入，控制面以 [PR #1543](https://github.com/ai-workspace-infra/Platform-Orchestrator/pull/1543)
固定新 owner，再发布新的不可变 tag；原 tag 未移动。
第二次只读 [plan 40840089376](https://github.com/ai-workspace-infra/Platform-Orchestrator/actions/runs/40840089376)
及 [IaC 子运行 40840131815](https://github.com/ai-workspace-infra/Platform-Orchestrator/actions/runs/40840131815)
验证为 **0 create、0 update、0 delete**，才继续同一节点的引导。完整指纹、精确 CMDB、
空盘和全部暂停等门禁不因重试而放宽。

## IaC 后自动 common 门禁

[V6 第三阶段](https://github.com/ai-workspace-infra/Platform-Orchestrator/pull/1547) 必须依赖成功的 IaC 回执，校验 GitOps/owner SHA、CMDB 校验和、实例归属及受信 SSH 主机密钥后，调用 Playbooks 的 `vhosts/common/tasks/node_bootstrap.yml`。

| 操作 | IaC 之后自动执行 | 继续条件 |
| --- | --- | --- |
| `plan` | 不连接主机 | 只产生计划回执 |
| `infra` | common-only；规范 hostname、cloud-init 保留、hosts 解析、独立只读审计账户 | 必须获得 `COMMON_NODE_VERIFIED`；common 失败则整体失败 |
| `deploy` | 同一 common 门禁，再初始化核实为空的新卷、安装 K3s/Flux 并加载暂停声明 | 必须获得 `PAUSED_BOOTSTRAP_VERIFIED`，不能仅看 workflow 绿色 |

CMDB/inventory 主键、`host.name` 和 K3s node name 必须一致为 `prod-k3s-v6`；业务域名保留为别名，不能代替节点身份。common 在改 hostname 前检查已有 K3s 节点、PV hostname affinity 和 Flux 对象；发现不同节点名、PV 绑定冲突或已激活 Flux 时停止，不自动改绑或重命名已有集群。

本轮在尚未安装 K3s、尚无 PV 时，已通过既有操作员受信 SSH 连接调用审查后的 common hostname 任务，将 runtime/static hostname、cloud-init 和 hosts 同步为 `prod-k3s-v6`。随后按固定 Playbooks SHA 执行 common-only：22 项成功、0 项失败，回执 `COMMON_NODE_VERIFIED`；实际审计身份允许读取状态、拒绝系统配置写入。此手动验证与自动流水线结果分开记录。

本次 [IaC 40851581630](https://github.com/ai-workspace-infra/Platform-Orchestrator/actions/runs/40851581630) 回执为 `applied_verified`，**0 create、0 update、0 delete**，云实例/独立卷归属与前次一致；产出的 inventory 主键已核实为 `prod-k3s-v6`。未重建节点或卷。

## 暂停式引导验收结果（2026-10-29）

[Selfhost 40851530314](https://github.com/ai-workspace-infra/Platform-Orchestrator/actions/runs/40851530314) 的四个 V6 阶段全部成功。下载并检查本次 `prod-k3s-v6-bootstrap-40851530314-1` artifact 中的 `v6-bootstrap-receipt.json`，同时经既有受信 SSH 独立读取节点、挂载、Flux Deployment 和全部发布对象。

| 验收项 | 实际结果 |
| --- | --- |
| IaC 归属及无漂移 | `applied_verified`；0 create、0 update、0 delete；保留同一受保护实例和卷 |
| 自动 common | `COMMON_NODE_VERIFIED`；在存储/K3s 前检查；CMDB、OS/K3s 节点名均为 `prod-k3s-v6` |
| 规范 hostname | runtime、`/etc/hostname`、cloud-init 保留、hosts 解析一致 |
| 新独立盘 | `/data` 为 ext4，回执 UUID 与实际 `findmnt` 一致；未复用 V5 卷 |
| K3s | `prod-k3s-v6` Ready，`v1.37.1+k3s1`；节点与集群 UID 已记录在运行回执 |
| Flux 控制器 | source、kustomize、helm、notification 四个 Deployment 均 1/1 Ready |
| 声明加载 | 已部署图：6 GitRepository、6 Flux Kustomization、7 HelmRelease，实际全部 `suspend: true`；新增 ESO/TLS 声明尚未加载 |
| 独立审计身份 | `AUDIT_ALLOW_DENY_VERIFIED`；实际身份可读系统/节点/namespace 状态，拒绝管理员 kubeconfig、系统/数据写入、Secret、node proxy 和 namespace 写入 dry-run |
| 业务与数据边界 | 五个单元尚未放行；未执行 SQL schema、数据迁移、DNS 或写者切换；V5 保留 |

该结果仅验收独立节点及暂停式控制面。ESO 尚未安装，新增 GitOps ESO/TLS 声明尚未加载；尚未验收各 chart 的实际工作负载、Secret 同步、应用 UID/DB 身份、业务容量、备份恢复或核心数据；不得将其标记为全业务生产上线完成。
