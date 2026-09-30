# Shared IAM 单机 GitOps

部署入口是 Toolkit `zitadel-server.yml` → Playbooks
`deploy_iam_domain.yml` → `deploy_zitadel_docker.yaml`（`doco-cd` 模式）。
Playbooks 准备 PostgreSQL、Caddy 和 Vault 读取的主机机密；Doco-CD 用
`target: zitadel` 选择根目录 `.doco-cd.zitadel.yaml`，不读取 Web SaaS 默认配置。
部署引用为本次审核的 GitOps commit SHA。升级通过新 GitOps PR 修改
`.env.shared` 的镜像 digest，再显式重跑服务部署；不跟随浮动 `main` 自动升级。

宿主机固定接口契约为 `/etc/xcontrol/zitadel/{config.yaml,masterkey,login.env}`
与 `/opt/zitadel` 持久 PAT 目录。配置和密钥权限为 root/0600，不进入 Git、日志或制品。
容器仅监听 localhost 19080/19081，公网入口由 Caddy 提供。
PostgreSQL 由现有 IAM prerequisite 管理，数据与 PAT 不因升级而删除。

验收必须核对 Compose 镜像 digest、API/Login health 和公开 OIDC issuer/JWKS，
不能仅凭 Doco-CD 自身 healthy 报告成功。部署不包含数据迁移或 DNS 修改。
