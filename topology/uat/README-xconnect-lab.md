# XConnect UAT Spot validation declaration

`xconnect-lab.yaml` is the static source for the XConnect One Linux client CLI
and XConnect One Gateway joint validation. The workflow consumes this file at
an immutable Git commit and passes its values to `iac_modules/vpn-overlay/xconnect-lab`.

The declaration reuses the UAT Zero endpoints, Vault namespace, AWS account,
region, default VPC and default subnet. It does not deploy another control
plane. The only workload nodes added for a run are a one-hour `t4g.micro` Spot
controlled-client and a one-hour `t4g.small` Spot Gateway. The IaC module also
creates disposable security groups so runner SSH and client-to-Gateway traffic
remain scoped to the run; these are destroyed with the instances.

Both instances are ARM64 independent Linux nodes. WireGuard and Xray run as
external host processes. The Gateway is a relay/service role and the client is
the controlled-client CLI role. Public WireGuard ingress remains closed.

The compatibility harness remains non-authoritative and temporary because the
formal Accounts API currently requires trusted pre-seeding for network and
one-use invitations. Once UAT contains seeded Gateway and One invitations, the
workflow must consume those formal enrollment values and remove the harness.
