# IaC 声明目录规范

GitOps 是云基础设施的唯一声明层。Terraform 模块仓库只保留可复用模块、模板、渲染器和
运行目录，不再保留 provider 的 `config/` 树，也不复制账号或资源 YAML。

## 统一路径

```text
resources/<project>/<environment>/<provider>/<declaration>.yaml
```

`project` 表示域名或账号边界，`environment` 使用 `sit`、`uat`、`prod`，`provider` 表示目标
云厂商。声明只包含非敏感的期望状态；凭据、私钥、Token 和密码统一放在 Vault 或 CI 密钥库。

## 当前映射

| 项目 | 环境 | 云厂商 | 声明 |
|---|---|---|---|
| `xworktech.com` | `dev` | `gcp` | 账号引导、Landing Zone 与共享资源 |
| `xworktech.com` | `uat` | `gcp` | `open-platform-uat.yaml` |
| `xworktech.com` | `prod` | `gcp` | `open-platform-prod.yaml` |
| `svc.plus` | `sit`、`uat`、`prod` | `aws` | AWS 主机/资源声明及 GitHub Actions OIDC 元数据 |
| `svc.plus` | `sit`、`uat`、`prod` | `vultr` | VPS 主机/资源声明 |
| `svc.plus` | `uat` | `akamai` | `web-saas`、`open-platform`、`ai-workspace` 与 JP/US/SG Agent Proxy 六个独立 namespace |
| `svc.plus` | `dev` | `supabase` | Supabase 项目声明 |

环境和云厂商目录必须分开，避免 UAT 渲染器误读生产值，也允许同一服务在 AWS 与 Vultr
分别声明。

## 消费契约

流水线以固定 ref 检出 GitOps，并把绝对声明路径通过 `--resources` 或 `RESOURCES` 传给渲染器。
Terraform 模块通过输入接收声明路径，不在模块仓库内搜索文件。渲染后的 HCL、tfvars、state、
CMDB 和 Ansible inventory 都是构建产物，并由 Git 忽略。

Akamai UAT 资源按 Terraform state namespace 拆分时，每个 YAML 只声明一台主机；
`global.state_namespace`、`global.workspace` 和文件名（不含 `.yaml`）必须一致。现有消费流水线
通过 `workspace` 参数生成统一 state key，因此触发时必须使用声明中的 namespace；不能把多个服务重新合并进 `selfhost`。
`scripts/validate-akamai-uat-six-namespaces.sh` 是此契约的 CI 校验。

新增云厂商或环境时：

1. 在本仓库创建统一目录和声明；
2. 更新消费流水线，固定 GitOps ref 并传入声明路径；
3. Terraform 模块仓库只保留代码与模板；
4. 先校验声明和渲染结果并发布 UAT，再用同一提交晋升 PROD。
