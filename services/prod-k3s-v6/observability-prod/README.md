# PROD-K3S-V6 可观测性与商业服务控制手册

本目录纳管 `prod-k3s-v6` 生产集群的可观测性栈，包含权威源 VictoriaMetrics 自建体系与观测云（Guance Cloud）香港商业版数据上报。

---

## 一、双集群版本分流规范

| 集群环境 | 观测云空间版本 | Vault KV v2 权威路径 | 目标网关域名 | 计费与配额策略 |
| :--- | :--- | :--- | :--- | :--- |
| **SIT (`sit-k3s-v6`)** | 北京免费版 (cn3) | `kv/data/observability/datakit/bj-free` | `https://cn3-openway.guance.com` | 7 天保留期，体验配额限额保护 |
| **PROD (`prod-k3s-v6`)** | 香港商业版 (cn6) | `kv/data/observability/datakit/hk-commercial` | `https://cn6-openway.guance.com` | 企业商业版，高 SLA，全量指标与分布式 APM |

---

## 二、GitOps 商业服务启停控制契约

商业 SaaS 服务伴随数据吞吐量计费。通过 GitOps 声明式管理，运维团队拥有三层精准启停与熔断机制：

### 1. 正常运行（启用商业服务）
- `datakit-helmrelease.yaml`：`spec.suspend: false`；
- `kustomization.yaml`：包含 `datakit-helmrelease.yaml`；
- `datakit-vault-secret.yaml`：`remoteRef.key: observability/datakit/hk-commercial`。

### 2. 停用商业服务（三种停机级别）

#### 级别 1：紧急止损 / 物理卸载（立即截断商业计费）
- **操作**：在 `kustomization.yaml` 中注释或删除 `datakit-helmrelease.yaml`：
  ```yaml
  resources:
    - datakit-vault-secret.yaml
    - datakit-helmrepository.yaml
    # - datakit-helmrelease.yaml   # <--- 注释此行
  ```
- **效果**：FluxCD 在下一次对账周期（5m 内）自动物理卸载 DataKit DaemonSet。节点停止向 `cn6-openway.guance.com` 发送任何网络请求，**商业计费即刻归零**。自建 VictoriaMetrics 权威源不受任何影响。

#### 级别 2：成本控制 / 降级回退至免费版
- **操作**：在 `datakit-vault-secret.yaml` 中修改 `remoteRef.key`：
  ```yaml
  data:
  - secretKey: ENV_DATAWAY
    remoteRef:
      key: observability/datakit/bj-free   # <--- 从 hk-commercial 切换回 bj-free
      property: DATAWAY_URL
  ```
- **效果**：ESO 自动更新集群内 Secret，DataKit 就地热重载并改向北京体验区上报，退出香港商业版计费。

#### 级别 3：静默保持 / 临时暂停同步
- **操作**：修改 `datakit-helmrelease.yaml` 中的 `spec.suspend: true`。
- **效果**：FluxCD 暂停对该组件的自动对账，可供现场排障或临时冻结配置。
