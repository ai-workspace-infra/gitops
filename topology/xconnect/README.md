# XConnect network declarations

`network-boundaries.yaml` is the non-sensitive catalog for the three isolated
XConnect Zero networks. Runtime secrets are resolved from the Vault paths named
by the catalog and are never committed here.

The UAT Hybrid matrix repeats the active UAT network contract in
`topology/uat/hybrid/resource-matrix.yaml` under `spec.xconnect_network` so the
orchestrator can pass the network identity to the existing-One workflow without
hard-coding the Gateway or network in a shell script.

## Three-tier routing policy

`routing-policy.yaml` is the declarative source for the XConnect three-tier
traffic split (`Media-Pool`, `Pro-EC2-Pool`, `Custom-Dedicated`). It is
consumed by the accounts control plane (RoutingPolicy sync and subscription
rendering), the portal `/panel/gateway` GitOps editor (which opens a PR against
this file), and `xconnect-edge-agent` / Playbooks when rendering Xray routing.

`Pro-EC2-Pool` is defined as **high-speed quota traffic** (`media_on_pro_action`
defaults to `allow`, with no streaming/download restrictions or client reminder
prompts). `Pro` subscriptions can use both `Media-Pool` (VPS quota) and
`Pro-EC2-Pool` (high-speed quota, e.g. 50 RMB plan = 30GB high-speed + 50GB VPS),
while `Plus` (and `Free`/`Shared`) subscriptions only use `Media-Pool` with
`Pro-EC2-Pool` nodes kept invisible.
