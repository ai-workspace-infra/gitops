# `compose/` — Docker Compose 部署声明

由 [Doco-CD](https://doco.cd) 消费。Doco-CD 跑在目标主机上，克隆本仓库、读取
`<stack>/.doco-cd.yml`，然后执行 `docker compose`。

这一层与 `environments/`、`services/` 平行而**不重叠**：那两个目录是
Kubernetes + Flux 的声明，面向未来的 k3s/sealos 集群；`compose/` 面向当前
在单机 VPS 上以 Docker Compose 运行的域。两条路径服务于同一批服务的不同
运行形态，迁移完成前都需要保留。

## 版本轴

`.env.<env>` 就是版本记录：CD 把新的镜像 tag 写进去、提交、推送，Doco-CD
拉到新 commit 即部署新版本。**git log 就是部署历史**，不需要另一套部署元数据。

镜像 tag 的取值遵循
[镜像 Tag 跨仓契约](https://github.com/ai-workspace-infra/platform-ops-toolkit/blob/main/docs/domains/IMAGE-TAG-CONTRACT.md)：
SIT 用户定义 / UAT `latest` / PROD `v*`·`release-*`。

## 两条铁律

**一、机密不进本目录。** 仓库是公开的，且 Doco-CD 每次部署都是全新 clone。
口令与 token 放在主机的 `/etc/xcontrol/<stack>/secrets.env`，由 Ansible 从
Vault 渲染；compose 里用绝对路径 `env_file` 引用。

**二、bind mount 一律写绝对路径。** 相对路径会解析到 Doco-CD 那个临时 clone
目录里 —— 证书和配置并不在仓库里，于是挂载出一个空目录**而不是报错**。这是
静默故障，不是启动失败。

## 新增一个 stack

1. 建 `compose/<stack>/`，放 `.doco-cd.yml` + `docker-compose.yml` + `.env.<env>`
2. compose 里所有 bind mount 用绝对路径，机密走主机侧 `env_file`
3. 镜像引用写 `${VAR:?...}` 形式 —— 变量缺失时必须让部署失败，而不是拉一个
   名字为空的镜像
4. 在 Doco-CD 的 `POLL_CONFIG` 或 webhook 触发方里登记这个 stack
