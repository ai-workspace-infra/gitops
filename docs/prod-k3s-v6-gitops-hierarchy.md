# PROD-K3S-V6 专属 GitOps 层级与独立发布

本方案只描述 V6。V5 的对象、版本和运行状态不参与本次调谐。
所有声明继续放在同一个 GitOps 仓库，但各发布单元独立固定配置版本和 chart/镜像版本。

## 1. 层级及职责

```mermaid
flowchart TD
  Repo[同一个 GitOps 仓库] --> Bootstrap[GitRepository: config-prod]
  Bootstrap --> Root[Kustomization: prod-k3s-v6]
  Root --> NS[5 个服务 namespace + external-secrets]
  Root --> ESO[Kustomization: external-secrets]
  ESO --> EHR[HelmRelease: external-secrets 2.14.0]
  Root --> ID[Kustomization: vault-tls-identity]
  ID --> SA[ServiceAccount + scoped TokenRequest RBAC]
  ID -. dependsOn .-> ESO
  Root --> TLS[Kustomization: vault-tls-bootstrap]
  TLS -. dependsOn .-> ID
  TLS --> Ext[SecretStore + ExternalSecret]
  Ext --> TSecret[Secret: vault-prod/vault-server-tls]
  TLS -. dependsOn .-> ESO
  Root --> V[Vault 单元 GitRepository + 子 Kustomization]
  Root --> P[PostgreSQL 单元 GitRepository + 子 Kustomization]
  Root --> I[Ingress 单元 GitRepository + 子 Kustomization]
  Root --> O[Observability 单元 GitRepository + 子 Kustomization]
  Root --> W[Web SaaS 单元 GitRepository + 子 Kustomization]
  V -. dependsOn .-> TLS
  V --> VH[HelmRepository → HelmRelease: vault]
  P --> PH[同包 OCIRepository → HelmRelease: postgresql]
  I --> IH[同包 OCIRepository → HelmRelease: caddy-ingress]
  O --> OH[2 个 OCIRepository + HelmRepository → 3 个 HelmRelease]
  W --> WH[OCIRepository → HelmRelease: web-saas-prod]
```

根层管理 namespace、单元配置源、集群控制器前置与子 Kustomization 定义，不直接合并部署五套业务 chart。
服务资源由对应 HelmRelease 的 Helm controller 管理；不要让 root 或其他单元重复管理其 Deployment/Service/PVC。

| 层 | V6 对象 | 管理内容 | 更新边界 |
| --- | --- | --- | --- |
| 引导配置源 | `flux-system/config-prod` | V6 根目录的不可变配置 tag/commit | 仅 V6 管理图、单元 source pin 或放行状态变化时更新 |
| 根 Kustomization | `flux-system/prod-k3s-v6` | `environments/clusters/prod-k3s-v6` | 只应用管理图；`wait: false` 不被暂停的子 Kustomization 阻塞，不由 bootstrap 另外生成 `platform-root` |
| 单元配置源 | 5 个 `flux-system/<unit>-config` | 同仓库中该单元配置的独立 tag/commit | 只推进被选中单元；其他四个 pin 保留 |
| 子 Kustomization | 5 个 `flux-system/<unit>` | `services/prod-k3s-v6/<unit>` | 独立 sourceRef、path、暂停状态、健康等待及最小依赖 |
| 控制器前置 | `flux-system/external-secrets` | `services/prod-k3s-v6/cluster-prerequisites/external-secrets` | ESO 2.14.0、CRD 与控制器；不属于五个业务发布单元 |
| Vault TLS 身份 Kustomization | `flux-system/vault-tls-identity` | `services/prod-k3s-v6/vault-prod/tls-identity` | 仅创建读取身份和范围限定的 TokenRequest 授权，供 Vault 身份验收 |
| Vault TLS 引导 Kustomization | `flux-system/vault-tls-bootstrap` | `services/prod-k3s-v6/vault-prod/tls-bootstrap` | 读取现有公共 Vault 域名证书，并在 Vault chart 前生成 TLS Secret |
| Chart 源 | 各服务 namespace 的 HelmRepository/OCIRepository | chart 来源及固定版本/digest | chart 源与配置 GitRepository 是两个不同层次 |
| HelmRelease | 各服务 namespace | chart values、chartRef、运行版本及 release 生命周期 | 可以独立固定版本；受 UI/API/DB 升级规则约束 |

