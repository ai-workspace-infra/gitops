# PROD-K3S-V6 可观测性与商业服务控制手册

本目录纳管 `prod-k3s-v6` 生产集群的可观测性栈，包含权威源 VictoriaMetrics 自建体系与观测云（Guance Cloud）香港商业版数据上报。

---

## 一、双集群版本分流规范

| 集群环境 | 观测云空间版本 | Vault KV v2 权威路径 | 目标网关域名 | 计费与配额策略 |
| :--- | :--- | :--- | :--- | :--- |
| **SIT (`sit-k3s-v6`)** | 香港商业版 (cn6) | `kv/data/observability/datakit/hk-commercial` | `https://cn6-openway.guance.com` | SIT 指标上报到指定香港商业空间 |
| **PROD (`prod-k3s-v6`)** | 北京免费版 (cn3) | `kv/data/observability/datakit/bj-free` | `https://cn3-openway.guance.com` | PROD 指标上报到指定北京免费空间 |

---

## 二、GitOps 商业服务启停控制契约

商业 SaaS 服务伴随数据吞吐量计费。通过 GitOps 声明式管理，运维团队拥有三层精准启停与熔断机制：

### 1. 正常运行
- `datakit-helmrelease.yaml`：`spec.suspend: false`；
- `kustomization.yaml`：包含 `datakit-helmrelease.yaml`；
- `datakit-vault-secret.yaml`：`remoteRef.key: observability/datakit/bj-free`。

### 2. 停用采集器

#### 级别 1：紧急止损 / 物理卸载（立即截断商业计费）
- **操作**：在 `kustomization.yaml` 中注释或删除 `datakit-helmrelease.yaml`：
  ```yaml
  resources:
    - datakit-vault-secret.yaml
    - datakit-helmrepository.yaml
    # - datakit-helmrelease.yaml   # <--- 注释此行
  ```
- **效果**：Flux 剪除该 HelmRelease 后，由 Helm 控制器卸载采集器；须检查实际运行状态和云端写入停止情况。

#### 级别 2：调整凭据来源
- 当前约定 PROD 使用 `observability/datakit/bj-free`。若需变更，由凭据所有者确认后更新声明，并验收采集器及云端数据。

#### 级别 3：静默保持 / 临时暂停同步
- **操作**：修改 `datakit-helmrelease.yaml` 中的 `spec.suspend: true`。
- **效果**：FluxCD 暂停对该组件的自动对账；已运行的采集器继续运行和上报。
