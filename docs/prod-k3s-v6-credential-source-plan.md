# PROD-K3S-V6 凭据来源核对与确认方案

日期：2026-10-30。状态：用户已确认下述无批次版本路径及人工初始化方案；仅从仓库声明与文档核对来源，没有读取秘密值，也没有验证目标 Vault 记录当前存在。

## 已找到的 V5 来源

V5 K3s 的业务 SecretStore 指向 **V5 集群内 Raft Vault**：
`https://vault-raft.platform-vault.svc.cluster.local:8200`，mount 为 `kv`，
auth mount 为 `kubernetes-web-saas-k3s-v5`。下面的 V5 业务记录不能假定也存在于公共 `https://vault.svc.plus`。

| 用途 | V5 声明的 KV 逻辑路径 | 字段 | 依据 |
|---|---|---|---|
| PostgreSQL 与业务混合记录 | `kv/prod/services/web-saas-k3s-v5/database` | `password`、`POSTGRES_PASSWORD`、`database_url`、`INTERNAL_SERVICE_TOKEN`、`ROOT_BOOTSTRAP_PASSWORD`、`ROOT_BOOTSTRAP_EMAIL`、`observability_identity_token` | `services/distributed-web-saas-fullstack/prod/external-secret.yaml` |
| JWT | `kv/prod/services/web-saas-k3s-v5/jwt` | `secret` | 同上 |
| V5 TLS | `kv/prod/services/web-saas-k3s-v5/tls` | `tls_fullchain_pem`、`tls_key_pem` | 同上 |
| V5 品牌 TLS | `kv/prod/services/web-saas-k3s-v5/brand-tls` | `tls_fullchain_pem_b64`、`tls_key_pem_b64` | 同上 |
| Content | 同一 `database` 记录 | 仅映射 `INTERNAL_SERVICE_TOKEN` 到 `content-runtime` | 同上 |

V5 Accounts、Billing 都引用 `web-saas-secrets`，所以旧结构存在共享记录；这不能证明 V6 的独立 `accounts-runtime`、`billing-runtime` 或各 DB runtime 记录已存在。

旧 Selfhost/Compose 编排另有一套入口（不是上述 V5 K3s SecretStore 的同一证据）：

| 来源 | 字段/用途 | 依据 |
|---|---|---|
| `kv/prod/databases` | `postgres_root_password`、`account_pg_password` | Orchestrator `selfhost-stage-deploy.yml` |
| `kv/WEB_SAAS` | `AUTH_TOKEN_PUBLIC_TOKEN`、`AUTH_TOKEN_REFRESH_SECRET`、`AUTH_TOKEN_ACCESS_SECRET`、`INTERNAL_SERVICE_TOKEN` 与可选 OAuth | 同上 |
| `kv/prod/billing-service` | Stripe 生产/Sandbox 字段，由旧适配器选择；不证明 V5 K3s 已读取 | 旧 `platform-ops_deploy_base_load-optional-web-saas.sh` |
| `kv/CICD` | GHCR 读取凭据、旧管理员引导字段 | `selfhost-stage-deploy.yml` |
| `kv/CICD/domains/svc.plus` | `tls_fullchain_pem_b64`、`tls_key_pem_b64` | V6 已有 TLS ExternalSecret 声明，从公共 Vault 读取 |

KV v2 API 路径在 mount 后增加 `data/`，例如 `kv/data/prod/services/...`。ESO `remoteRef.key` 不带 `kv/data/`。

## 已确认的服务 KV 路径

取消此前建议的 `kv/prod/services/prod-k3s-v6` 业务前缀。服务 KV 路径不带部署批次版本，采用下表中的完整路径。
OS 公钥仍为 `kv/prod/security/{root,operator,auditor}`；Kubernetes 私有身份仍为
`kv/prod/prod-k3s-v6/{root,operator,auditor}`，由新 master 生成并写入，CA 私钥留在 master。

