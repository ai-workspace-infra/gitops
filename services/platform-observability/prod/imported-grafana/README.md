# Configuration-only migration receipt

Recorded: 2026-10-25, Asia/Shanghai. Source inventory sampled 2026-10-24; original version 13.2.3. Target public health was independently checked on 2026-10-25 and still reports 11.3.0. This change is pending deployment, not an acceptance receipt.

Source: `https://observability.svc.plus/grafana` (configuration GET only).
Target: `https://observability-k3s-v5.svc.plus` / `web-saas-k3s-v5`, PROD.

- 16 source dashboards, 1 source folder, 3 canonical datasource UIDs.
- Retain target Platform overview: expected 17 dashboards after deployment.
- Bundle SHA256: `2c794b9563d6399705b813f9b1c41877c611c3288d53b51fe3429a53324a8c53`.
- Three identical source-input render replays: zero changed files.
- Target endpoints replace source datasource and application endpoints; credentials use dedicated target environment references.
- Target Grafana database backup is encrypted in controlled local evidence. No source historical metrics, logs or traces are included.
- No source users, alert rules, contact points or production notification channels are imported or enabled.

Owner changes: Playbooks PR760, Artifacts PR216 and PR217. Deployment declaration: GitOps PR546. Original snapshots remain in controlled encrypted evidence, not this repository.

## Release gates

1. Published observability-stack 1.1.1 digest is pinned: `sha256:6c9edd8ad04a06ec73ea0a6967e6653c4e1f1048487b88c7e5e9a43c077f7174` (publication run 40110045932 succeeded; independently pulled).
2. Recover authorized target SSH access; current local and historical deployment identities were rejected.
3. Reconcile dedicated target identity credentials and prove the target Accounts resolver accepts the dedicated credential without exposing it.
4. Deploy only this target through its fixed GitOps release; preserve release/PVC identities and admin credential.
5. Verify 13.2.4, datasource queries, all 16 imported dashboards, folder UID, variables, plugin behavior and the retained Platform overview.
6. Repeat reconciliation and verify no drift or unexpected restarts. Rendering idempotence alone is not runtime acceptance.

Status: rendering/tests PASSED; upgrade/configuration runtime acceptance BLOCKED pending access; source writes, historical-data migration, DNS and traffic cutover NOT_RUN.
