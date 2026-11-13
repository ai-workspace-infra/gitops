# SIT-K3S-V6 可观测性服务手册

本目录纳管 `sit-k3s-v6` 测试集群的可观测性栈，包含本地自建轻量级 `vmagent` 以及观测云北京免费版数据上报。

---

## 一、集群版本分流与凭据规范

- **集群环境**：`sit-k3s-v6` (`172.237.9.58`)
- **观测云空间**：北京免费版 (cn3 体验节点)
- **Vault 权威路径**：`kv/data/observability/datakit/bj-free`
- **目标网关端点**：`https://cn3-openway.guance.com`
- **指标集规范**：
  - `postgresql` (:9187/metrics)
  - `kube-state-metrics` (:8080/metrics)
  - `node-exporter` (:9100/metrics)
- **安全与额度策略**：
  - 默认剔除 `host_processes` 进程采集，保护每日免费时间序列额度；
  - 严格保持与生产集群 `prod-k3s-v6`（香港商业版 `observability/datakit/hk-commercial`）的逻辑与网络隔离。
