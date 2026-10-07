# iam.svc.plus identity integration contract

`resources/svc.plus/<env>/iam/identity-integrations.yaml` is the non-secret
declaration for the shared ZITADEL issuer. Each provider contains one or more
flows: `workforce`, `workload`, or `application`. A flow records the selected
protocol, the official capability evidence, and the Vault reference for its
runtime metadata.

OIDC is selected whenever the target account supports it. A SAML flow must set
`oidc_supported: false` and include a concrete `selection_reason`. A
`vault-api-token` flow is for provider APIs that have not been verified to
support federation; it is not a claim that the provider supports OIDC.

The manifest contains no client secret, API token, private key, or access
token. Validate it with:

```sh
scripts/validate-iam-integrations.sh
```

Behavior tests and manual acceptance references: [IAM testing](iam-testing.md).
