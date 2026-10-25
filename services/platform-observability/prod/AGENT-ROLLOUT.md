# Standalone Kubernetes agent activation

Parent: GitOps #564. Producer: Artifacts #225. This consumer uses the existing reusable `observability-agent` chart as **one separate HelmRelease**, not three separate exporter charts and not a new server stack.

## Current declaration state

`agent-release.yaml` stages chart version 1.1.0 with both OCIRepository and HelmRelease suspended. This version is a candidate until the producer PR is reviewed, published and independently pulled. The tag is not a fake digest and is not activation permission. Replace the tag with the verified published OCI digest, then explicitly remove suspension in the reviewed activation change. The parent Observability server chart pin is unchanged.

`agent-values.yaml` selects Node host metrics, kube-state-metrics and process exporter, with Vector off. The KSM/process components default off in the generic chart and are opted in here. The Node image, process image and KSM image are immutable. `agent-scrape-values.yaml` is an **inactive activation patch**, deliberately not consumed by the current server HelmRelease while producers are suspended. In the activation PR, merge its `telemetry.extraScrapeConfigs` into the canonical `values.yaml` or add an explicitly generated ConfigMap via the server's `valuesFrom`. Do not apply ad-hoc cluster changes or enable references to missing producers.

The actual cluster GitRepository currently follows a release tag, not main. A main merge and a five-minute interval do not establish runtime application. Promotion must record the exact new GitOps release tag/revision, reconciliation result, chart digest and running workload identity.

## Source and label contract

The existing VictoriaMetrics instance is the sole local scraper: KSM Service; Node/process Pod discovery restricted to this namespace/release; direct kubelet and cAdvisor endpoints. All jobs carry cluster/environment. Node/process `instance` and `node` are actual Kubernetes node names. Node `nodename` is relabeled to that same identity so the existing Node dashboard variables remain usable. cAdvisor preserves namespace/pod/container dimensions for the imported StarsL K8s dashboard. No recording rules are required.

The existing process dashboard filters `namedprocess_namegroup_cpu_seconds_total` by `instance`; verify that independently. Process default non-root collection cannot guarantee ownership-protected I/O/fd metrics, so the activation patch drops those families instead of treating unreadable zeroes as truth. Preserve the three `namedprocess_scrape_*` error counters and investigate coverage gaps.

## Required preflight

1. Verify current cluster identity, node names, source revision and independent read-only backend credentials. Never use the old deployment CMDB as current fleet proof.
2. Check existing host/DaemonSet exporters, Vector and metric ownership. Detect occupied Node Exporter port, duplicate series and collector overlap before enabling a producer; select one canonical path. Do not stop existing services as an automatic side effect of installing this release.
3. Review Node's read-only `/proc`, `/sys` and rootfs mounts, HostToContainer propagation and explicit hostNetwork exception. It binds the node IP; namespace NetworkPolicy may not limit hostNetwork traffic. Verify the actual listener/exposure and approved collector reachability. No cloud/host firewall is changed here.
4. Process only mounts `/proc` read-only, without hostPID, hostNetwork, root, privileged, API token or runtime socket. Verify hidepid/LSM/ownership limitations and non-root runtime identity on the actual target. HTTP 200 alone is insufficient.
5. KSM ServiceAccount may list/watch only reviewed resources, never Secrets/ConfigMaps. Validate the real intended identity's allowed and denied paths without dumping raw sensitive resources.
6. Prove kubelet serving-certificate/CA/IP-SAN verification with the collector token. Do not use an API proxy or insecure TLS fallback. Existing collector RBAC must be reviewed separately; this task does not expand it.

## Runtime acceptance (NOT_RUN by this PR)

Check Ready counts match expected Linux nodes, followed by authenticated queries scoped to the exact cluster/environment:

```promql
up{job=~"node-exporter|process-exporter|kube-state-metrics|kubelet|cadvisor"}
time() - timestamp(node_uname_info)
count by (cluster, environment, node) (node_uname_info)
kube_node_info
sum by (cluster, environment, node) (namedprocess_namegroup_num_procs)
increase(namedprocess_scrape_errors[5m])
increase(namedprocess_scrape_partial_errors[5m])
increase(namedprocess_scrape_procread_errors[5m])
container_cpu_usage_seconds_total
kubelet_volume_stats_capacity_bytes
```

Narrow all these example queries with the exact resource selectors. Require non-empty fresh values (<=180 seconds) and one canonical Node series per expected node; inspect restricted process visibility rather than calling partial data full coverage. PVC metrics also depend on the real storage plugin. Then verify the new K8s dashboard plus existing Node/process dashboards and 30-minute continuity. Schema/config tests and a successful Flux run do not establish these outcomes.

## Optional cross-cluster relay

The generic agent supports `vector.enabled=true`, `vector.mode=relay`: scoped source VM federation → timestamp/identity filter → verified HTTPS remote write. It resamples latest metrics rather than losslessly forwarding every scrape. Set an approved source cluster/environment, metric allowlist, distinct remote backend, source aliases and existing auth/CA Secrets. Authentication comes from runtime secret management. No remote target is specified here, so no placeholder URL/Secret is deployed and relay is off. Require source-stoppage/freshness and loop/duplicate checks before enabling it.

## Upgrade and rollback

Reviewed producer → immutable agent publication/digest → activation PR with source tag, agent pin and canonical scrape config → authorized reconciliation → runtime checks. Keep prior GitOps/chart refs and restore only this release and scrape selection on regression. Do not delete backend data, transfer writers, rebuild nodes or change DNS. Pending rollout and runtime checks keep parent #564 open.
