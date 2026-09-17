# XConnect 区域入口约定

## 台湾入口

PROD 的 `tw-tpe` 区域入口为 `tw-xconnect.svc.plus`，节点声明位于：

- `topology/prod/selfhost/xconnect-regional-pools.yaml`
- `topology/prod/selfhost/ulighthost-xconnect.yaml`
- `topology/prod/selfhost/runtime-topology.yaml`

该节点允许共址部署 `xconnect-gateway` 与 `agent-proxy`，但共址不等于共享进程、状态目录或公网监听端口：

- `xconnect-gateway` 持有 `tw-xconnect.svc.plus` 的公开 XConnect 入口；
- `agent-proxy` 使用独立服务用户、配置和状态目录，并按 `host-local` 约定运行；
- 不创建第二个 WireGuard 接口，不把 UDP `51820` 暴露到公网；
- 在共享同一公网 IPv4 的情况下，不得让两个服务同时监听 TCP `443`。若 Agent Proxy 以后需要公网入口，必须先落地共享 TLS/SNI 前门或额外公网 IPv4，再扩展 GitOps 声明。

该声明只描述区域、DNS、节点归属和共址约束，不包含 SSH、TLS、VLESS 或 WireGuard 私密材料。节点连接信息继续从 Vault 的 `prod/ulighthost-xconnect` 记录读取。
