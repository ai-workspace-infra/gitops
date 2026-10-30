# PROD-K3S-V6 凭据来源核对与待确认方案

日期：2026-10-30。状态：待用户审查；仅从固定仓库声明与文档核对路径和字段，没有读取秘密值，也没有验证 Vault 记录当前存在。

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

## V6 建议映射：待确认后实施

`kv/prod/services/prod-k3s-v6` 是建议的新批次业务前缀，尚未创建。
OS 公钥仍为 `kv/prod/security/{root,operator,auditor}`；Kubernetes 私有身份仍为
`kv/prod/prod-k3s-v6/{root,operator,auditor}`，由新 master 生成并写入，CA 私钥留在 master。

| V6 Kubernetes Secret | 建议 KV 后缀/来源 | 处理 |
|---|---|---|
| `postgresql-prod/postgresql-superuser` | `postgresql/admin` | 新目标独立密码，仅数据库初始化/管理使用 |
| `web-saas-prod/accounts-db-runtime` | `accounts/database` | 新目标 `accounts_runtime`，只授业务所需 DML；DSN 指向 V6 |
| `web-saas-prod/billing-db-runtime` | `billing/database` | 新目标 `billing_runtime`，不复用 Accounts 或超级用户 |
| `web-saas-prod/accounts-runtime` | `accounts/runtime` | 分离认证/引导与业务令牌，逐字段确认 V5 来源与初始化需要 |
| `web-saas-prod/billing-runtime` | `billing/runtime` | 冷启动默认不接真实扣款与 webhook；生产账单接入另行确认 |
| `web-saas-prod/content-runtime` | `content/runtime` | 仅服务必需的内部令牌；共享令牌是否复用需明确消费者 |
| `vault-prod/vault-server-tls` | 公共 Vault `kv/CICD/domains/svc.plus` | 只读复用已有 TLS，验证有效期、链、key 配对与实际 SAN |
| `ingress-prod/{console,accounts,billing}-tls` | 同上公共域名 TLS 来源 | ESO 分别生成 Secret；只有 V6 专属域名允许参与 DNS 阶段 |

不能将 V5 的 `database_url` 原样交付给 V6，以免新工作负载写入 V5。
共享域名证书不能直接假定覆盖 `*.svc.cluster.local`；内部 Vault 客户端必须使用受证书覆盖的验证名称或专用内部 SAN 证书，禁止关闭证书验证。

## Vault 初始化材料：未找到可直接复用的 KV 约定

V5 `services/platform-vault/prod/README.md` 明确采用人工初始化/恢复及 unseal，未声明 auto-unseal。
白皮书配套 runbook `knowledge/docs/reference/platform-ops-toolkit/04-security-vault-and-iam/manual-unseal.md`
明确禁止 IaC/GitHub Actions 接收 root token 或 unseal shares；`vault_operator_material` 仅检查受控节点上材料文件的权限与非空状态。

因此不把任何现有 KV 路径描述成已存在的 V6 unseal 材料库，也不把旧 Raft 的 shares 当作新 Vault 初始化材料。
本次需确认：新 V6 Vault 独立初始化后的材料托管方案，以及人工 unseal 门禁或另行审查的 Transit/KMS auto-unseal 方案。
在这一门禁完成前，流水线应明确记录 `Vault sealed/uninitialized` 并停止后续服务验收，不能只等待后报告成功。

## 执行边界

当前 GitOps 活动状态清理只是候选变更。候选发布标签计划为 `v2026.10.30.2`，必须合并后再创建，不能移动 `v2026.10.30.1`。
公共 Vault 专用 JWT 身份、TLS 同步和新目标 DB/schema 初始化各自验收；核心数据迁移与写入方切换另行评审。
canonical `vault/observability/console/accounts/billing/postgresql.svc.plus` 不在 DNS 写入允许列表。
