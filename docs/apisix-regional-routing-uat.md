# UAT APISIX 区域分流声明

本文件说明 `topology/uat/selfhost/apisix-gateway.yaml` 的静态目标状态。
它不执行 DNS、EIP、数据库或主机操作；对应动作分别由 IaC、DNS 管理和
Playbooks 负责。

APISIX、配置 API 和 JSONB 同步器部署在区域边缘节点，由 Playbook 安装并由
systemd 直接管理。DocoD/Compose 不参与该网关的安装、升级、启动或回滚；
web-saas 主机只提供远程 PostgreSQL 数据库。

## 入口和部署边界

每个区域部署一个 APISIX Standalone 入口。JP UAT 的固定用户连接域名是
`jp-xconnect.onwalk.net`，入口地址由 `cmdb://network/uat/jp-xconnect-apisix/eip`
解析。APISIX 与 JP 入口使用同一个区域边界，边缘 Agent 保持轻量，只运行
Xray、同步客户端和观测组件。APISIX 不使用 etcd，也不保存账户、订阅、团队
或额度表。

区域域名按 canonical region 去重；free、plus 和 team 资源池不会在用户的
区域下拉框中变成三个区域。root 管理页可以展示所有资源池和节点分布。

## 权益到资源池

| 区域 | 资源池 | 节点声明 | 用户连接域名 |
| --- | --- | --- | --- |
| jp | free | `jp-xconnect-t4g-small-01.svc.plus`、`jp-xconnect-t4g-micro-01.svc.plus` | `jp-xconnect.onwalk.net` |
| jp | plus | `jp-xconnect-c6g-medium-01.svc.plus` | `jp-xconnect.onwalk.net` |
| jp | team | `cmdb://nodes/jp-xconnect-team-01` | `jp-xconnect.onwalk.net` |

Accounts 根据订阅有效期、用户组、团队成员关系和额度状态计算
`effective_entitlement`，并为新连接签发不含物理节点名的 opaque binding。
APISIX 只匹配该 binding 对应的已发布路由，不能从客户端自报的 header 或
query 参数推断 plus、free 或 team。团队 binding 必须同时带有受控的
`team_id`，团队节点永远不能被个人池复用。

一个区域只有一台公共节点时，free 与 plus 可以共用该节点，但 Accounts 和
Agent 仍按各自额度、限流和配置范围执行；节点健康异常也不能把 plus 用户
切入 team 或其它不匹配的池。多台公共节点时，APISIX 按有效权益选择池，
同一个 XHTTP binding 的上行、下行和 packet-up 请求固定到同一后端。

## PG JSONB 到热加载

web-saas 主机的 PostgreSQL `account` 数据库是配置发布的唯一持久化存储，
schema 为 `gateway_config`。连接凭据只通过 Vault 注入运行时角色
`gateway_config_api`；GitOps 只保存 Vault 引用，不保存 DSN、密码或运行时 IP。

配置变更必须经过以下链路：

```text
管理 API
  -> gateway_config.revisions.config (JSONB，不可变草稿)
  -> 原生 APISIX schema/plugin 校验
  -> gateway_config.publications (generation + revision)
  -> 节点同步器按节点令牌读取 snapshot
  -> 生成完整 apisix.yaml
  -> fsync + 原子替换
  -> APISIX Standalone 文件监视热加载
  -> gateway_config.node_status 回报版本和探测结果
```

`routes`、`upstreams`、`services` 和 `plugin_configs` 是 APISIX 文件快照的
四个顶层集合，缺省集合也必须输出为空数组。回滚需要创建新的 publication
generation；节点遇到校验或探测失败时恢复上一份文件并继续服务。

动态路由的管理 API 可以维护区域和 binding 的投影，但提交给同步器的
`config` 必须仍然只包含 APISIX 的四个顶层集合。下面的 YAML 展示管理面
如何把一个 opaque binding 渲染成普通 APISIX route；它不是要提交到 GitOps
的运行时 JSON 文件，也不应把 `region` 或 `bindings` 直接塞进 APISIX
快照的顶层：

```yaml
management_projection:
  region: jp
  entrypoint: jp-xconnect.onwalk.net
  binding:
    id: opaque-binding-id
    resource_class: plus
    team_id: null
    upstream_id: jp-plus
config:
  routes:
    - id: jp-xconnect-plus
      uri: /xconnect/r/opaque-binding-id/*
      upstream_id: jp-plus
  upstreams:
    - id: jp-plus
      nodes:
        jp-xconnect-c6g-medium-01.svc.plus: 1
  services: []
  plugin_configs: []
```

`bindings` 是 Accounts 下发的调度投影；用户 UUID、订阅明文、Xray 密钥和
额度消费明细不进入网关配置。同步器只接受管理面已经发布的完整快照，不能
直接连接 Accounts 表执行查询，也不能自行修改用户权益。

## 验收边界

UAT 验收应覆盖同一入口下的 free、plus、team 路由，过期订阅回落、free
3GB 耗尽后的断流、团队跨租户拒绝、binding 修改拒绝、XHTTP 会话粘性、
同步器断开 PG/API 时保留上一版本，以及探测失败自动回滚。静态 GitOps
校验和同步器单测不能代替真实连接验收。
