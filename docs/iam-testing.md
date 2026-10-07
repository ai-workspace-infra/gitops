# IAM 声明自动测试

```bash
ruby tests/test_iam_integrations.rb
bash scripts/validate-iam-integrations.sh
```

无需 IdP、Vault 或云凭据。正常六 provider 声明通过；22 个变异用例验证
缺失/重复 provider、协议选择、bool 类型、跨环境和 provider 路径、路径穿越、
未知敏感字段、issuer/证据/回调、缺理由及重复 purpose 被拒绝。
GitHub Actions `.github/workflows/iam-tests.yml` 在相关 PR/main 更新运行。

校验器用 Ruby 标准库执行字段白名单和业务规则；不声称调用 JSON Schema 引擎。
Schema 与业务规则变更时必须同步维护 validator 与负面用例。

真实接入验收和证据模板位于 `platform-ops-toolkit/docs/howto/iam-integration-testing.md`。
声明通过不能证明目标账号已开通 SSO；账号能力与实际回调必须在 UAT 验收。
