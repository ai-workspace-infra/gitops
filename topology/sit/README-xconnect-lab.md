# XConnect SIT lab declaration

`xconnect-lab.yaml` is an explicit cross-provider lab topology, separate from the
existing selfhost/serverless/hybrid routing documents. YAML is the canonical
human-editable format for this declaration.
It declares the intended AWS Spot client and co-located Vultr Zero/Gateway, overlay
addresses, TTL, and Vault references. It contains no secrets or generated state.

The pipeline consumes this declaration at a full reviewed commit SHA and uses the
dedicated root `iac_modules/vpn-overlay/xconnect-lab` at another full SHA. The
consumer must fail on a missing or incompatible declaration; no existing
production topology is used as a fallback.

The AWS role/account mirrors the current GitOps AWS OIDC declaration. Its actual
trust policy and SIT permission coverage must be checked before dispatch; this
file does not grant access or change IAM. The Vault SIT role must permit reading
the listed infrastructure and runtime paths plus the GitHub App key. Runtime
ADMIN_TOKEN/SIGNING_KEY/VLESS_ID values are provisioned separately in Vault.

The region/size/overlay values in this dedicated lab document are intentional
desired state, not fallback defaults for another environment. The provider OS ID
and AWS AMI are resolved from the declared Ubuntu release during account preflight.
