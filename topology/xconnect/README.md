# XConnect network declarations

`network-boundaries.yaml` is the non-sensitive catalog for the three isolated
XConnect Zero networks. Runtime secrets are resolved from the Vault paths named
by the catalog and are never committed here.

The UAT Hybrid matrix repeats the active UAT network contract in
`topology/uat/hybrid/resource-matrix.json` under `spec.xconnect_network` so the
orchestrator can pass the network identity to the existing-One workflow without
hard-coding the Gateway or network in a shell script.
