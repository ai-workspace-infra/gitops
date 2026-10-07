# PROD Selfhost storage contract

`open-platform-prod / web-saas-prod` selects `.doco-cd.prod.yml`, reads
`.env.prod`, and adds `docker-compose.prod-storage.yml`. The default
`.doco-cd.yml` remains the existing UAT declaration.

Playbooks must verify the exact IaC CMDB disk identity, mount its independent
filesystem at `/data`, prepare `/data/postgresql`, and refuse an existing
PostgreSQL container backed by another volume before starting Doco-CD.
The Compose override uses an explicit bind with `create_host_path: false`;
it does not copy or delete any existing PostgreSQL data.

Deployment/init source pins and an immutable Accounts schema/image release
must be integrated before executing PROD `deploy+init`. This declaration
does not switch the stable API aliases or prove database initialization,
business-copy convergence, or production acceptance.

Doco-CD's poll `target: prod` selects the environment file according to its
[official polling contract](https://doco.cd/latest/Poll-Settings/).
