# XConnect 区域入口约定

## 台湾入口

PROD 的 `tw-tpe` 区域入口为 `tw-xconnect.svc.plus`，节点声明位于：

- `topology/prod/selfhost/xconnect-regional-pools.yaml`
- `topology/prod/selfhost/ulighthost-xconnect.yaml`
- `topology/prod/selfhost/runtime-topology.yaml`

Gateway 与 AgentProxy 现在分开部署，避免共享节点上的公网监听冲突：

- `xconnect-gateway` 持有 `tw-xconnect-gateway.svc.plus` 的公开 XConnect 入口；
- `agent-proxy` 持有 `tw-xconnect.svc.plus` 的公开 AgentProxy 入口；
- 两者使用独立节点、Vault 记录、服务用户、配置和状态目录；
- 不创建第二个 WireGuard 接口，不把 UDP `51820` 暴露到公网；
- 两个公网域名分别解析到各自节点，双方都可以独立监听 TCP `443`；
- Gateway 的连接信息从 `prod/ulighthost-xconnect/tw-xconnect-gateway.svc.plus` 读取，AgentProxy 继续从 `prod/ulighthost-xconnect/tw-xconnect.svc.plus` 读取。

该声明只描述区域、DNS、节点归属和共址约束，不包含 SSH、TLS、VLESS 或 WireGuard 私密材料。节点连接信息继续从 Vault 的 `prod/ulighthost-xconnect` 记录读取。
