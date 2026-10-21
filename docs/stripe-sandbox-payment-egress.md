# Explicit sandbox payment egress

The sandbox payment profile adds an outbound network only to Accounts. The
existing recovery network stays internal; PostgreSQL and Billing retain their
existing networks, credentials and image pins. The default recovery and primary
profiles are unchanged. This declaration does not select or deploy the profile.

Before an operator selects the alternative sandbox controller configuration:

1. Verify the running Accounts credential is a Stripe test key and each selected
   Price is active, recurring, in the correct currency, and `livemode=false`.
2. Verify the signing secret belongs to the exact Stripe endpoint delivering to
   this runtime. Copying a previous generation's secret does not authenticate a
   different endpoint. Keep the existing declared Vault owner; no secret migration
   or path change is required by this network fix.
3. Record the current controller configuration and immutable image references.
   Select one controller configuration for this Compose project; do not run the
   recovery and sandbox configurations concurrently.
4. Have the Playbooks owner render and compare the resulting Compose model,
   verify only Accounts gains outbound connectivity, and preserve the internal
   database network. Profile selection on a serving runtime is a separate reviewed
   operation.
5. Verify Stripe HTTPS from the Accounts network, then test preview, checkout and
   signed delivery using an isolated test account and database. Do not complete a
   payment against a shared serving database when production billing writes are
   outside the authorized scope. Test-mode events can still reach every registered
   endpoint in the same Stripe account.

Rollback selects the recorded previous controller configuration and reconciles
Accounts through the Playbooks owner. It removes the extra outbound attachment;
it does not restore or alter billing records. No DNS, webhook destination, secret,
background-writer flag, database port or image version changes are part of this
profile. Compose rendering alone is not end-to-end payment acceptance.
