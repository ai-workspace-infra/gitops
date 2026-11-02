# Accounts 独立迁移服务

业务 Accounts 与迁移 listener 分开部署。`migratectl transfer-api` 访问 Accounts 公共域名下的迁移专用路由，由 Caddy 转发到 listener；普通业务请求仍进入 Accounts。listener 复用 Accounts 的服务认证，独立连接数据库并保存加密分片、预览和回执。

## 目标数据库部署选择

| Flux source path | 常驻 Pod | 数据库用途 |
| --- | --- | --- |
| `services/accounts-migration/target` | listener + candidate | 当前已部署模式，独立 PostgreSQL 用于隔离验证 |
| `services/accounts-migration/target-direct` | listener | 直接连接 V6 已有业务 PostgreSQL，候选数据库不在该资源图内 |

两个入口共享 `target/listener`，无需复制 listener 实现。可选候选库单独位于 `target/candidate`。两种模式都需要 `migration-stage` PVC、TLS Secret 和专用数据库身份。`source_ip`、`destination_ip` 的值由运行时环境交付，GitOps 仅引用 Secret。

**声明入口存在不代表已完成直接写业务库交付。** 当前 Flux 仍使用原 `target` 路径；`operations/accounts-migration/target.yaml` 和 Playbooks bootstrap 仍面向候选库，不可直接拿它们初始化、轮换或授权现有业务 PostgreSQL。

## 切换到业务库的顺序

1. 保留现有 `migrate.sh`，核验业务库实际 schema、数据、目标身份、备份恢复证据及冲突；不得清库或覆盖目标独有事实。
2. 由 Playbooks 为同一个业务库交付独立的迁移数据库身份和 listener Secret；连接串只存在 Vault/Secret。源端仍使用只读身份，不修改 V5 数据或 schema。
3. 为 listener 放行到 PostgreSQL 的精确 NetworkPolicy，确认查询可见性、目标表权限以及源端拒绝写入的权限证据。
4. 更新 listener 的运行时连接并重新预览。目标物理数据库身份已经改变，旧候选库的 plan 和备份回执不可重用为新目标的写入授权。
5. 在预览、账单差异、冲突处理及幂等验证通过后，将 Flux path 改为 `target-direct`。目标业务库写入仍需要精确 plan/hash 和备份恢复校验；默认脚本只做预览。
6. 检查 namespace 只剩 listener 一个常驻 Pod，并记录回退用的原连接引用和固定镜像。验证完成之前保留候选库；两个 PVC 均禁用 Flux prune，切换路径不会自动删除暂存分片和候选数据库卷。后续 PVC 清理由独立保留策略处理。

初始化 Job 是一次性管理操作，不在 Flux 资源图中。完成或失败后应保存必要的受限诊断记录，再清理 Job；诊断 Pod 不作为常驻服务交付。