V6 首次图为 **6 个 GitRepository、1 个根 + 5 个业务单元 + 3 个前置 Flux Kustomization、8 个 HelmRelease**。
其中七个 HelmRelease 属于五个业务单元，新增的 ESO HelmRelease 是集群控制器前置。
观测单元含三个独立发布的 chart，因此“五单元”不强制合并为“五个 HelmRelease”。

## 2. 五个发布单元的精确对应

| 发布单元 / namespace / 子 Kustomization | 独立 GitRepository（flux-system） | HelmRelease（服务 namespace） | 管理范围 |
| --- | --- | --- | --- |
| `vault-prod` | `vault-prod-config` | `vault` | V6 Vault、Raft PVC、Vault 自身身份配置；TLS/恢复材料按外部可信引导路径提供 |
| `postgresql-prod` | `postgresql-prod-config` | `postgresql` | PostgreSQL、ClusterIP Service、PVC、数据库运行配置；应用 schema/数据迁移由 owner 工具执行 |
| `ingress-prod` | `ingress-prod-config` | `caddy-ingress` | Caddy 反向代理、TLS 引用及 V6 路由；与 DB/业务使用同一个 chart 包，TLS Secret 在入口 namespace |
| `observability-prod` | `observability-prod-config` | `observability`、`observability-agent`、`datakit` | 监控存储/查询/Dashboard/探测、采集器；不承载业务账单状态 |
| `web-saas-prod` | `web-saas-prod-config` | `web-saas-prod`（releaseName `web-saas`） | UI/API Deployment、Service、应用配置；内嵌 PostgreSQL 和 Caddy 关闭 |

Web SaaS 当前采用一个已有 fullstack chart，单元级发布会调谐该 HelmRelease；UI/API 子服务
不是额外的 Flux 发布单元。将来要分别发布 UI/API chart，需要 producer/consumer 契约变更，
不能在本轮规划中声称已经具备每个 Deployment 的独立 HelmRelease。

PostgreSQL、`caddy-ingress`、`web-saas-prod` 三个 HelmRelease 统一引用同一个
`distributed-web-saas-fullstack` OCI chart 包，在各自 namespace 保留独立 source/digest。
通过 PostgreSQL-only、Caddy-only、application-only 三套 values 控制资源归属；Caddy 使用
显式跨 namespace 后端，不重复启用业务 Pod。独立 Caddy 契约仍待 producer 发布新 digest，
旧暂停 pin 不构成可部署证据。完整 values 和 KV 路径关联见创建准备文档。

## 3. 每种版本与更新方式

- **根配置版本**：`config-prod.spec.ref`。保存 V6 管理图与各单元的选择。
- **单元配置版本**：`<unit>-config.spec.ref`。固定该单元的 values、chartRef、暂停状态等；
  五个配置源可处于不同不可变 tag，不要求同时升级。
- **Chart 版本**：HelmRepository 模式使用 HelmRelease 的精确 `chart.spec.version`；
  OCI 模式固定 OCIRepository digest/精确 tag，HelmRelease 使用 `chartRef`。
- **镜像版本**：按 chart 契约固定 image digest 或已审查的不可变 tag；chart 版本不自动证明镜像已固定。

例如只修复 Web SaaS API：

1. 仅修改 `services/prod-k3s-v6/web-saas-prod` 的相应镜像/chart 配置，审查并发布包含该修改的稳定 tag。
2. 在新的根配置提交中只推进 `web-saas-prod-config` 的 tag，再审查发布根配置版本。
3. 由授权入口将 V6 根 source 指向这个新管理图版本。其他四个单元配置 tag 保持原值，
   各自 chart/镜像版本不变化；根 source 变更不等于全部单元升级。
4. 已放行的 Web SaaS 子 Kustomization 和 HelmRelease 各自调谐。验收接口、回归和错误率。

