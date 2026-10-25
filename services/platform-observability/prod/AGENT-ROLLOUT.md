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


## Pre-release container ownership review

The 18 declared Dashboard models were checked against the pinned OTel container group and the raw kubelet cAdvisor metric/label contract. Only the old K3s overview working-set panel depended on `k8s_pod_name`; it now selects the canonical cAdvisor job and real namespace/pod/workload-container labels. The StarsL generator and generated model select `job="cadvisor"` for raw container metrics. Its ten application CPU/working-set selectors explicitly exclude pause containers; network selectors intentionally keep sandbox samples and `id="/"` CPU totals retain their host meaning. The unmodified upstream source and checksum remain preserved in Playbooks.

No PrometheusRule/VMRule or Grafana alert definitions are declared in this target bundle or the canonical server chart. This is a source audit only: it does not establish that manually managed live rules are absent or compatible. Those rules must be checked with the approved read-only visible-rules API where available; otherwise record NOT_RUN. The original baseline snapshot remains historical evidence rather than being rewritten to claim runtime PASS.

For runtime coverage compare **every actual node** (live node inventory/KSM) with the scoped raw scrape targets; do not verify only the node hosting the server. For each applicable per-node job, this set difference must be empty:

```promql
max by (node) (kube_node_info{cluster="web-saas-k3s-v5",environment="prod"})
unless on (node)
max by (node) (up{cluster="web-saas-k3s-v5",environment="prod",job="cadvisor"} == 1)
```

Repeat for `node-exporter`, `process-exporter` and `kubelet`, verify each expected node/job has exactly one current target, and compare KSM node names with the actual Kubernetes node list. KSM is a cluster service, not a per-node exporter.

After at least three 15-second scrapes, check active per-container uniqueness, not just different job names. This query must be empty in steady state (repeat for CPU and RSS where applicable):

```promql
count by (cluster,environment,node,namespace,pod,container) (
  container_memory_working_set_bytes{cluster="web-saas-k3s-v5",environment="prod",job="cadvisor",namespace!="",pod!="",container!="",container!="POD"}
  and
  ((time() - timestamp(container_memory_working_set_bytes{cluster="web-saas-k3s-v5",environment="prod",job="cadvisor",namespace!="",pod!="",container!="",container!="POD"})) < 45)
) > 1
```

Also inspect **all jobs** for the same metric and real workload identity; an OTel-derived series may carry `k8s_namespace_name`/`k8s_pod_name`/`container_name` instead of raw namespace/pod/container. Query those separately and require no fresh OTel container-group series after the receiver update; do not infer uniqueness merely from differing labels. Historical samples may remain in the selected time window and are not evidence of current double collection. Query freshness by original sample timestamp. Never sum cgroup root, pod sandbox and application hierarchy together as though they were separate application containers.
