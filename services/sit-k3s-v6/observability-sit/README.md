# SIT-K3S-V6 可观测性服务手册

本目录纳管 `sit-k3s-v6` 测试集群的可观测性栈，包含本地自建轻量级 `vmagent` 以及观测云北京免费版数据上报。

---

## 一、集群版本分流与凭据规范

- **集群环境**：`sit-k3s-v6`（Contabo `5.189.172.69`）
- **观测云空间**：香港商业版 (cn6)
- **Vault 权威路径**：`kv/data/observability/datakit/hk-commercial`
- **目标网关端点**：`https://cn6-openway.guance.com`
- **指标集规范**：
  - `postgresql` (:9187/metrics)
  - `kube-state-metrics` (:8080/metrics)
  - `node-exporter` (:9100/metrics)
- **安全与额度策略**：
  - 默认剔除 `host_processes` 进程采集，保护每日免费时间序列额度；
  - DataWay 凭据由 `datakit-dataway-reader` ESO 身份按只读 Vault policy 交付；不将 token/endpoint 值写入 Git。
  - PROD `prod-k3s-v6` 使用独立映射 `observability/datakit/bj-free`，两个集群只复用既有 KV mount 下的不同记录。
  - Contabo SIT overlay 用 Flux Helm post-renderer 从固定版本 DataKit chart `2.16.1` 的 ClusterRole 中移除不需要的 `pods/exec` 权限；升级 chart 时必须复核该补丁仍定位到同一权限项。
