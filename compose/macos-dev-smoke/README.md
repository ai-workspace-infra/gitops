# macOS local Doco-CD smoke profile

This is an isolated development-only Compose declaration for proving the
GitOps → Doco-CD → container → owner-health path on one Mac. It is not the
repository default and must never be selected through the root `.doco-cd.yml`.
The explicit profile is the repository-root `.doco-cd.macos-dev-smoke.yml` and
is selected only by a poll entry with `target: macos-dev-smoke`.

The profile contains one public, non-sensitive Redis workload. It has no
production/UAT domain, no host bind mount, no external network, no Vault
reference, and no credential. The private local endpoint is
`127.0.0.1:16379` after the workload is healthy.

The Playbook must pass an explicit `target: macos-dev-smoke` poll entry and a
40-character Git commit in `MACOS_DEV_GITOPS_REVISION`. A moving branch or the
root Doco-CD config is rejected by the bootstrap. The current working-tree
files are preparation only; a commit/ref is intentionally not created here.

For this local-only acceptance, create a bare Git remote under `/tmp`, push the
reviewed local commit into it, and mount it read-only into Doco-CD. This proves
fixed-ref polling without a public push or Git credential. After OrbStack is
running and the Docker-socket approval is recorded, the minimal run is:

```bash
export MACOS_DEV_GITOPS_URL=file:///gitops.git
export MACOS_DEV_GITOPS_BARE_REPO=/tmp/macos-doco-cd-gitops.git
export MACOS_DEV_GITOPS_REVISION=<approved-40-character-commit>
ANSIBLE_LOCAL_TEMP=/tmp/macos-doco-cd-ansible \
  ansible-playbook ai-workspace-infra/playbooks/setup-macos-dev-doco-cd.yml \
  -e macos_doco_cd_allow_docker_socket=true
```

The same command with the same commit is the idempotence run; record the
owner container ID before and after and require it to remain unchanged. For a
rollback, rerun it with the previously accepted commit in
`MACOS_DEV_GITOPS_REVISION`, then repeat the image/health/PONG checks below.

Useful owner checks after an approved run:

```bash
docker --context orbstack exec macos-dev-smoke-owner redis-cli ping
docker --context orbstack inspect --format '{{.Config.Image}} {{.State.Health.Status}}' macos-dev-smoke-owner
```

Idempotence is demonstrated by rerunning the same bootstrap with the same
commit and confirming the owner container ID is unchanged. Rollback is the
same bootstrap with `MACOS_DEV_GITOPS_REVISION` set to the previously accepted
commit; the Playbook must then confirm the pinned image and health again.
