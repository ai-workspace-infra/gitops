# XConnect Zero Trust topology declarations

This directory is the GitOps source for reviewed, non-sensitive XConnect Zero
Trust network declarations. It describes intended environment topology, public
service endpoints, immutable release pins, cloud sizing, and verification
requirements. It does not contain Terraform resources, host configuration, or
credentials.

## Ownership boundary

| Repository | Owns |
| --- | --- |
| `iac_modules` | Reusable Terraform modules and their module-local validation. |
| `playbooks` | OS-level Xray, WireGuard, Gateway, and controlled-client roles. |
| `gitops/vpn-overlay` | Environment topology and non-sensitive deployment intent. |

Vault is the only source for signing material, enrollment credentials, VLESS
credentials, and device private keys. XConnect Zero Accounts remains the
runtime source of truth for devices, networks, policies, and signed configs.

## Environments

`uat/xconnect-transport-lab.json` is the first-stage, control-plane-free
four-node WireGuard-over-VLESS validation declaration. It is intentionally
separate from `uat/xconnect-lab.json`: it establishes the Gateway/Linux/
Windows/macOS runtime and transport baseline before Accounts enrollment,
signed configuration, policy and ACK are introduced. It declares only role,
version-independent topology, Spot shape, TTL and non-sensitive addresses.
Runtime private keys, disposable TLS material, VLESS identities and rendered
peer files are generated on protected nodes or runners and never enter GitOps.

`uat/xconnect-lab.json` is the canonical disposable UAT declaration for the
XConnect Zero → Gateway → One WireGuard-over-VLESS closure. It pins the two
AWS Spot node shapes and release artifacts, while the workflow injects secrets
only at runtime. The Gateway and controlled-client each have a one-hour maximum
runtime. `spec.node_observation.mode: until-expiry` directs the default
automation to retain both nodes for observation through their absolute
`expires_at` after CI validation succeeds. `release_on_failure: true` permits
earlier release when validation fails. AWS Spot capacity interruption can still
terminate either node before expiry.

## Desktop acceptance stage

`spec.desktop_validation` declares an optional, operator-run macOS (`darwin`)
and Windows stage after the Linux check. It is disabled by default. To enable
a reviewed run, set `enabled` and supply one or two exact public IPv4 `/32`
source addresses in `ingress_cidrs`; never use a broad network or `0.0.0.0/0`.

The cloud workflow accepts an optional, run-scoped
`ssh_debug_ingress_cidrs` dispatch input for temporary operator debugging. The
input is limited by the consumer to canonical IPv4 `/32` values and is not
stored in GitOps. It adds only TCP 22 to both disposable nodes for that run;
it does not open WireGuard UDP 51820 or change the desktop VLESS/TLS
allowlist. The desktop VLESS/TLS list remains disabled unless an explicitly
requested desktop window is enabled; public WireGuard UDP remains closed.

The window is at most 20 minutes and remains inside the existing one-hour
Spot lease. The public handoff contains only endpoint/instance metadata,
device/network identifiers, the Gateway public key and the disposable CA
certificate. Invitation tokens, VLESS credentials, owner identity and private
keys must never be included in that artifact or this repository.

Gateway v0.1.4 fixes formal Accounts device-session renewal; the release is
built by the Gateway project's own CI and downloaded by deployment. Desktop
acceptance requires independent local sync/runtime, exact-peer handshake,
private ping and exact-run HTTP checks. A Linux pass or a Gateway peer count
does not certify either desktop.
# Existing VPS One inventory

`uat/xconnect-one-nodes.yaml` and `prod/xconnect-one-nodes.yaml` declare only
the non-sensitive fixed and dynamic One-node contract. They do not contain IPs,
SSH credentials, VLESS IDs, WireGuard private keys, device credentials or
invites.

- Fixed nodes are `persistent`: they need an explicit operator revocation.
- Pipeline Spot nodes are `ephemeral`: Accounts owns their lease and revokes
  them at expiry; Gateway then removes the peer through its next signed-config
  sync.
- UAT and Prod always use distinct overlay CIDRs. A current single-network
  Gateway cannot host both environments simultaneously; a Prod declaration is
  intentionally non-deployable until a dedicated Prod Gateway is selected.
