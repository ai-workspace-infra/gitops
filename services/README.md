# `services/` —— K8s/Flux 声明(未来路线,当前非活跃)

这个目录是 Helm release + `OCIRepository` 形式的 K8s/Flux 部署声明，覆盖
accounts / console / database(postgresql / stunnel-server / stunnel-client)
/ observability 等域。

**当前实际部署路径是 `compose/` 目录 + Doco-CD**（见仓库根 `compose/README.md`
与 `compose/web-saas/`）。本目录代表的是 K8s/Flux 化的未来路线，与
`compose/` 不并行运行——不要假设这里的清单已经在任何环境里生效。

## ⚠️ 已知过期：`x-evor` 命名空间

以下文件引用 `ghcr.io/x-evor/*`，这是相关仓库改名/迁移到当前 org
（`ai-workspace-infra` / `ai-workspace-services`）之前留下的旧命名空间，
**已在镜像构建方那一侧退休**（`ai-workspace-infra/postgresql.svc.plus#19`；
`compose/*/.env.uat` 已同步更新）：

```
services/database/postgresql/oci-repository.yaml
services/database/postgresql/stunnel-server-deployment.yaml
services/database/postgresql/stunnel-client-deployment.yaml
services/database/postgresql/values.yaml
services/database/postgresql-core/oci-repository.yaml
services/database/postgresql-core/values.yaml
services/database/stunnel-server/stunnel-server-deployment.yaml
services/observability/observability-stack/oci-repository.yaml
services/stunnel-client/base/stunnel-client-deployment.yaml
services/accounts/base/oci-repository.yaml
services/accounts/base/values.yaml
services/console/base/values.yaml
services/console/base/oci-repository.yaml
```

**在启用这条 K8s/Flux 路线之前，必须逐个核对每个文件该指向哪个 org**——
不能整批替换成同一个命名空间。已核实的对照（`docker manifest inspect`，
非推断）：

| 服务 | 正确路径 |
|---|---|
| postgresql / stunnel-server / stunnel-client | `ghcr.io/ai-workspace-infra/*`（不带 `images/` 前缀） |
| accounts / console | `ghcr.io/ai-workspace-services/*`（不同 org，与上面的不是同一个） |
| observability-stack | 未核实——启用前需要先确认 |

混用会重演 web-saas compose 栈踩过的坑：地址写错时 Helm/Flux 侧不报任何
错，镜像拉取会静默失败，且失败只出现在 Flux/kubelet 自己的事件日志里，
不会体现在这份 YAML 或任何 CI 状态上。