独立更新是“独立选择版本和调谐范围”，不等于无依赖、无审查或允许修改业务持久状态。
SQL schema/数据库/业务持久状态版本转换必须去下一代新集群；这类 source/HR pin 不能在 V6
原地推进。独立非业务/非账单监控服务可按已明确的例外原地更新。

## 4. 引导、暂停与放行

### 首次引导

首次候选的六个 GitRepository pin 指向同一个包含完整 V6 目录的已审查 tag/commit，
便于核对完整初始图。初始正式版本为 `v2026.10.29.4`，解析到已合入的
`c74a1a5a7d3a633d4020897fbb765b3e23fb279a`；六个初始 pin 已统一固定并构建验证。
后续各单元可独立推进版本引用，不重新执行首次全图引导。

Playbooks 的 `declarative_paused` 模式从控制端固定 GitOps checkout 构建 root 与所有前置/业务路径，
加载 source、root、子 Kustomization、chart 源及 HelmRelease；不会另外生成/调谐 `platform-root`。
六个 GitRepository、九个 Flux Kustomization 和八个 HelmRelease 均要求 `suspend: true`。
ExternalSecret 本身没有 `suspend` 字段；它由暂停的 `vault-tls-bootstrap` Kustomization 隔离，不会在放行前调谐。
所有对象已加载不等于 release 已安装，更不等于业务健康或数据验收通过。

引导器验证源码 commit、稳定 tag、对象名称、sourceRef/path、一单元一配置源以及完整暂停状态；
拒绝覆盖已有 active Flux 图。保留旧 generated 模式仅为既有 caller 兼容，V6 明确选 paused 模式。

### 放行顺序

1. K3s 与 Flux core 由受审查的 Playbooks bootstrap 安装。V6 已验收 K3s `v1.37.1+k3s1` Ready，
   Flux source/kustomize/helm/notification controller 均 `1/1 Ready`；不重复安装。
2. 节点、独立数据卷 `/data`、PV 供给路径、hostname/身份及 Flux 暂停式声明加载完成。
   在权威声明中启用根 GitRepository 和根 Kustomization，仅使管理图开始调谐；root `wait: false`
   只确认管理对象成功应用，五个业务单元和三个前置各自报告状态并仍保持暂停。
3. 单独放行 `external-secrets` Kustomization 与 HelmRelease，等待 ESO controller 和 CRD Ready。
   ESO 固定 Helm chart `2.14.0`；V6 K3s `1.37` 在该版本上游支持矩阵内。禁用 chart 默认的全局
   `serviceaccounts/token` 创建权限，只授予 ESO 对 `vault-prod/vault-tls-reader` 的命名空间级、
   resourceName 限定 TokenRequest 权限。
4. 放行 `vault-tls-identity`，创建专用 ServiceAccount 与限定 TokenRequest 权限；保持 `vault-tls-bootstrap` 暂停。
   由共享公共 Vault 的 owner 配置独立 JWT auth mount/role：只接受
   V6 专用 service account、专用 audience，并仅能读取 `kv/data/CICD/domains/svc.plus`。
   Vault JWT verifier 必须信任 V6 K3s service-account 签名公钥与 issuer；不开放公网 K3s API 供
   Vault TokenReview，也不存静态 Vault token。使用真实 ServiceAccount 验证指定记录可读、相邻记录被拒绝、
   错误 audience 和错误 ServiceAccount 登录被拒绝，记录脱敏证据。此角色与 V6 Vault 启动后的内部 Vault auth 完全分开。
   Flux dependsOn 仅验证身份对象已应用；授权验收是独立的放行门禁，不由 dependsOn 自动证明。
5. 放行 `vault-tls-bootstrap` 后等待其 ExternalSecret `Ready=True`，检查目标 Secret 名称/类型、证书
   与私钥匹配、有效期及 SAN `vault-k3s-v6.svc.plus`；敏感值不得写入日志。ExternalSecret 每 5 分钟读取公共 Vault 中
   `tls_fullchain_pem_b64` / `tls_key_pem_b64`，解码后生成 `vault-prod/vault-server-tls`。
   公网 Vault 地址仍是 `https://vault.svc.plus`；不改 DNS、不本机签发证书。
