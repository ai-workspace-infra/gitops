# DEV K3s DataKit (Flux HelmRelease)

Flux owns the DataKit Helm release in the DEV K3s cluster. It adopts the existing release name `datakit` in namespace `datakit`; chart version is pinned to `2.16.1`. This path is for the current SIT feature lane only.

The values preserve the existing DataWay Secret by name and do not contain its value. `inputs.prom` scrapes the Caddy metrics Service on port 9180 every 30 seconds and retains the existing PostgreSQL exporter scrape on port 9187. Container stdout/stderr logs are scoped to namespaces matching `feature-*`. Existing OTLP receiver settings and the DataKit DaemonSet resource budget are retained.

## Ownership and operation

- Source of desired state: this GitOps directory.
- Caller: the DEV cluster Flux Kustomization declared in `environments/clusters/dev-k3s-v5/platform-observability-kustomization.yaml`.
- Side effects: Flux Helm Controller upgrades the existing DataKit release and rolls its DaemonSet in the DEV cluster. This PR does not contain scripts, credentials, or runtime addresses.
- Do not run Helm/Ansible over SSH to apply this release. Merge the reviewed GitOps declaration and verify Flux `HelmRelease/datakit` readiness in-cluster through read-only checks.

## Rollback

Revert the GitOps commit or restore the prior values in this HelmRelease input; Flux will roll back the release configuration. Keep the existing `datakit-dataway-secret` untouched. Remove only the Caddy `dkconfig` entry to stop that scrape while preserving PostgreSQL metrics; restore the prior log selector if required.

## Acceptance

Verify the Flux HelmRelease is Ready at chart `2.16.1`, DataKit DaemonSet is ready, the Caddy `prom` target reports successful/fresh collection, PostgreSQL exporter collection remains present, and business Pod stdout/stderr logs arrive in Guance with the expected cluster/environment tags. This does not claim VictoriaMetrics/Grafana central ingestion.
