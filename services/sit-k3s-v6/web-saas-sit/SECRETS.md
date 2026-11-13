# SIT Web SaaS runtime secrets

The Contabo overlay synchronizes only the shared runtime credential from Vault.
Database credentials are delivered by the PostgreSQL unit and remain separate.

| Vault KV v2 path | Fields | Kubernetes Secret | Consumers |
| --- | --- | --- | --- |
| `kv/sit/web-saas/runtime` | `JWT_SECRET`, `SESSION_SECRET` | `web-saas-secrets` | accounts, billing, content |

Vault policy is read-only and scoped to this path. ESO uses a dedicated Kubernetes
JWT identity bound to `web-saas-sit:web-saas-runtime-reader` and the Contabo cluster
JWT mount. No credential values are stored in Git.