| 身份或 Kubernetes Secret | 已确认的完整 KV 路径 | 处理 |
|---|---|---|
| PostgreSQL `admin`；`postgresql-prod/postgresql-superuser` | `kv/prod/database/postgresql/admin` | 初始化、DDL、恢复及必要管理；不注入业务工作负载 |
| PostgreSQL `operator` | `kv/prod/database/postgresql/operator` | 日常数据库运行维护；按审查范围读写，不默认超级用户 |
| PostgreSQL `auditor` | `kv/prod/database/postgresql/auditor` | 独立只读，用于审计及授权迁移源读取；无目标写入或提权 |
| Accounts；`web-saas-prod/accounts-runtime`、`accounts-db-runtime` | `kv/prod/Accounts-service` | 由不同 Secret 显式映射所需字段；数据库连接指向 V6，应用数据库身份仍限定 DML |
| Billing；`web-saas-prod/billing-runtime`、`billing-db-runtime` | `kv/prod/billing-service` | 显式映射运行与数据库字段；真实支付和 webhook 的启用不由路径确认自动放行 |
| Content；`web-saas-prod/content-runtime` | `kv/prod/Accounts-service` | 与 Accounts 共用 KV 路径，仅映射 Content 必需字段 |
| `vault-prod/vault-server-tls` | 公共 Vault `kv/CICD/domains/svc.plus` | 只读复用已有 TLS，验证有效期、链、key 配对与实际 SAN |
| `ingress-prod/{console,accounts,billing}-tls` | 同上公共域名 TLS 来源 | ESO 分别生成 Secret；只有 V6 专属域名允许参与 DNS 阶段 |
| `xworktech.com` 及其证书覆盖的品牌域名 TLS | 公共 Vault `kv/CICD/domains/xworktech.com` | 按实际路由域名/SAN 选取，单独映射 TLS Secret；源路径确认不增加公网路由或 DNS 变更 |

不能将 V5 的 `database_url` 原样交付给 V6，以免新工作负载写入 V5。
Vault KV 路径区分大小写；`Accounts-service` 保留用户指定的大写 A。表中的服务记录不增加批次目录，也不自动衍生 `/runtime`、`/database` 子记录；字段映射和记录存在性仍待实施验收。
Content 与 Accounts 共用 Vault KV 记录时，Vault policy 的读取授权粒度是整条记录；ESO 只映射部分字段不能被描述为 Vault 字段级隔离。
稳定路径不等于自动复用已有密码或连接目标。已有记录不得被冷启动覆盖；V5/V6 并行期间须核对实际数据库绑定和现有消费者，冲突时停止，不能将 V5 连接原地改成 V6。
共享域名证书不能直接假定覆盖 `*.svc.cluster.local`；内部 Vault 客户端必须使用受证书覆盖的验证名称或专用内部 SAN 证书，禁止关闭证书验证。

## Vault 初始化/unseal：外部安全托管、迁移过程手动初始化

V5 `services/platform-vault/prod/README.md` 明确采用人工初始化/恢复及 unseal，未声明 auto-unseal。
白皮书配套 runbook `knowledge/docs/reference/platform-ops-toolkit/04-security-vault-and-iam/manual-unseal.md`
明确禁止 IaC/GitHub Actions 接收 root token 或 unseal shares；`vault_operator_material` 仅检查受控节点上材料文件的权限与非空状态。

因此不把任何现有 KV 路径描述成已存在的 V6 unseal 材料库，也不把旧 Raft 的 shares 当作新 Vault 初始化材料。
用户已确认：Vault 初始化及 unseal 材料由外部安全托管；迁移过程中通过受控管理通道手动初始化，并手动完成所需 unseal。材料不写入以上服务 KV、Git、workflow inputs、artifact 或日志；本次不引入自动初始化或 Transit/KMS auto-unseal。
操作前先检查 `initialized`/`sealed`：仅对未初始化的新目标执行初始化；已初始化的目标不得重复 init。新目标使用自己的初始化材料，恢复旧 Raft 数据时采用另行审查的恢复与材料流程。
在这一门禁完成前，流水线应明确记录 `Vault sealed/uninitialized` 并停止后续服务验收，不能只等待后报告成功。

## 执行边界

当前 GitOps 活动状态清理只是候选变更。候选发布标签计划为 `v2026.10.30.2`，必须合并后再创建，不能移动 `v2026.10.30.1`。
公共 Vault 专用 JWT 身份、TLS 同步和新目标 DB/schema 初始化各自验收；核心数据迁移与写入方切换另行评审。
canonical `vault/observability/console/accounts/billing/postgresql.svc.plus` 不在 DNS 写入允许列表。
