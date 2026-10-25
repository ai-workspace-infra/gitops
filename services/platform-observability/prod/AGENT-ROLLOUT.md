# Standalone Kubernetes agent activation

Parent: GitOps #564. Producer: Artifacts #225. This consumer uses the existing reusable `observability-agent` chart as **one separate HelmRelease**, not three separate exporter charts and not a new server stack.

## Prepared activation state

This declaration now pins independently pulled published charts:

- agent **1.1.0**: `sha256:e75aebf0aaff448a9d387eb2da1af0695d87752d339dda9c3d982367fe7580af`; publication run 40206544544, source `2dcca6aefb054878f58161b209e651d5bfc4f50c`.
- server stack **1.1.4**: `sha256:cbc00eaa3798542b6445a785a24556d24f828c9949a4fb7359778de2932ee871`; publication run 40206795144, source `8d1d4124bcdd576a3618ad4c7af702c80395fd18`.

The OCIRepository and independent agent HelmRelease are unsuspended in the desired state. The five scrape jobs are attached directly to canonical `values.yaml`; the inactive staging patch has been removed, so there is no second scrape source or manual values merge step. `agent-values.yaml` selects the three producers and leaves Vector off.

The server retains kubeletstats for `[node,pod,volume]`, preserving the existing `k8s_node_*` overview source while raw cAdvisor owns the container metrics. This prevents the old receiver's byte-normalized container memory series from being summed a second time.

The actual cluster GitRepository follows a **release tag**, not main. A main merge and a five-minute interval do not establish runtime application. Root/operator must promote the reviewed GitOps release tag/revision and verify reconciliation and running workload identity. This PR is desired-state activation, not a claim of completed deployment or data acceptance.

Operator's pre-activation baseline independently verified the exact provider resource, SSH identity and node, healthy existing stack/PVC, and absence of exporter DaemonSets/port-9100 listener. It used the authorized management identity and therefore does not establish independent audit-role isolation. Direct kubelet TLS/RBAC and new producer metric freshness remain rollout gates.

## Source and label contract

The existing VictoriaMetrics instance is the sole local scraper: KSM Service; Node/process Pod discovery restricted to this namespace/release; direct kubelet and cAdvisor endpoints. All jobs carry cluster/environment. Node/process `instance` and `node` are actual Kubernetes node names. Node `nodename` is relabeled to that same identity so the existing Node dashboard variables remain usable. cAdvisor preserves namespace/pod/container dimensions for the imported StarsL K8s dashboard. No recording rules are required.

The existing process dashboard filters `namedprocess_namegroup_cpu_seconds_total` by `instance`; verify that independently. Process default non-root collection cannot guarantee ownership-protected I/O/fd metrics, so the canonical scrape config drops those families instead of treating unreadable zeroes as truth. Preserve the three `namedprocess_scrape_*` error counters and investigate coverage gaps.

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

Reviewed producer → immutable agent/stack publication and independently pulled digests (completed) → this activation PR with canonical scrape config → authorized GitOps source tag/revision promotion → runtime checks. Keep prior GitOps/chart refs and restore only this release and scrape selection on regression. Do not delete backend data, transfer writers, rebuild nodes or change DNS. Pending rollout and runtime checks keep parent #564 open.
