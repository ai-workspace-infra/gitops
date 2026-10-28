# Doco-CD 编排: obs-agent

观测云 `obs-agent` 单机容器部署。

## 启动方法 (由 Doco-CD 或 Playbook 调度)
1. 复制 `.env.example` 到 `.env` 并填写 `AGENT_ID` 与 `AGENT_API_KEY`：
   ```bash
   chmod 600 .env
   ```
2. 启动服务：
   ```bash
   docker compose up -d
   ```