6. 只有 Secret 同步与证书校验通过后，才放行 Vault 子 Kustomization/HelmRelease；之后由 Vault owner
   独立执行初始化、unseal、恢复材料保管及 V6 内部 auth 准备。不可让尚未初始化的 V6 Vault
   为自身 TLS 或首次凭据提供来源。
7. Vault Ready 并且内部 ESO/SecretStore 可用后，按 PostgreSQL、Observability 的顺序各自放行；
   Web SaaS 等 Vault 与 PostgreSQL。数据迁移前目标业务写者/后台任务保持暂停。
8. Ingress 按用户要求最后放行，并依赖 Vault、Observability、Web SaaS。先用 V6 专属域名做受控
   路由和 TLS 验证；公共 DNS 变更保持为单独、后续评审步骤。
9. 所有暂停变更必须在权威固定版本声明中：根配置管理 source/Kustomization 放行，单元 tag 管
   HelmRelease 状态。不能只现场 `flux resume` 后让父层旧声明再次暂停。

不要在 HelmRelease 暂停时等待子 Kustomization 健康成功再决定是否放行 HelmRelease；
`wait: true` 会等待其 release 健康，需按同一单元的放行步骤配套推进后再观察 Ready。
逐层解除暂停不授予数据库迁移、真实扣退款、DNS 或写入权切换权限。

## 5. 依赖、健康及数据保护

`dependsOn` 编码会导致 reconcile 失败或不可用的硬前置；人工/数据验收仍是额外门禁：

- `external-secrets` Kustomization 安装 ESO chart/CRD；`vault-tls-identity` dependsOn ESO；`vault-tls-bootstrap` dependsOn 两者。
- Vault 子 Kustomization dependsOn `vault-tls-bootstrap`；TLS ExternalSecret Ready 是 Vault HelmRelease 的硬门禁。
- PostgreSQL 和 Observability 分别依赖 Vault；首次部署按 PostgreSQL、Observability 顺序放行。
- Web SaaS 依赖 Vault 与 PostgreSQL；它不依赖独立监控或 Ingress。
- Ingress 依赖 Vault、Observability 与 Web SaaS，依照部署安排最后放行；公网 DNS 仍单独评审。
- 依赖状态 Ready 不代替证书 SAN/有效期、应用链路、PVC/备份恢复和业务验收。

根和包含数据的子 Kustomization 使用 `prune: false`，减少移除定义时级联删除的风险；
这不禁止 Helm 升级自身删除资源，也不代替 PVC/StorageClass `Retain`、云卷删除保护、
备份与恢复演练。任何 release uninstall、namespace/PVC 删除和旧代退役单独评审授权。

## 6. 文件布局与当前交付边界

```text
environments/clusters/prod-k3s-v6/
  kustomization.yaml              # 根目录资源列表，也包含 root.yaml
  source.yaml                     # 引导 GitRepository
  root.yaml                       # 唯一 V6 根 Flux Kustomization
  unit-sources.yaml               # 五个独立单元配置源
  external-secrets-kustomization.yaml
  vault-tls-identity-kustomization.yaml
  vault-tls-bootstrap-kustomization.yaml
  namespaces.yaml
  platform-*-kustomization.yaml    # 四个平台子单元
  web-saas-kustomization.yaml
services/prod-k3s-v6/cluster-prerequisites/external-secrets/ # ESO chart/controller
services/prod-k3s-v6/vault-prod/tls-identity/ # 仅 SA 和 TokenRequest RBAC
services/prod-k3s-v6/vault-prod/tls-bootstrap/ # 公共 Vault → ESO → vault-server-tls
services/prod-k3s-v6/<unit>/       # 五个业务单元自己的 Kustomize、chart source、HelmRelease
```

V6 已安装并验收 K3s `v1.37.1+k3s1` 及四个 Flux controller；ESO 与 TLS bootstrap 声明是本次新增，
仍需固定新 GitOps tag、由受审查入口加载为暂停状态，再按上述依赖逐级放行。详见[创建准备与实机证据](prod-k3s-v6-node-cluster-preflight.md)。
